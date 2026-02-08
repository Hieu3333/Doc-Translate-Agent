from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class UserSignUp(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password")

class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

class UserSchema(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the user")
    username: str = Field(..., description="Username of the user")
    email: str = Field(..., description="Email address of the user")
    password: Optional[str] = Field(None, description="Hashed password")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    
    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")