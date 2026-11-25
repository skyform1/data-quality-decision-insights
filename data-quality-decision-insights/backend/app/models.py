from pydantic import BaseModel, Field
class Finding(BaseModel):
    type: str
    severity: str
    title: str
    description: str
    affected_records: int
    affected_columns: list[str] = Field(default_factory=list)
    business_risk: str
class Recommendation(BaseModel):
    priority_rank: int
    title: str
    description: str
    expected_outcome: str
    affected_records: int
    severity: str
    category: str
    human_review_required: bool
class AnalysisResponse(BaseModel):
    analysis_id: str
    context: str
    context_match_count: int
    detected_signals: list[str]
    quality_index: int
    high_severity_finding_count: int
    row_count: int
    column_count: int
    findings: list[Finding]
    recommendations: list[Recommendation]
    executive_summary: str
    execution_time_seconds: float
    source_file_name: str = "dataset"
