from fastapi import APIRouter, HTTPException, status, Header, UploadFile, File, Form
from core.schemas.session import (
    SessionCreate,
    SessionSchema,
    SessionWithMessages,
    SessionUpdate,
    MessageCreate,
    MessageSchema,
    ChatRequest,
    ChatResponse,
)
from core.database import get_supabase_client
from core.auth import decode_token
from typing import List, Optional
import uuid
from uuid import UUID
from service.storage_service import FileStorageService
from service.chat_service import ChatService

router = APIRouter(prefix="/sessions", tags=["sessions"])

def verify_token(authorization: Optional[str]) -> str:
    """Verify JWT token and return user_id"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return payload.get("sub")

# ===================== Session Endpoints =====================

@router.post("", response_model=SessionSchema, status_code=status.HTTP_201_CREATED)
async def create_session(
    file: UploadFile = File(...),
    context: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
):
    """Create a new translation session with file upload"""
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    session_id = str(uuid.uuid4())
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Create storage path: user_id/session_id/filename
        storage_path = f"{user_id}/{session_id}/{file.filename}"
        
        # Upload file to storage
        file_storage_path = FileStorageService.upload_file(
            file_path=storage_path,
            file_content=file_content
        )
        
        # Save session to database with file path
        response = supabase.table("translation_sessions").insert({
            "id": session_id,
            "user_id": user_id,
            "main_file_path": file_storage_path,
            "context": context,
        }).execute()
        
        if response.data:
            session = response.data[0]
            return SessionSchema(
                id=session["id"],
                user_id=session["user_id"],
                main_file_path=session["main_file_path"],
                context=session["context"],
                created_at=session["created_at"],
                updated_at=session["updated_at"],
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session in database"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )

@router.get("/{session_id}", response_model=SessionWithMessages)
async def get_session(
    session_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get a session with all its messages"""
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    try:
        # Get session
        session_response = supabase.table("translation_sessions").select("*").eq("id", session_id).execute()
        
        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session = session_response.data[0]
        
        # Verify ownership
        if session["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get messages
        messages_response = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
        
        messages = [
            MessageSchema(
                id=msg["id"],
                session_id=msg["session_id"],
                role=msg["role"],
                content=msg["content"],
                file_path=msg["file_path"],
                created_at=msg["created_at"],
            )
            for msg in messages_response.data
        ]
        
        return SessionWithMessages(
            id=session["id"],
            user_id=session["user_id"],
            main_file_path=session["main_file_path"],
            context=session["context"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
            messages=messages,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching session: {str(e)}"
        )

@router.get("", response_model=List[SessionSchema])
async def list_sessions(authorization: Optional[str] = Header(None)):
    """List all sessions for the current user"""
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("translation_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        
        sessions = [
            SessionSchema(
                id=session["id"],
                user_id=session["user_id"],
                main_file_path=session["main_file_path"],
                context=session["context"],
                created_at=session["created_at"],
                updated_at=session["updated_at"],
            )
            for session in response.data
        ]
        
        return sessions
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sessions: {str(e)}"
        )

@router.put("/{session_id}", response_model=SessionSchema)
async def update_session(
    session_id: str,
    session_data: SessionUpdate,
    authorization: Optional[str] = Header(None),
):
    """Update a session"""
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    try:
        # Verify ownership
        session_response = supabase.table("translation_sessions").select("user_id").eq("id", session_id).execute()
        
        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session_response.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update session (only context can be updated, file is immutable)
        update_data = {}
        if session_data.context is not None:
            update_data["context"] = session_data.context
        
        response = supabase.table("translation_sessions").update(update_data).eq("id", session_id).execute()
        
        if response.data:
            session = response.data[0]
            return SessionSchema(
                id=session["id"],
                user_id=session["user_id"],
                main_file_path=session["main_file_path"],
                context=session["context"],
                created_at=session["created_at"],
                updated_at=session["updated_at"],
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating session: {str(e)}"
        )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    authorization: Optional[str] = Header(None),
):
    """Delete a session and all its messages"""
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    try:
        # Verify ownership
        session_response = supabase.table("translation_sessions").select("user_id").eq("id", session_id).execute()
        
        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session_response.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete session (messages will be deleted due to CASCADE)
        supabase.table("translation_sessions").delete().eq("id", session_id).execute()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )

# ===================== Message Endpoints =====================

@router.get("/{session_id}/messages", response_model=List[MessageSchema])
async def get_messages(
    session_id: str,
    authorization: Optional[str] = Header(None),
):
    """Get all messages in a session"""
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    try:
        # Verify session exists and user owns it
        session_response = supabase.table("translation_sessions").select("user_id").eq("id", session_id).execute()
        
        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session_response.data[0]["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get messages
        response = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
        
        messages = [
            MessageSchema(
                id=msg["id"],
                session_id=msg["session_id"],
                role=msg["role"],
                content=msg["content"],
                file_path=msg["file_path"],
                created_at=msg["created_at"],
            )
            for msg in response.data
        ]
        
        return messages
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching messages: {str(e)}"
        )

# ===================== Chat Endpoint =====================

@router.post("/{session_id}/chat", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def chat(
    session_id: str,
    chat_request: ChatRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Chat endpoint - User sends a message and backend responds with agent response.
    
    1. Saves user message to database
    2. Processes message with agent logic
    3. Saves agent response to database
    4. Returns both messages
    """
    user_id = verify_token(authorization)
    supabase = get_supabase_client()
    
    try:
        # Verify session exists and user owns it
        session_response = supabase.table("translation_sessions").select("*").eq("id", session_id).execute()
        
        if not session_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        session = session_response.data[0]
        
        if session["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Save user message
        user_message_id = str(uuid.uuid4())
        user_message_response = supabase.table("messages").insert({
            "id": user_message_id,
            "session_id": session_id,
            "role": "user",
            "content": chat_request.message,
            "file_path": None,
        }).execute()
        
        if not user_message_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save user message"
            )
        
        user_message = user_message_response.data[0]
        
        # Get conversation history for context
        messages_response = supabase.table("messages").select("*").eq("session_id", session_id).order("created_at").execute()
        
        conversation_history = []
        if messages_response.data:
            # Convert message history to OpenAI format (exclude the current user message)
            for msg in messages_response.data[:-1]:  # Exclude the just-saved user message
                conversation_history.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        chat_service = ChatService()
        
        # Process message with LLM
        agent_response_text = await chat_service.handle_user_message(
            user_message=chat_request.message,
            session_context=session["context"],
            conversation_history=conversation_history
        )
        
        # Save agent response message
        agent_message_id = str(uuid.uuid4())
        agent_message_response = supabase.table("messages").insert({
            "id": agent_message_id,
            "session_id": session_id,
            "role": "assistant",
            "content": agent_response_text,
            "file_path": None,
        }).execute()
        
        if not agent_message_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save agent response"
            )
        
        agent_message = agent_message_response.data[0]
        
        return ChatResponse(
            user_message=MessageSchema(
                id=user_message["id"],
                session_id=user_message["session_id"],
                role=user_message["role"],
                content=user_message["content"],
                file_path=user_message["file_path"],
                created_at=user_message["created_at"],
            ),
            agent_response=MessageSchema(
                id=agent_message["id"],
                session_id=agent_message["session_id"],
                role=agent_message["role"],
                content=agent_message["content"],
                file_path=agent_message["file_path"],
                created_at=agent_message["created_at"],
            ),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )
