from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ToolResponseSchema(BaseModel):
    tool: str = Field(..., description="Name of the tool used")
    output_file: Optional[str] = Field(None, description="Output file from the tool execution")
    cost: Optional[Dict[str, Any]] = Field(None, description="Cost details for the tool execution")
    status: str = Field(..., description="Status message of the tool execution")
    result: Optional[Dict[str, Any]] = Field(None, description="Additional result details from the tool execution")
    success: bool = Field(..., description="Indicates if the tool execution was successful")

    class Config:
        from_attributes = True