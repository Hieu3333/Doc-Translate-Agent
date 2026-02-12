"""
OpenAI LLM Provider for handling message processing and responses.
"""


import os
from typing import Optional, List
from dotenv import load_dotenv
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
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
        
        self.cost_table = {
            # GPT-5 family
            "gpt-5.2":         {"input": 1.75,  "output": 14.00},  
            "gpt-5.2-pro":     {"input": 21.0,  "output": 168.0},  
            "gpt-5-mini":      {"input": 0.25,  "output": 2.00},   

            # GPT-5 and GPT-5.1 variants (community / docs indicate similar pricing)
            "gpt-5":           {"input": 1.25,  "output": 10.00},  
            "gpt-5.1":         {"input": 1.25,  "output": 10.00},  
            "gpt-5-nano":      {"input": 0.05,  "output": 0.40},   

            # GPT-4.1 family
            "gpt-4.1":         {"input": 2.00,  "output": 8.00},   
            "gpt-4.1-mini":    {"input": 0.40,  "output": 1.60},   
            "gpt-4.1-nano":    {"input": 0.10,  "output": 0.40},   

            # GPT-4o family
            "gpt-4o-mini":     {"input": 0.15,  "output": 0.60},   
            "gpt-4o":          {"input": 2.50,  "output": 10.00},  

            # Realtime API models
            "gpt-realtime":         {"input": 4.00, "output": 16.00},  
            "gpt-realtime-mini":    {"input": 0.60, "output": 2.40}

        }
    
    def chat_completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> dict:
        """Send chat completion request to OpenAI API."""
        chosen_model = model if model else self.model
        
        # GPT-5 models don't support temperature parameter
        is_gpt5 = chosen_model.startswith("gpt-5")
        
        api_params = {
            "model": chosen_model,
            "messages": messages,
        }
        
        if not is_gpt5:
            api_params["temperature"] = temperature
        
        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens
        
        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            # If tools are provided, set tool_choice (default to "auto")
            api_params["tool_choice"] = tool_choice if tool_choice else "auto"
        
        response = self.client.chat.completions.create(**api_params)
        
        # Extract response data
        message = response.choices[0].message
        logger.info(f"LLM Response Message: {message}")
        output_text = message.content or ""
        
        # Extract tool calls if present
        tool_calls = []
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = [
                {
                    "id": call.id,
                    "type": call.type,
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }
                for call in message.tool_calls
            ]
        
        token_usage = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
        cost = token_usage["input_tokens"] * self.cost_table[chosen_model]["input"] / 1_000_000 + \
               token_usage["output_tokens"] * self.cost_table[chosen_model]["output"] / 1_000_000
        
        return {
            "response": output_text,
            "tool_calls": tool_calls,
            "token_usage": token_usage,
            "cost": cost
        }