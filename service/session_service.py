"""
Session service for handling session and message operations with database.
"""

from typing import List
from uuid import UUID

from core.database import get_supabase_client
from core.schemas.session import (
    SessionSchema,
    SessionWithMessages,
    MessageSchema,
    MessageCreate,
)


class SessionService:
    """Service for managing user sessions and messages"""
    
    def __init__(self):
        self.db = get_supabase_client()
    
    def create_session(self, user_id: UUID, main_file_path: str) -> SessionSchema:
        """
        Create a new translation session.
        
        Args:
            user_id: User ID
            main_file_path: Storage path of the uploaded file
            context: Optional context for translation
            
        Returns:
            SessionSchema: Created session
        """
        response = self.db.table("translation_sessions").insert({
            "user_id": str(user_id),
            "main_file_path": main_file_path,
        }).execute()
        
        if response.data:
            return SessionSchema(**response.data[0])
        raise Exception("Failed to create session")
    
    def get_session(self, session_id: UUID) -> SessionSchema:
        """
        Fetch session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionSchema: Session data
        """
        response = self.db.table("translation_sessions").select("*").eq("id", str(session_id)).execute()
        
        if response.data:
            return SessionSchema(**response.data[0])
        raise Exception(f"Session {session_id} not found")
    
    def get_session_with_messages(self, session_id: UUID) -> SessionWithMessages:
        """
        Fetch session with all its messages.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionWithMessages: Session data with messages
        """
        # Get session data
        session = self.get_session(session_id)
        
        # Get messages for this session
        messages = self.list_session_messages(session_id)
        
        return SessionWithMessages(
            id=session.id,
            user_id=session.user_id,
            main_file_path=session.main_file_path,
            context=None,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=messages
        )
    
    def list_session_messages(self, session_id: UUID) -> List[MessageSchema]:
        """
        Fetch all messages in a session ordered by creation time.
        
        Args:
            session_id: Session ID
            
        Returns:
            List[MessageSchema]: List of messages in the session
        """
        response = self.db.table("messages").select("*").eq("session_id", str(session_id)).order("created_at").execute()
        
        if response.data:
            return [MessageSchema(**msg) for msg in response.data]
        return []
    
    def get_message(self, message_id: UUID) -> MessageSchema:
        """
        Fetch a single message by ID.
        
        Args:
            message_id: Message ID
            
        Returns:
            MessageSchema: Message data
        """
        response = self.db.table("messages").select("*").eq("id", str(message_id)).execute()
        
        if response.data:
            return MessageSchema(**response.data[0])
        raise Exception(f"Message {message_id} not found")
    
    def add_message_to_session(self, session_id: UUID, message: MessageCreate) -> MessageSchema:
        """
        Add a message to a session.
        
        Args:
            session_id: Session ID
            message: Message data to add
            
        Returns:
            MessageSchema: Created message
        """
        insert_data = {
            "session_id": str(session_id),
            "role": message.role,
            "content": message.content,
            "file_path": message.file_path
        }
        
        # Include reasoning_content if provided
        if message.reasoning_content is not None:
            insert_data["reasoning_content"] = message.reasoning_content
        
        response = self.db.table("messages").insert(insert_data).execute()
        
        if response.data:
            return MessageSchema(**response.data[0])
        raise Exception("Failed to add message to session")
    
    def list_user_sessions(self, user_id: UUID) -> List[SessionSchema]:
        """
        Fetch all sessions for a user ordered by creation time (newest first).
        
        Args:
            user_id: User ID
            
        Returns:
            List[SessionSchema]: List of user sessions
        """
        response = self.db.table("translation_sessions").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).execute()
        
        if response.data:
            return [SessionSchema(**session) for session in response.data]
        return []
    
    def update_session(self, session_id: UUID, main_file_path: str) -> SessionSchema:
        """
        Update session data.
        
        Args:
            session_id: Session ID
            update_data: Fields to update
            
        Returns:
            SessionSchema: Updated session
        """
        response = self.db.table("translation_sessions").update({
            "main_file_path": main_file_path
        }).eq("id", str(session_id)).execute()
        
        
        if response.data:
            return SessionSchema(**response.data[0])
        raise Exception(f"Failed to update session {session_id}")
    
    def delete_session(self, session_id: UUID) -> bool:
        """
        Delete a session and all its messages.
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: Success status
        """
        response = self.db.table("translation_sessions").delete().eq("id", str(session_id)).execute()
        return len(response.data) > 0 or response.count == 0
    
    def get_message_count(self, session_id: UUID) -> int:
        """
        Get the number of messages in a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            int: Number of messages
        """
        response = self.db.table("messages").select("id").eq("session_id", str(session_id)).execute()
        return len(response.data) if response.data else 0    
    def update_message_file_path(self, message_id: UUID, file_path: str) -> MessageSchema:
        """
        Update a message's file path.
        
        Args:
            message_id: Message ID
            file_path: File path to attach to the message
            
        Returns:
            MessageSchema: Updated message
        """
        response = self.db.table("messages").update({
            "file_path": file_path
        }).eq("id", str(message_id)).execute()
        
        if response.data:
            return MessageSchema(**response.data[0])
        raise Exception(f"Failed to update message {message_id}")