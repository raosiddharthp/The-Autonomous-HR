from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class Intent(str, Enum):
    LEAVE_REQUEST   = "leave_request"
    BALANCE_QUERY   = "balance_query"
    PAYROLL_QUERY   = "payroll_query"
    GRIEVANCE_LOG   = "grievance_log"
    POLICY_QUESTION = "policy_question"
    UNKNOWN         = "unknown"


class LeaveType(str, Enum):
    CASUAL  = "casual"
    SICK    = "sick"
    EARNED  = "earned"
    UNPAID  = "unpaid"
    UNKNOWN = "unknown"


class DecisionOutcome(str, Enum):
    APPROVE  = "approve"
    DENY     = "deny"
    ESCALATE = "escalate"
    PENDING  = "pending"


class Slots(BaseModel):
    leave_type: Optional[LeaveType] = None
    start_date: Optional[str]       = None
    end_date:   Optional[str]       = None
    num_days:   Optional[int]       = None
    reason:     Optional[str]       = None


class PolicyRef(BaseModel):
    chunk_id:        str
    page_number:     int
    excerpt:         str
    relevance_score: float
    version_id:      str = "unknown"   # S-20: added for audit log


class AgentState(BaseModel):
    # Identity
    correlation_id: str
    worker_wa_id:   str
    worker_id:      Optional[str] = None

    # Inbound message
    raw_text:     Optional[str] = None
    language:     str           = "en"
    transcript:   Optional[str] = None
    content_type: str           = "text"

    # Classification
    intent:            Optional[Intent] = None
    intent_confidence: float            = 0.0
    slots:             Slots            = Field(default_factory=Slots)

    # Tool outputs
    leave_balance:      Optional[Dict[str, int]] = None
    leave_record_id:    Optional[str]            = None   # S-21: set after write_leave_record commits
    policy_refs:        List[PolicyRef]          = Field(default_factory=list)
    decision:           Optional[DecisionOutcome] = None
    decision_reasoning: Optional[str]             = None
    policy_clause:      Optional[str]             = None
    rag_confidence:     float                    = 0.0    # S-21: written by RAG tool, read by leave_engine

    # Confidence & HITL
    confidence_score: float          = 0.0
    hitl_required:    bool           = False
    hitl_reason:      Optional[str]  = None

    # Response
    response_text:     Optional[str] = None
    response_language: str           = "en"

    # Metadata
    processing_steps: List[str] = Field(default_factory=list)
    errors:           List[str] = Field(default_factory=list)

    def log_step(self, step: str) -> "AgentState":
        self.processing_steps.append(step)
        return self

    def log_error(self, error: str) -> "AgentState":
        self.errors.append(error)
        return self
