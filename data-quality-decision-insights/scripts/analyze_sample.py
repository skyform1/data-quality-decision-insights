"""Regenerate the bundled synthetic example without running the web application."""
from pathlib import Path
import sys,json
from html import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.services.analyzer import analyze_dataframe,read_dataframe_from_path
root=Path(__file__).resolve().parents[1]
result=analyze_dataframe(read_dataframe_from_path(root/'sample_data/service_requests.csv'))
result['source_file_name']='service_requests.csv'
(root/'examples').mkdir(exist_ok=True)
(root/'examples/analysis.json').write_text(json.dumps(result,indent=2))
html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Data Quality and Decision Insights</title><style>body{font:16px/1.6 system-ui,sans-serif;background:#081427;color:#f2f7ff;margin:0}main{max-width:1080px;margin:auto;padding:32px}h1{font-size:clamp(28px,4vw,44px);line-height:1.2}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.card{background:#11243d;border:1px solid #315475;border-radius:12px;padding:20px;margin:16px 0}.metric{font-size:36px;color:#67d7ff}.note{border-left:4px solid #67d7ff;padding:18px;background:#142b47}p{color:#c0cfe0}.tag{color:#ffd166}li{margin:12px 0}</style></head><body><main><p>INDEPENDENT ANALYTICAL APPLICATION</p><h1>Data Quality &amp; Decision Insights</h1><div class="note"><b>Static sample report</b><p>Computed by the included Python engine from original fictional data. This file does not accept uploads. The full React application and API are included separately. No live AI or trained model is used.</p></div><div class="grid">'''
for label,value in [('Rows analysed',result['row_count']),('Quality index · heuristic',result['quality_index']),('Findings',len(result['findings'])),('High-severity findings',result['high_severity_finding_count'])]:html+='<div class="card"><div class="metric">'+str(value)+'</div>'+label+'</div>'
html+='</div><section class="card"><h2>Summary</h2><p>'+escape(result['executive_summary'])+'</p></section><h2>Data and workflow findings</h2>'
for f in result['findings']:html+='<section class="card"><span class="tag">'+escape(f['severity'].upper())+'</span><h3>'+escape(f['title'])+'</h3><p>'+escape(f['description'])+'</p><p>'+str(f['affected_records'])+' affected records · '+escape(', '.join(f['affected_columns']))+'</p></section>'
html+='<h2>Proposed review actions</h2><ol>'
for a in result['recommendations']:html+='<li><b>'+escape(a['title'])+'</b><p>'+escape(a['description'])+'</p></li>'
html+='</ol><div class="note">Findings can overlap and are not additive counts of distinct bad rows. Context labels are header hints. No verified business impact or statistical confidence is claimed.</div></main></body></html>'
(root/'DEMO.html').write_text(html)
print(json.dumps({'rows':result['row_count'],'findings':len(result['findings']),'quality_index':result['quality_index']}))
