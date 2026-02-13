from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# Message schemas
class MessageCreate(BaseModel):
    role: str = Field(..., description="Role (e.g., 'user', 'assistant')")
    content: str = Field(..., description="Message content")
    file_path: Optional[str] = Field(None, description="Optional file path")
    reasoning_content: Optional[str] = Field(None, description="Optional reasoning content (for deepseek-reasoner)")


class MessageSchema(BaseModel):
    id: UUID = Field(..., description="Message ID")
    session_id: UUID = Field(..., description="Session ID")
    role: str = Field(..., description="Role (e.g., 'user', 'assistant')")
    content: str = Field(..., description="Message content")
    file_path: Optional[str] = Field(None, description="Optional file path")
    reasoning_content: Optional[str] = Field(None, description="Optional reasoning content (for deepseek-reasoner)")
    created_at: datetime = Field(..., description="Message creation timestamp")
    
    class Config:
        from_attributes = True


class SessionWithMessages(BaseModel):
    id: UUID = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    main_file_path: str = Field(..., description="Storage path of the uploaded file")
    context: Optional[str] = Field(None, description="Context for translation")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Session last update timestamp")
    messages: List[MessageSchema] = Field(default_factory=list, description="Messages in session")
    
    class Config:
        from_attributes = True

class SessionSchema(BaseModel):
    id: UUID = Field(..., description="Session ID")
    user_id: UUID = Field(..., description="User ID")
    main_file_path: str = Field(..., description="Storage path of the uploaded file")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Session last update timestamp")
    
    class Config:
        from_attributes = True
    
class ChatRequest(BaseModel):
    master_language: str = Field(..., description="Master language for translation (e.g., 'English')")
    message: str = Field(..., description="User message to send")
    model: str = Field("gpt-4o-mini", description="Language model to use for processing the message")
    

class ChatResponse(BaseModel):
    user_message: MessageSchema = Field(..., description="Saved user message")
    agent_response: Optional[MessageSchema] = Field(None, description="Agent response message")
    file_path: Optional[str] = Field(None, description="Optional file path")
    token_usage: Optional[Dict[str, Any]] = Field(None, description="Token usage details")
    cost: Optional[float] = Field(None, description="Cost incurred for the chat interaction")