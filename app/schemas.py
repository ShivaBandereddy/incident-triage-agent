# app/schemas.py
from typing import List, Optional

from pydantic import BaseModel, Field


class Intake(BaseModel):
    service: str = Field(description='affected component, e.g. datastore, host, network')
    severity: str = Field(description='low, medium, high or critical')
    symptom: str = Field(description='one-line symptom')


class Findings(BaseModel):
    findings: List[str] = Field(description='up to 5 one-line findings quoting key log text')


class Hypothesis(BaseModel):
    cause: str = Field(description="one allowed root cause key or 'unknown'")
    confidence: float = Field(description='0.0 to 1.0')
    evidence: List[str] = Field(description='log lines or runbook facts supporting this')
    runbook: Optional[str] = Field(default=None, description='runbook file name or null')


class Hypotheses(BaseModel):
    hypotheses: List[Hypothesis] = Field(description='up to 3, most likely first')
    proposed_fix: str = Field(description='short numbered suggestions for a human to review')
