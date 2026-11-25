"""Local dataset analysis API. Bind only to loopback for portfolio demonstrations."""
from __future__ import annotations
import csv
import io
import json
import os
import secrets
import uuid
from pathlib import Path
from fastapi import Depends,FastAPI,File,Header,HTTPException,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from app.models import AnalysisResponse
from app.services.analyzer import analyze_dataframe,read_dataframe_from_path

DATA_DIR=Path(os.environ.get('DATA_INSIGHTS_DIR',Path(__file__).resolve().parents[1]/'runtime'))
MAX_BYTES=10*1024*1024

def require_key(x_data_insights_key: str|None=Header(default=None)):
    expected=os.environ.get('DATA_INSIGHTS_API_KEY')
    if expected and not secrets.compare_digest(x_data_insights_key or '',expected):
        raise HTTPException(401,'Invalid or missing local API key')

app=FastAPI(title='Data Quality and Decision Insights',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Data-Insights-Key'])

def canonical_id(value):
    try:return str(uuid.UUID(value))
    except (ValueError,TypeError):raise HTTPException(400,'Invalid identifier')

def directory(name):
    path=DATA_DIR/name;path.mkdir(parents=True,exist_ok=True);return path

def read_json(name,identifier):
    path=directory(name)/(canonical_id(identifier)+'.json')
    if not path.exists():raise HTTPException(404,'Record not found')
    return json.loads(path.read_text())

def store_analysis(frame,source):
    result=AnalysisResponse(**analyze_dataframe(frame),source_file_name=Path(source).name)
    (directory('analyses')/(result.analysis_id+'.json')).write_text(result.model_dump_json(indent=2))
    return result

async def save_upload(file):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ('.csv','.xlsx'):raise HTTPException(400,'Only CSV and XLSX files are supported')
    raw=await file.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise HTTPException(413,'Demo upload limit is 10 MB')
    if not raw:raise HTTPException(400,'Uploaded file is empty')
    if suffix=='.csv':
        try:
            headers=next(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
            if not headers or any(not h.strip() for h in headers) or len(headers)!=len(set(headers)):
                raise ValueError('Blank or duplicate headers')
        except (ValueError,UnicodeError,StopIteration,csv.Error):raise HTTPException(400,'CSV needs unique nonblank UTF-8 column headers')
    identifier=str(uuid.uuid4());path=directory('uploads')/(identifier+suffix)
    path.write_bytes(raw)
    try:frame=read_dataframe_from_path(path)
    except HTTPException:
        path.unlink(missing_ok=True);raise HTTPException(400,'Could not parse dataset')
    if frame.empty or len(frame)>50000 or len(frame.columns)>200:
        path.unlink(missing_ok=True);raise HTTPException(400,'Demo requires 1–50,000 rows and at most 200 columns')
    metadata={'upload_id':identifier,'file_name':Path(file.filename or 'dataset').name,'suffix':suffix,'row_count':len(frame),'column_count':len(frame.columns)}
    (directory('uploads')/(identifier+'.json')).write_text(json.dumps(metadata))
    return metadata,frame

@app.get('/health')
def health():return {'status':'ok','service':'data-insights','version':'1.0.0'}

@app.post('/upload',dependencies=[Depends(require_key)])
async def upload(file:UploadFile=File(...)):
    metadata,frame=await save_upload(file)
    return {**metadata,'columns':[str(c) for c in frame.columns],'preview':json.loads(frame.head(25).to_json(orient='records'))}

@app.post('/analyze',response_model=AnalysisResponse,dependencies=[Depends(require_key)])
async def analyze(file:UploadFile=File(...)):
    metadata,frame=await save_upload(file)
    return store_analysis(frame,metadata['file_name'])

@app.post('/analyze/{upload_id}',response_model=AnalysisResponse,dependencies=[Depends(require_key)])
def analyze_saved(upload_id:str):
    metadata=read_json('uploads',upload_id)
    return store_analysis(read_dataframe_from_path(directory('uploads')/(canonical_id(upload_id)+metadata['suffix'])),metadata['file_name'])

@app.get('/analyses',dependencies=[Depends(require_key)])
def history():
    paths=sorted(directory('analyses').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:25]
    return [{k:r[k] for k in ['analysis_id','context','quality_index','high_severity_finding_count','row_count','source_file_name']}|{'finding_count':len(r['findings']),'recommendation_count':len(r['recommendations'])} for r in [json.loads(p.read_text()) for p in paths]]

@app.get('/analysis/{analysis_id}',dependencies=[Depends(require_key)])
def detail(analysis_id:str):return read_json('analyses',analysis_id)

@app.get('/analysis/{analysis_id}/report.md',response_class=PlainTextResponse,dependencies=[Depends(require_key)])
def report(analysis_id:str):
    r=read_json('analyses',analysis_id)
    findings='\n'.join(f"- {f['severity'].upper()}: {f['title']} — {f['affected_records']} affected records" for f in r['findings']) or 'No findings under current rules.'
    recommendations='\n'.join(f"{a['priority_rank']}. {a['title']} — Human review required" for a in r['recommendations']) or 'Review whether the checks fit the dataset.'
    return f"# Data Quality and Decision Insights\n\n{r['executive_summary']}\n\n## Findings\n{findings}\n\n## Proposed actions\n{recommendations}\n\nIndices and context hints are heuristics, not calibrated probabilities. Findings may overlap. Synthetic demonstration; no live AI.\n"
