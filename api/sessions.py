from fastapi import APIRouter, HTTPException, status, Header, UploadFile, File, Form
from core.schemas.session import (
    SessionSchema,
    SessionWithMessages,
    MessageCreate,
    MessageSchema,
    ChatRequest,
    ChatResponse,
)

from core.auth import decode_token
from typing import List, Optional
from uuid import UUID
import logging
from pathlib import Path
from service.storage_service import FileStorageService
from service.chat_service import ChatService
from service.session_service import SessionService

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

def verify_token(authorization: Optional[str]) -> str:
    """Verify JWT token and return user_id"""
    if not authorization:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid token format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    token = authorization[7:]
    payload = decode_token(token)
    if not payload:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    return payload.get("sub")

# ===================== Session Endpoints =====================

@router.post("", response_model=SessionSchema, status_code=status.HTTP_201_CREATED)
async def create_session(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    """Create a new translation session with file upload"""
    user_id = verify_token(authorization)
    session_service = SessionService()
    logger.info(f"Creating session for user: {user_id}")
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Create initial session with empty path
        new_session = session_service.create_session(
            user_id=UUID(user_id),
            main_file_path="",
        )
        
        # Create storage path: user_id/session_id/filename
        storage_path = f"{user_id}/{new_session.id}/{file.filename}"
        
        # Upload file to storage
        file_storage_path = FileStorageService.upload_file(
            file_path=storage_path,
            file_content=file_content
        )
        
        # Update session with actual file path
        updated_session = session_service.update_session(
            session_id=new_session.id,
            main_file_path=file_storage_path
        )
        
        logger.info(f"Session {updated_session.id} created successfully for user {user_id}")
        return SessionSchema(
            id=updated_session.id,
            user_id=updated_session.user_id,
            main_file_path=updated_session.main_file_path,
            created_at=updated_session.created_at,
            updated_at=updated_session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
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
    session_service = SessionService()
    logger.info(f"Fetching session {session_id} for user {user_id}")
    
    try:
        # Get session with messages using session_service
        session_with_messages = session_service.get_session_with_messages(UUID(session_id))
        
        # Verify ownership
        if str(session_with_messages.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return session_with_messages
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching session: {str(e)}"
        )

@router.get("", response_model=List[SessionSchema])
async def list_sessions(authorization: Optional[str] = Header(None)):
    """List all sessions for the current user"""
    user_id = verify_token(authorization)
    session_service = SessionService()
    logger.info(f"Listing sessions for user {user_id}")
    
    try:
        sessions = session_service.list_user_sessions(UUID(user_id))
        logger.info(f"Listed {len(sessions)} sessions for user {user_id}")
        return sessions
    
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sessions: {str(e)}"
        )

# @router.put("/{session_id}", response_model=SessionSchema)
# async def update_session(
#     session_id: str,
#     session_data: SessionUpdate,
#     authorization: Optional[str] = Header(None),
# ):
#     """Update a session"""
#     user_id = verify_token(authorization)
#     supabase = get_supabase_client()
    
#     try:
#         # Verify ownership
#         session_response = supabase.table("translation_sessions").select("user_id").eq("id", session_id).execute()
        
#         if not session_response.data:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Session not found"
#             )
        
#         if session_response.data[0]["user_id"] != user_id:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Access denied"
#             )
        
#         # Update session (only context can be updated, file is immutable)
#         update_data = {}
#         if session_data.context is not None:
#             update_data["context"] = session_data.context
        
#         response = supabase.table("translation_sessions").update(update_data).eq("id", session_id).execute()
        
#         if response.data:
#             session = response.data[0]
#             return SessionSchema(
#                 id=session["id"],
#                 user_id=session["user_id"],
#                 main_file_path=session["main_file_path"],
#                 context=session["context"],
#                 created_at=session["created_at"],
#                 updated_at=session["updated_at"],
#             )
    
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error updating session: {str(e)}"
#         )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    authorization: Optional[str] = Header(None),
):
    """Delete a session and all its messages"""
    user_id = verify_token(authorization)
    session_service = SessionService()
    logger.info(f"Deleting session {session_id} for user {user_id}")
    
    try:
        # Verify ownership
        session = session_service.get_session(UUID(session_id))
        
        if str(session.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete session (messages will be deleted due to CASCADE)
        session_service.delete_session(UUID(session_id))
        logger.info(f"Session {session_id} deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}", exc_info=True)
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
    session_service = SessionService()
    logger.info(f"Fetching messages for session {session_id}")
    
    try:
        # Verify session exists and user owns it
        session = session_service.get_session(UUID(session_id))
        
        if str(session.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get messages using session_service
        messages = session_service.list_session_messages(UUID(session_id))
        
        return messages
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}", exc_info=True)
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
    session_service = SessionService()
    logger.info(f"Chat request in session {session_id} from user {user_id}")
    
    try:
        # Verify session exists and user owns it
        session = session_service.get_session(UUID(session_id))
        
        if str(session.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        local_file_path = FileStorageService.download_and_save_locally(session.main_file_path)
        logger.info(f"File saved locally at: {local_file_path}")
        
        # Save user message using session_service
        user_message = session_service.add_message_to_session(
            session_id=UUID(session_id),
            message=MessageCreate(
                role="user",
                content=chat_request.message,
                file_path=None
            )
        )
        
        # Get conversation history for context
        messages = session_service.list_session_messages(UUID(session_id))
        
        # Exclude the just-saved user message from conversation history
        conversation_history = messages[:-1] if messages else []
        
        chat_service = ChatService()
        
        # Process message with LLM
        agent_response = await chat_service.handle_user_message(
            user_message=chat_request.message,
            conversation_history=conversation_history,
            main_file_path=local_file_path
        )
        
        # Extract output file if available
        output_file = agent_response.get("output_file")
        supabase_output_path = None
        
        # Upload output file to Supabase if it exists
        if output_file:
            try:
                # Create Supabase path for output file
                output_filename = Path(output_file).name
                supabase_output_path = f"{user_id}/{session_id}/outputs/{output_filename}"
                
                # Upload to Supabase
                supabase_output_path = FileStorageService.upload_local_file_to_supabase(
                    local_file_path=output_file,
                    supabase_path=supabase_output_path
                )
                logger.info(f"Output file uploaded to Supabase: {supabase_output_path}")
            except Exception as e:
                logger.error(f"Error uploading output file to Supabase: {str(e)}", exc_info=True)
        
        # Save agent response message using session_service with Supabase path
        agent_message = session_service.add_message_to_session(
            session_id=UUID(session_id),
            message=MessageCreate(
                role="assistant",
                content=agent_response.get("response"),
                file_path=supabase_output_path
            )
        )
        
        if supabase_output_path:
            logger.info(f"Output file attached to agent response: {supabase_output_path}")
        
        logger.info(f"Chat completed successfully. User message ID: {user_message.id}, Agent message ID: {agent_message.id}")
        return ChatResponse(
            user_message=user_message,
            agent_response=agent_message,
            file_path=supabase_output_path,
            token_usage=agent_response.get("token_usage"),
            cost=agent_response.get("cost")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occured during chat"
        )
