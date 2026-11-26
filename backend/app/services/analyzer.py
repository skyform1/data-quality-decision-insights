from __future__ import annotations

import io
import time
import uuid
from typing import Any, Dict, List, Tuple

import pandas as pd
from fastapi import HTTPException, UploadFile

from app.services.context import detect_context



def read_dataframe_from_path(path) -> pd.DataFrame:
    name = str(path).lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(path)
        if name.endswith((".xlsx",)):
            return pd.read_excel(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}") from exc
    raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")


def read_upload(file: UploadFile) -> pd.DataFrame:
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    name = file.filename or "dataset"
    try:
        if name.lower().endswith(".csv"):
            return pd.read_csv(io.BytesIO(raw))
        if name.lower().endswith((".xlsx",)):
            return pd.read_excel(io.BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}") from exc
    raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")


def severity_from_ratio(ratio: float) -> str:
    if ratio >= 0.20:
        return "critical"
    if ratio >= 0.10:
        return "high"
    if ratio >= 0.05:
        return "medium"
    return "low"


def analyze_quality(df: pd.DataFrame) -> Tuple[int, List[Dict[str, Any]]]:
    findings: List[Dict[str, Any]] = []
    rows = max(len(df), 1)
    cols = max(len(df.columns), 1)

    missing = df.isna().sum()
    missing_total = int(missing.sum())
    if missing_total:
        affected_cols = missing[missing > 0].index.astype(str).tolist()
        ratio = missing_total / (rows * cols)
        findings.append({
            "type": "data_quality",
            "severity": severity_from_ratio(ratio),
            "title": "Missing values detected",
            "description": f"{missing_total} missing values were detected across {len(affected_cols)} columns.",
            "affected_records": int(df.isna().any(axis=1).sum()),
            "affected_columns": affected_cols[:10],
            "business_risk": "Incomplete data can distort analysis, reporting accuracy, and operational decisions.",
        })

    # Full duplicate rows
    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        ratio = duplicate_rows / rows
        findings.append({
            "type": "data_quality",
            "severity": severity_from_ratio(ratio),
            "title": "Duplicate records detected",
            "description": f"{duplicate_rows} full duplicate records were found.",
            "affected_records": duplicate_rows,
            "affected_columns": [],
            "business_risk": "Duplicate records can inflate volume, revenue, workload, or performance metrics.",
        })

    # ID-like column duplicates, more useful for operations datasets
    for col in df.columns:
        c = str(col).lower()
        if (c == "id" or c.endswith("_id") or c in ("sku", "invoice_number", "transaction_number", "ticket_number", "order_number")):
            duplicate_ids = int(df[col].dropna().duplicated().sum())
            if duplicate_ids:
                findings.append({
                    "type": "data_quality",
                    "severity": severity_from_ratio(duplicate_ids / rows),
                    "title": f"Duplicate identifiers detected in {col}",
                    "description": f"{duplicate_ids} duplicate values were detected in the identifier column {col}.",
                    "affected_records": duplicate_ids,
                    "affected_columns": [str(col)],
                    "business_risk": "Duplicate identifiers can create reconciliation errors, ownership conflicts, fulfilment mistakes, or inaccurate reporting.",
                })

    # Numeric outliers and invalid zero values in operational measures
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) > 20:
            zero_count = int((series == 0).sum())
            if zero_count and any(token in str(col).lower() for token in ["price", "revenue", "duration", "amount", "time", "days"]):
                findings.append({
                    "type": "data_quality",
                    "severity": severity_from_ratio(zero_count / rows),
                    "title": f"Potential invalid zero values in {col}",
                    "description": f"{zero_count} zero values were detected in {col}, which may indicate missing or invalid operational records.",
                    "affected_records": zero_count,
                    "affected_columns": [str(col)],
                    "business_risk": "Invalid zero values can hide revenue leakage, metadata errors, process exceptions, or failed measurement.",
                })
            if series.std() > 0:
                z = (series - series.mean()).abs() / series.std()
                outliers = int((z > 3).sum())
                if outliers:
                    findings.append({
                        "type": "data_quality",
                        "severity": severity_from_ratio(outliers / rows),
                        "title": f"Outliers detected in {col}",
                        "description": f"{outliers} statistically unusual values were detected in {col}.",
                        "affected_records": outliers,
                        "affected_columns": [str(col)],
                        "business_risk": "Outliers may reveal errors, fraud, process exceptions, or high-impact edge cases.",
                    })

    quality_score = round(100 * (1 - missing_total / (rows * cols)) * (1 - duplicate_rows / rows))
    return quality_score, findings[:15]


