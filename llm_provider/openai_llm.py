"""
OpenAI LLM Provider for handling message processing and responses.
"""


import os
from typing import Optional, List
from dotenv import load_dotenv
import logging
from core.schemas.session import MessageSchema
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

        }
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from OpenAI provider"""
        return list(self.cost_table.keys())
    
    
    
    def calculate_cost(self, model: str, usage: dict) -> float:
        """Calculate cost based on token usage and model pricing."""
        if model not in self.cost_table:
            logger.warning(f"Model {model} not found in cost table. Cost will be set to 0.")
            return 0.0
        
        input_cost = usage.input_tokens * self.cost_table[model]["input"] / 1000
        output_cost = usage.output_tokens * self.cost_table[model]["output"] / 1000
        total_cost = input_cost + output_cost
        return round(total_cost, 6)
    
    def chat_completion(
        self,
        system_prompt: str,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        tools: Optional[List[dict]] = None,
    ) -> dict:
        """Send chat completion request to OpenAI API."""
        
        params = {
            "model": model,
            "instructions": system_prompt,
            "tools": tools, 
            "input": messages,
        }
        # GPT-5 models don't support temperature parameter
        if not model.startswith("gpt-5"):
            params["temperature"] = temperature

        tool_calls = []
        output_text = None
        response = self.client.responses.create(**params)
        for item in response.output:
            if item.type == "message":
                output_text = item.content[0].text
            # elif item.type == "reasoning":
            #     reasoning_text = item.content
            elif item.type == "function_call":
                tool_call = {
                    "id": item.call_id,
                    "function": {
                        "name": item.name,
                        "arguments": item.arguments
                    }
                }
                tool_calls.append(tool_call)
        
        response_usage = response.usage.model_dump() if response.usage else {"input_tokens": 0, "output_tokens": 0}


        return {
            "id": response.id,
            "output": response.output,
            "response": output_text,
            "tool_calls": tool_calls,
            "token_usage": response_usage,
            "cost": self.calculate_cost(model, response.usage)
        }



        

