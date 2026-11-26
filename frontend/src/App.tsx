
import { useEffect, useState } from "react";

type Finding = { severity: string; title: string; description: string; affected_records: number; business_risk: string };
type Recommendation = { priority_rank: number; title: string; description: string; affected_records: number; severity: string; expected_outcome: string };
type Analysis = {
  analysis_id: string; context: string; context_match_count: number; quality_index: number; high_severity_finding_count: number;
  row_count: number; column_count: number; findings: Finding[]; recommendations: Recommendation[]; executive_summary: string; source_file_name?: string;
};
type AnalysisListItem = { analysis_id: string; context: string; quality_index: number; high_severity_finding_count: number; row_count: number; finding_count: number; recommendation_count: number; source_file_name: string };

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export default function Home() {
  const [apiKey,setApiKey] = useState("");
  const authHeaders = ():Record<string,string> => apiKey ? {"X-Data-Insights-Key":apiKey} : {};
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [history, setHistory] = useState<AnalysisListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHistory() {
    try {
      const response = await fetch(`${API_URL}/analyses`, {headers:authHeaders()});
      if (response.ok) setHistory(await response.json());
    } catch {}
  }

  useEffect(() => { loadHistory(); }, []);

  async function runAnalysis() {
    if (!file) return;
    setLoading(true); setError(null); setAnalysis(null);
    const formData = new FormData(); formData.append("file", file);
    try {
      const uploadResponse = await fetch(`${API_URL}/upload`, { method: "POST", body: formData, headers: authHeaders() });
      if (!uploadResponse.ok) throw new Error(await uploadResponse.text());
      const uploadPayload = await uploadResponse.json();
      const analysisResponse = await fetch(`${API_URL}/analyze/${uploadPayload.upload_id}`, { method: "POST", headers: authHeaders() });
      if (!analysisResponse.ok) throw new Error(await analysisResponse.text());
      const payload = await analysisResponse.json();
      setAnalysis(payload); await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally { setLoading(false); }
  }

  async function openPastAnalysis(id: string) {
    const response = await fetch(`${API_URL}/analysis/${id}`, {headers:authHeaders()});
    if (response.ok) setAnalysis(await response.json());
  }

  return (
    <main>
      <div className="container nav"><div className="logo">DATA QUALITY & DECISION INSIGHTS</div><div className="badge">Independent analytical application</div></div>
      <section className="container hero">
        <div>
          <h1>Understand the data behind the decision.</h1>
          <p>Upload a fictional dataset, inspect transparent quality checks and review proposed actions. No live AI or trained model is used.</p>
          <div className="actions"><a className="button" href="#upload">Analyze Dataset</a><a className="button secondary" href="#results">View Results</a></div>
        </div>
        <div className="card"><div className="label">Application workflow</div><div className="grid" style={{ marginTop: 18 }}><div>Context Hints</div><div>Data Quality</div><div>Workflow Findings</div><div>Prioritized Actions</div><div>Executive Report</div></div></div>
      </section>
      <section id="upload" className="container" style={{ padding: "52px 0" }}>
        <div className="card"><div className="label">Upload</div><h2>Analyze CSV or XLSX</h2>
          <label className="upload"><input type="file" accept=".csv,.xlsx" onChange={(event) => setFile(event.target.files?.[0] || null)} /><strong>{file ? file.name : "Select a fictional dataset"}</strong><p>Use the included synthetic service-delivery sample or another fictional CSV/XLSX dataset. Maximum 10 MB; 50,000 rows and 200 columns.</p></label>
          <label>Optional local API key<input type="password" value={apiKey} onChange={e=>setApiKey(e.target.value)} autoComplete="off" /></label><button onClick={loadHistory}>Refresh history</button><button disabled={!file || loading} onClick={runAnalysis}>{loading ? "Analyzing..." : "Run Analysis"}</button>{error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        </div>
      </section>
      <section id="results" className="container" style={{ paddingBottom: 60 }}>
        <div className="grid" style={{ gap: 20 }}>
          {analysis ? <>
            <div className="grid grid-3"><div className="card"><div className="score">{analysis.quality_index}</div><div className="label">Quality Index · heuristic</div></div><div className="card"><div className="metric">{analysis.context}</div><div className="label">Header matches · {analysis.context_match_count} signals</div></div><div className="card"><div className="metric">{analysis.row_count}</div><div className="label">Rows Analyzed · {analysis.column_count} Columns</div></div></div>
            <div className="card"><div className="label">Executive Summary</div><p>{analysis.executive_summary}</p><a className="button secondary" href="#" onClick={async e=>{e.preventDefault(); const r=await fetch(`${API_URL}/analysis/${analysis.analysis_id}/report.md`,{headers:authHeaders()});if(!r.ok){setError("Report unavailable; check local API key.");return;}const url=URL.createObjectURL(await r.blob());const a=document.createElement("a");a.href=url;a.download="analysis-report.md";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}}>Open Markdown Report</a></div>
            <div className="card"><div className="label">Findings</div><h2>Data and Workflow Findings</h2>{analysis.findings.map((finding, index) => <div key={index} className={`finding ${finding.severity}`}><strong>{finding.title}</strong><p>{finding.description}</p><small>{finding.severity.toUpperCase()} · {finding.affected_records} affected records · {finding.business_risk}</small></div>)}</div>
            <div className="card"><div className="label">Recommendations</div><h2>Priority Actions</h2>{analysis.recommendations.map((rec) => <div key={rec.priority_rank} className="finding"><strong>{rec.priority_rank}. {rec.title}</strong><p>{rec.description}</p><small>{rec.severity.toUpperCase()} · {rec.affected_records} affected records · Human review required</small></div>)}</div>
          </> : <div className="card"><div className="label">Results</div><p>Upload a fictional dataset to run the first analysis.</p></div>}
          <div className="card"><div className="label">Recent Analyses</div><h2>Local History</h2>{history.length ? history.map(item => <button key={item.analysis_id} className="history" onClick={() => openPastAnalysis(item.analysis_id)}><strong>{item.source_file_name}</strong><span>{item.context} · Quality {item.quality_index} · High-severity findings {item.high_severity_finding_count} · {item.finding_count} findings</span></button>) : <p>No analyses saved yet.</p>}</div>
        </div>
      </section>
    </main>
  );
}