def generate_operational_findings(df: pd.DataFrame) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    rows = max(len(df), 1)
    lower_cols = {str(c).lower(): c for c in df.columns}

    for key, col in lower_cols.items():
        if key == "sla_breached":
            values = df[col].dropna().astype(str).str.strip().str.lower()
            valid = values.isin(["true", "false", "1", "0", "1.0", "0.0"])
            if not valid.all():
                raise HTTPException(status_code=400, detail="sla_breached must contain true/false or 1/0")
            breached = int(values.isin(["true", "1", "1.0"]).sum())
            if breached:
                findings.append({
                    "type": "operations",
                    "severity": severity_from_ratio(breached / rows),
                    "title": "SLA breaches detected",
                    "description": f"{breached} records indicate SLA breaches.",
                    "affected_records": breached,
                    "affected_columns": [str(col)],
                    "business_risk": "SLA breaches can reduce customer trust, increase escalation volume, and create contractual risk.",
                })
        if "status" in key:
            values = df[col].astype(str).str.lower()
            risky = values.isin(["failed", "blocked", "delayed", "cancelled"]).sum()
            if risky:
                findings.append({
                    "type": "operations",
                    "severity": severity_from_ratio(int(risky) / rows),
                    "title": f"Operational risk statuses in {col}",
                    "description": f"{int(risky)} records are marked as failed, blocked, delayed, or cancelled.",
                    "affected_records": int(risky),
                    "affected_columns": [str(col)],
                    "business_risk": "Risk statuses indicate workflow friction, delayed execution, or avoidable rework.",
                })
    return findings[:8]


def generate_recommendations(findings: List[Dict[str, Any]], context: str) -> List[Dict[str, Any]]:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    ranked = sorted(findings, key=lambda f: (order.get(f["severity"], 4), -f["affected_records"]))
    return [{"priority_rank": i, "title": "Review " + f["title"].lower(),
             "description": "Confirm the finding with the dataset owner before choosing a correction or process change.",
             "expected_outcome": "Potential improvement in data reliability; benefit requires measurement.",
             "affected_records": f["affected_records"], "severity": f["severity"],
             "category": f["type"], "human_review_required": True}
            for i, f in enumerate(ranked[:6], start=1)]


def executive_summary(context: str, quality_score: int, findings: List[Dict[str, Any]], recommendations: List[Dict[str, Any]]) -> str:
    return (f"Header-based context hint: {context}. Quality index {quality_score}/100 is a rule-based heuristic, "
            f"not a probability or certification. {len(findings)} findings and {len(recommendations)} review actions. "
            "Findings can overlap; absence of a rule match does not establish data correctness. No trained model or live AI is used.")


def analyze_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    start = time.time()
    if len(df) == 0:
        raise HTTPException(status_code=400, detail="Dataset has no rows")
    context, match_count, signals = detect_context(df)
    if len(df) > 50000 or len(df.columns) > 200:
        raise HTTPException(status_code=400, detail="Demo limit: 50,000 rows and 200 columns")
    if df.columns.duplicated().any():
        raise HTTPException(status_code=400, detail="Duplicate column headers are not supported")
    quality_score, quality_findings = analyze_quality(df)
    operational_findings = generate_operational_findings(df)
    findings = (quality_findings + operational_findings)[:20]
    recommendations = generate_recommendations(findings, context)
    high_risk_count = len([f for f in findings if f["severity"] in ["critical", "high"]])
    high_severity_finding_count = high_risk_count
    summary = executive_summary(context, quality_score, findings, recommendations)
    return {
        "analysis_id": str(uuid.uuid4()),
        "context": context,
        "context_match_count": match_count,
        "detected_signals": signals,
        "quality_index": quality_score,
        "high_severity_finding_count": high_severity_finding_count,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "findings": findings,
        "recommendations": recommendations,
        "executive_summary": summary,
        "execution_time_seconds": round(time.time() - start, 2),
    }
