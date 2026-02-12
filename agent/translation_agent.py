from tools.tool_registry import ToolRegistry
from tools.xlsx_tool import XLSXTranslateTool
from typing import List
from tools.base import BaseTool
import json
import openai
import os
from core.schemas.session import ChatRequest, ChatResponse, MessageSchema

class TranslationAgent:
    def __init__(self, model: str):

        api_key = os.getenv("OPENAI_API_KEY")
        self.tool_registry = ToolRegistry()
        # Register available tools
        self.tool_registry.register_tool(XLSXTranslateTool())
        # Add other tool registrations here

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def _build_system_prompt_with_tools(self, user_message: str) -> str:
        """Build system prompt with tool schemas formatted as JSON."""
        available_tools = self.tool_registry.list_tools()
        
        # Format tool schemas as JSON for clarity
        tools_json = json.dumps(
            list(available_tools.values()),
            indent=2
        )
        
        system_prompt = f"""You are a translation agent. Based on the user's message, decide which tools to use and in what order.

Available Tools:
{tools_json}

Instructions:
- Analyze the user's request to determine which tool(s) are needed
- Extract the required parameters for each tool from the user's message
- Plan a step-by-step sequence of tool calls (with arguments) to fulfill the request. 
- For each tool call, provide all required parameters. 
- Return a list of tool call plans in JSON format: [{'tool': ..., 'args': {{...}}}]. 
- If no tool is needed, return an empty list.

User Request: {user_message}
"""
        return system_prompt
    

    def build_history_messages(self, chat_history: List[str]) -> List[dict]:
        messages = []
        for i, msg in enumerate(chat_history):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})
        return messages


    def plan_tool_sequence(self, user_message: str, chat_history: List[MessageSchema]) -> List[BaseTool]:
        system_prompt = self._build_system_prompt_with_tools(user_message)
        
        if chat_history:
            history_messages = self.build_history_messages(chat_history)
            messages = [{"role": "system", "content": system_prompt}] + history_messages + [{"role": "user", "content": user_message}]
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        kwargs = {
            "model": self.model,
            "messages": messages
        }
        response = self.client.chat.completions.create(**kwargs)
        response_text = response.choices[0].message.content
        try:
            tool_plans = json.loads(response_text)
            return tool_plans
        except json.JSONDecodeError:
            raise ValueError("Failed to parse tool plan response as JSON.")

    def process_message(self, message: str, chat_history: List[MessageSchema]) -> str:
        """
        Process a user message by:
        1. Planning which tools to use (plan_tool_sequence)
        2. Executing the planned tools
        3. Returning a message with the results
        """
        tool_plans = self.plan_tool_sequence(message, chat_history)
        
        if not tool_plans:
            return "No tools needed for this request."
        
        results = []
        for plan in tool_plans:
            tool_name = plan.get("tool")
            tool_args = plan.get("args", {})
            try:
                result = self.tool_registry.execute_tool(tool_name, **tool_args)
                if result.get("success"):
                    results.append(f"✓ Tool '{tool_name}' executed successfully. Output file: {result.get('output_file')}")
                else:
                    results.append(f"✗ Tool '{tool_name}' execution failed. Status: {result.get('status')}")
            except Exception as e:
                results.append(f"✗ Error executing tool '{tool_name}': {str(e)}")
        
        return "\n\n".join(results)