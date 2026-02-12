import logging
import re
from tools.tool_registry import ToolRegistry
from tools.xlsx_tool import XLSXTranslateTool
from typing import List
from tools.base import BaseTool
import json
from llm_provider.openai_llm import OpenAILLM
from core.schemas.session import MessageSchema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
class TranslationAgent:
    def __init__(self, master_language: str = "English"):
        """
        Initialize the Translation Agent.
        
        Args:
            model: The LLM model to use (e.g., 'gpt-4')
            master_language: The language the agent will use when interacting with the user
        """

        self.tool_registry = ToolRegistry()
        # Register available tools
        self.tool_registry.register_tool(XLSXTranslateTool())
        # Add other tool registrations here

        self.llm_provider = OpenAILLM()
        self.master_language = master_language

    def _build_system_prompt_for_planning(self, user_message: str) -> str:
        """Build system prompt for tool planning."""
        system_prompt = f"""You are a translation agent. You help translate the main document file. Note that the tools have access to the file. Based on the user's message, decide which tools to use.

IMPORTANT: You must respond to the user ONLY in {self.master_language}.

Use the available tools to fulfill the user's request. If the user wants to translate the file, call the translate tool. Do not respond by saying you dont have access to the file - the tools have access.
Always respond in {self.master_language}, regardless of the language used in the user's request.
"""
        return system_prompt
    
    def _build_tools(self) -> List[dict]:
        """
        Build the tools for the OpenAI API.

        Returns:
            List[dict]: List of dictionaries representing the tools.
        """
        available_tools = self.tool_registry.list_tools()
        openai_tools = []
        
        for tool_name, tool_schema in available_tools.items():
            # tool_schema already has name, description, and parameters from get_schema()
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool_schema.get("name"),
                    "description": tool_schema.get("description"),
                    "parameters": tool_schema.get("parameters", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }),
                    "strict": True
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools

    def build_messages(self, messages: List) -> List[dict]:
        """
        Build the messages for the OpenAI API.

        Args:
            messages (List): List of messages to build (can be strings or MessageSchema objects).

        Returns:
            List[dict]: List of dictionaries representing the messages.
        """
        openai_messages = []
        for message in messages:
            # Handle different message types
            if isinstance(message, str):
                openai_message = {
                    "role": "user",
                    "content": message
                }
            elif isinstance(message, dict):
                openai_message = message
            else:
                # Handle MessageSchema or similar objects
                role = getattr(message, 'role', 'user')
                content = getattr(message, 'content', str(message))
                
                openai_message = {
                    "role": role,
                    "content": content
                }
                
                # Handle tool calls if present
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    openai_message["tool_calls"] = []
                    for tool_call in message.tool_calls:
                        tool_call_dict = {
                            "id": tool_call.get("id") if isinstance(tool_call, dict) else tool_call.id,
                            "function": {
                                "arguments": json.dumps(tool_call.get("arguments") if isinstance(tool_call, dict) else tool_call.arguments, ensure_ascii=False),
                                "name": tool_call.get("name") if isinstance(tool_call, dict) else tool_call.name,
                            },
                            "type": "function"
                        }
                        openai_message["tool_calls"].append(tool_call_dict)
            
            openai_messages.append(openai_message)
        
        return openai_messages


    def plan_tool_sequence(self, user_message: str, chat_history: List[MessageSchema], model: str) -> List[dict]:
        """Plan tool sequence using OpenAI's native tool calling feature."""
        system_prompt = self._build_system_prompt_for_planning(user_message)

        logger.info(f"Planning tool sequence with message: {user_message[:50]}...")
        
        # Build messages from history and current user message
        history_for_api = self.build_messages(chat_history) if chat_history else []
        messages = [{"role": "system", "content": system_prompt}] + history_for_api + [{"role": "user", "content": user_message}]
        
        # Get available tools in OpenAI format
        openai_tools = self._build_tools()
        
        if not openai_tools:
            logger.warning("No tools available for planning")
            return []
        
        # Call LLM with tool definitions
        response_data = self.llm_provider.chat_completion(
            messages=messages,
            model=model,
            tools=openai_tools,
            tool_choice="auto"
        )
        
        # Extract tool calls from response
        tool_calls = response_data.get("tool_calls", [])
        
        if tool_calls:
            logger.info(f"Tool calls planned: {[tc['function']['name'] for tc in tool_calls]}")
            # Convert OpenAI tool calls to our format
            tool_plans = []
            for tc in tool_calls:
                try:
                    args = json.loads(tc['function']['arguments']) if isinstance(tc['function']['arguments'], str) else tc['function']['arguments']
                    tool_plans.append({
                        "tool": tc['function']['name'],
                        "args": args
                    })
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {tc['function']['arguments']}")
            return tool_plans
        else:
            logger.info("No tool calls in response")
            return []

    def process_message(self, message: str, main_file_path: str, chat_history: List[MessageSchema], model: str) -> dict:
        """
        Process a user message by:
        1. Planning which tools to use (plan_tool_sequence)
        2. If tools are needed, execute them and summarize results
        3. If no tools needed, respond as a normal chat
        """
        tool_plans = self.plan_tool_sequence(message, chat_history, model)
        logger.info(f"Planned tool sequence: {[plan.get('tool') for plan in tool_plans]}")
        
        if not tool_plans:
            # No tools needed - respond as normal chat
            logger.info("No tools needed, responding with normal chat")
            
            system_prompt = f"You are a helpful translation agent. Respond to the user in {self.master_language}."
            
            # Build messages with conversation history using build_messages()
            history_for_api = self.build_messages(chat_history) if chat_history else []
            chat_messages = [{"role": "system", "content": system_prompt}] + history_for_api + [{"role": "user", "content": message}]
            
            response_data = self.llm_provider.chat_completion(
                model=model,
                messages=chat_messages
            )
            
            return {
                "response": response_data.get("response", ""),
                "token_usage": response_data.get("token_usage", {}),
                "cost": response_data.get("cost", 0.0)
            }
        
        results = []
        output_files = []
        # Set context once for all tools with the model
        self.tool_registry.set_context(main_file_path, model)
        logger.info(f"Tool registry context set to: {main_file_path} with model: {model}")
        
        for plan in tool_plans:
            tool_name = plan.get("tool")
            tool_args = plan.get("args", {})
            
            try:
                logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")
                result = self.tool_registry.execute_tool(tool_name, **tool_args)
                if result.get("success"):
                    output_file = result.get("output_file")
                    if output_file:
                        output_files.append(output_file)
                    results.append(f"✓ Tool '{tool_name}' executed successfully. Output file: {output_file}")
                    logger.info(f"Tool '{tool_name}' executed successfully")
                else:
                    results.append(f"✗ Tool '{tool_name}' execution failed. Status: {result.get('status')}")
                    logger.warning(f"Tool '{tool_name}' execution failed: {result.get('status')}")
            except Exception as e:
                results.append(f"✗ Error executing tool '{tool_name}': {str(e)}")
                logger.error(f"Error executing tool '{tool_name}': {str(e)}", exc_info=True)
        
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
        
        summary_response = self.llm_provider.chat_completion(
            model=model,
            messages=summary_messages
        )
        output_text = summary_response["response"]
        token_usage = summary_response.get("token_usage")
        cost = summary_response.get("cost")
        
        # Return first output file if available
        output_file = output_files[0] if output_files else None
        
        return {
            "response": output_text,
            "token_usage": token_usage,
            "cost": cost,
            "output_file": output_file
        }