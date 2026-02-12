from tools.tool_registry import ToolRegistry
from tools.xlsx_tool import XLSXTranslateTool
from typing import List
from tools.base import BaseTool
import json
import openai
import os
from core.schemas.session import ChatRequest, ChatResponse, MessageSchema

class TranslationAgent:
    def __init__(self, model: str, master_language: str = "English"):
        """
        Initialize the Translation Agent.
        
        Args:
            model: The LLM model to use (e.g., 'gpt-4')
            master_language: The language the agent will use when interacting with the user
        """
        api_key = os.getenv("OPENAI_API_KEY")
        self.tool_registry = ToolRegistry()
        # Register available tools
        self.tool_registry.register_tool(XLSXTranslateTool())
        # Add other tool registrations here

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.master_language = master_language

    def _build_system_prompt_with_tools(self, user_message: str) -> str:
        """Build system prompt with tool schemas formatted as JSON."""
        available_tools = self.tool_registry.list_tools()
        
        # Format tool schemas as JSON for clarity
        tools_json = json.dumps(
            list(available_tools.values()),
            indent=2
        )
        
        system_prompt = f"""You are a translation agent. Based on the user's message, decide which tools to use and in what order.

IMPORTANT: You must interact and respond to the user ONLY in {self.master_language}.

Available Tools:
{tools_json}

Instructions:
- Analyze the user's request to determine which tool(s) are needed
- Extract the required parameters for each tool from the user's message
- Plan a step-by-step sequence of tool calls (with arguments) to fulfill the request. 
- For each tool call, provide all required parameters. 
- Return a list of tool call plans in JSON format: [{'tool': ..., 'args': {{...}}}]. 
- If no tool is needed, return an empty list.
- Always respond to the user in {self.master_language}, regardless of the language used in the user's request.

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
        3. Returning a message with the results in the master language
        """
        tool_plans = self.plan_tool_sequence(message, chat_history)
        
        if not tool_plans:
            return f"I understand your request. However, no tools are needed to fulfill it. Could you please provide more details? (Response in {self.master_language})"
        
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
        
        # Summarize results in master language
        results_summary = "\n\n".join(results)
        summary_prompt = f"""Based on the following tool execution results, provide a summary in {self.master_language}:

Tool Execution Results:
{results_summary}

Please acknowledge the completion and summarize what was accomplished."""
        
        summary_messages = [
            {"role": "system", "content": f"You are a helpful translation agent. Respond in {self.master_language}."},
            {"role": "user", "content": summary_prompt}
        ]
        
        summary_response = self.client.chat.completions.create(
            model=self.model,
            messages=summary_messages
        )
        
        final_response = summary_response.choices[0].message.content
        return final_response