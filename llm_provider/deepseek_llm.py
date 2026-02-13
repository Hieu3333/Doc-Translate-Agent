"""
DeepSeek LLM Provider for handling message processing and responses.
Compatible with OpenAI-style API.
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


class DeepSeekLLM:
    """Handler for DeepSeek API calls (OpenAI-compatible endpoint)"""

    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model = "deepseek-chat"

        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

        try:
            from openai import OpenAI
            # DeepSeek uses OpenAI-compatible endpoint
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
        except ImportError:
            raise ImportError("OpenAI library is not installed. Run: pip install openai")

        # DeepSeek pricing (adjust if official pricing changes)
        self.cost_table = {
            "deepseek-chat": {"input": 0.028, "output": 0.42},
            "deepseek-reasoner": {"input": 0.028, "output": 0.42},
        }

    def get_available_models(self) -> List[str]:
        """Get list of available DeepSeek models"""
        return list(self.cost_table.keys())

    def chat_completion(
        self,
        messages: List[dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[str] = None,
    ) -> dict:
        """Send chat completion request to DeepSeek API."""

        chosen_model = model if model else self.model

        api_params = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            api_params["max_tokens"] = max_tokens

        # Add tools if provided (DeepSeek supports OpenAI-style tools)
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = tool_choice if tool_choice else "auto"

        response = self.client.chat.completions.create(**api_params)

        # Extract response
        message = response.choices[0].message
        logger.info(f"DeepSeek LLM Response Message: {message}")

        output_text = message.content or ""
        
        # Extract reasoning_content if present (for deepseek-reasoner)
        reasoning_content = None
        if hasattr(message, 'reasoning_content') and message.reasoning_content:
            reasoning_content = message.reasoning_content

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

        cost = 0
        if chosen_model in self.cost_table:
            cost = (
                token_usage["input_tokens"]
                * self.cost_table[chosen_model]["input"]
                / 1_000_000
                + token_usage["output_tokens"]
                * self.cost_table[chosen_model]["output"]
                / 1_000_000
            )

        return {
            "response": output_text,
            "reasoning_content": reasoning_content,
            "tool_calls": tool_calls,
            "token_usage": token_usage,
            "cost": cost
        }
