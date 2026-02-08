"""
OpenAI LLM Provider for handling message processing and responses.
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


class OpenAILLM:
    """Handler for OpenAI API calls"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = "gpt-4o-mini"
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("OpenAI library is not installed. Run: pip install openai")
    
    async def process_message(
        self,
        user_message: str,
        session_context: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> str:
        """
        Process user message with OpenAI and return agent response.
        
        Args:
            user_message: The user's input message
            session_context: Optional context for the translation/task
            session_main_file_path: Optional path to the main file being processed
            conversation_history: Optional list of previous messages for context
        
        Returns:
            The agent's response message
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(
                session_context=session_context,
            )
            
            # Build message list
            messages = self._build_messages(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=conversation_history
            )
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Extract response text
            agent_response = response.choices[0].message.content
            
            return agent_response
        
        except Exception as e:
            # Return error message instead of raising
            return f"Error processing message with LLM: {str(e)}"
    
    def _build_system_prompt(
        self,
        session_context: Optional[str] = None,
    ) -> str:
        """
        Build the system prompt for the LLM.
        
        Args:
            session_context: Optional context for the task
            session_main_file_path: Optional path to the main file
        
        Returns:
            The system prompt string
        """
        prompt = "You are a helpful AI assistant for document translation and processing."
        
        if session_context:
            prompt += f"\n\nSession Context: {session_context}"
        
        
        prompt += "\n\nProvide clear, concise, and helpful responses."
        
        return prompt
    
    def _build_messages(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> List[dict]:
        """
        Build the messages list for the OpenAI API.
        
        Args:
            system_prompt: The system prompt
            user_message: The current user message
            conversation_history: Optional list of previous messages
        
        Returns:
            List of message dictionaries for the API
        """
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
