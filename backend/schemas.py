from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = []

class ResolutionRequest(BaseModel):
    error_code: Optional[str] = None
    module: Optional[str] = None
    description: str
    resolution: str
    ticket_level: str

class HealthResponse(BaseModel):
    vectorstore_loaded: bool

class FeedbackRequest(BaseModel):
    type: str  # 'positive' or 'negative'
    messageId: str
    suggestions: Optional[str] = None