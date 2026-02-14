from core.schemas.session import MessageSchema
from llm_provider.openai_llm import OpenAILLM
from typing import Optional, List
from agent.translation_agent import TranslationAgent

import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, master_language: str = "English"):
        self.translation_agent = TranslationAgent(master_language=master_language)
    
    async def handle_user_message(
        self,
        user_message: str,
        main_file_path: str,
        conversation_history: Optional[List[MessageSchema]] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> dict:
        
        """
        Handle a user message by processing it through the Translation Agent.
        
        Args:
            user_message: The message sent by the user
            main_file_path: Supabase path to the main file for the session
            conversation_history: Optional list of past messages in the conversation as MessageSchema objects
            model: The language model to use for processing the message
        Returns:
            dict: The agent's response to the user's message along with token usage, cost, and optional output_file
        """
        
        # Download file from Supabase and save locally for processing
       
       
        result = self.translation_agent.process_message(
            message=user_message,
            main_file_path=main_file_path,
            chat_history=conversation_history or [],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return {
            "response": result.get("response"),
            "token_usage": result.get("token_usage"),
            "cost": result.get("cost"),
            "output_file": result.get("output_file")
        }
        