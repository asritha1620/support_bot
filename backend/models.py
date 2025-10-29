from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    message: str
    session_id: str
    mode: Optional[str] = None  # e.g., "add_resolution" for data addition mode

class ChatResponse(BaseModel):
    success: bool
    response: str
    sources: List[Dict[str, Any]] = []
    session_id: str
    actions: List[Dict[str, str]] = []  # e.g., [{"type": "button", "label": "Add Resolution", "action": "add_resolution"}]

class FileInfo(BaseModel):
    filename: str
    rows: int
    columns: int
    column_names: List[str]

class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_info: FileInfo
    session_id: str