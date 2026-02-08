from llm_provider.openai_llm import OpenAILLM
from typing import Optional, List

class ChatService:
    def __init__(self):
        self.llm = OpenAILLM()
    
    async def handle_user_message(
        self,
        user_message: str,
        session_context: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        Handle user message by processing it through the LLM.
        
        Args:
            user_message: The user's input message
            session_context: Optional context for the translation/task
            conversation_history: Optional list of previous messages for context
        
        Returns:
            The agent's response message
        """
        response = await self.llm.process_message(
            user_message=user_message,
            session_context=session_context,
            conversation_history=conversation_history
        )
        return response