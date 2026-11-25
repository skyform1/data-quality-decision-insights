import io,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from fastapi import HTTPException
from fastapi.testclient import TestClient
import app.main as module
from app.services.analyzer import analyze_dataframe
from app.services.context import detect_context

class AnalysisTests(unittest.TestCase):
 def test_context_hint_and_tie(self):
  self.assertEqual(detect_context(pd.DataFrame({'order_id':[1],'sku':['A']}))[0],'Commerce')
  self.assertEqual(detect_context(pd.DataFrame({'order_id':[1],'invoice_number':[1]}))[0],'Generic / mixed dataset')
 def test_missing_and_duplicate_records(self):
  r=analyze_dataframe(pd.DataFrame({'record_id':[1,1,3],'name':['A','A',None]}));titles=[f['title'] for f in r['findings']];self.assertIn('Missing values detected',titles);self.assertIn('Duplicate records detected',titles);self.assertTrue(any('Duplicate identifiers' in t for t in titles))
 def test_non_id_column_is_not_misclassified(self):
  r=analyze_dataframe(pd.DataFrame({'paid':[True,True,False]}));self.assertFalse(any('identifiers' in f['title'] for f in r['findings']))
 def test_sla_false_not_counted(self):
  r=analyze_dataframe(pd.DataFrame({'ticket_id':[1,2,3],'sla_breached':['true','false','false']}));f=next(x for x in r['findings'] if x['title']=='SLA breaches detected');self.assertEqual(f['affected_records'],1)
 def test_invalid_sla_rejected(self):
  with self.assertRaises(HTTPException):analyze_dataframe(pd.DataFrame({'sla_breached':['maybe']}))
 def test_statuses_and_human_review(self):
  r=analyze_dataframe(pd.DataFrame({'status':['failed','delayed','completed']}));f=next(x for x in r['findings'] if 'risk statuses' in x['title']);self.assertEqual(f['affected_records'],2);self.assertTrue(all(a['human_review_required'] for a in r['recommendations']))
 def test_empty_rejected(self):
  with self.assertRaises(HTTPException):analyze_dataframe(pd.DataFrame())
 def test_clean_data_has_no_forced_actions(self):
  r=analyze_dataframe(pd.DataFrame({'record_id':[1,2],'value':[3,4]}));self.assertEqual(r['findings'],[]);self.assertEqual(r['recommendations'],[]);self.assertEqual(r['quality_index'],100);self.assertEqual(r['high_severity_finding_count'],0)
 def test_confidence_and_roi_are_not_claimed(self):
  r=analyze_dataframe(pd.DataFrame({'record_id':[1,1]}));self.assertNotIn('industry_confidence',r);self.assertTrue(all('confidence_score' not in f for f in r['findings']));self.assertTrue(all('estimated_roi' not in a for a in r['recommendations']))
 def test_synthetic_dataset_analysis(self):
  sample=Path(__file__).resolve().parents[2]/'sample_data/service_requests.csv';r=analyze_dataframe(pd.read_csv(sample));self.assertEqual(r['row_count'],33);self.assertGreater(len(r['findings']),3)

class ApiTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path_patch=patch.object(module,'DATA_DIR',Path(self.tmp.name));self.path_patch.start();self.env=patch.dict(os.environ,{'DATA_INSIGHTS_API_KEY':''});self.env.start();self.client=TestClient(module.app)
 def tearDown(self):self.env.stop();self.path_patch.stop();self.tmp.cleanup()
 def upload(self,name='sample.csv',body=b'record_id,status\n1,delayed\n2,completed\n'):
  return self.client.post('/upload',files={'file':(name,body)})
 def test_upload_analyze_history_detail_report_cycle(self):
  uploaded=self.upload();self.assertEqual(uploaded.status_code,200);uid=uploaded.json()['upload_id'];r=self.client.post('/analyze/'+uid);self.assertEqual(r.status_code,200);aid=r.json()['analysis_id'];self.assertEqual(self.client.get('/analyses').json()[0]['analysis_id'],aid);self.assertEqual(self.client.get('/analysis/'+aid).status_code,200);self.assertIn('Human review required',self.client.get('/analysis/'+aid+'/report.md').text)
 def test_direct_analysis(self):
  r=self.client.post('/analyze',files={'file':('a.csv',b'record_id,value\n1,3\n2,4')});self.assertEqual(r.status_code,200)
 def test_optional_key_protects_reads_and_writes(self):
  with patch.dict(os.environ,{'DATA_INSIGHTS_API_KEY':'test-only-key'}):
   for path in ['/analyses','/analysis/00000000-0000-0000-0000-000000000000','/analysis/00000000-0000-0000-0000-000000000000/report.md']:
    self.assertEqual(self.client.get(path).status_code,401)
   self.assertEqual(self.upload().status_code,401);self.assertEqual(self.client.get('/analyses',headers={'X-Data-Insights-Key':'test-only-key'}).status_code,200);self.assertEqual(self.client.get('/health').status_code,200)
 def test_unsupported_empty_duplicate_headers_and_malformed_csv(self):
  for name,body in [('a.txt',b'foo'),('a.csv',b''),('a.csv',b'id,id\n1,2'),('a.csv',b'\xff')]:self.assertEqual(self.upload(name,body).status_code,400)
 def test_identifiers_and_missing_analysis(self):
  self.assertEqual(self.client.get('/analysis/not-an-id').status_code,400);self.assertEqual(self.client.get('/analysis/00000000-0000-0000-0000-000000000000').status_code,404)
 def test_size_limit(self):
  with patch.object(module,'MAX_BYTES',10):self.assertEqual(self.upload('a.csv',b'record_id\n123456789').status_code,413)
 def test_xlsx(self):
  buf=io.BytesIO();pd.DataFrame({'record_id':[1,2],'status':['failed','completed']}).to_excel(buf,index=False);self.assertEqual(self.upload('sample.xlsx',buf.getvalue()).status_code,200)
 def test_cors_does_not_allow_arbitrary_origin(self):
  r=self.client.options('/upload',headers={'Origin':'https://untrusted.example','Access-Control-Request-Method':'POST'});self.assertNotIn('access-control-allow-origin',r.headers)

if __name__=='__main__':unittest.main()
