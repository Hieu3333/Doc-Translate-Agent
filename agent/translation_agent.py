import logging
import re
from tools.tool_registry import ToolRegistry
from tools.xlsx_tool import XLSXTranslateTool, XLSXExtractStructureTool, XLSXSearchTool
from typing import List, Dict
from tools.base import BaseTool
import json
from llm_provider.openai_llm import OpenAILLM
from llm_provider.deepseek_llm import DeepSeekLLM
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
        self.tool_registry.register_tool(XLSXExtractStructureTool())
        self.tool_registry.register_tool(XLSXTranslateTool())
        self.tool_registry.register_tool(XLSXSearchTool())
        # Add other tool registrations here

        self.openai_llm_provider = OpenAILLM()
        self.deepseek_llm_provider = DeepSeekLLM()
        self.master_language = master_language
        self.available_tools = {
            "xlsx": {"extract_structure": "xlsx_extract_structure", "translate": "xlsx_translate"},
        }

    def _build_system_prompt_for_planning(self) -> str:
        """Build system prompt for tool planning."""
        system_prompt = f"""You are a translation agent. You help translate the main document file. Note that the tools have access to the file content. 
        Decide which tools to use.

IMPORTANT: You must respond to the user ONLY in {self.master_language}.

Use the available tools to fulfill the user's request. If the user wants to translate the file, call the translate tool. Do not respond by saying you dont have access to the file - the tools have access.
Always respond in {self.master_language}, regardless of the language used in the user's request.
"""
        return system_prompt
    
    def _build_system_prompt_for_summarization(self) -> str:
        system_prompt = f"""You are a helpful translation agent. Respond in {self.master_language}.
        Based on the tool execution results below, generate a short, user-facing confirmation message. If there are many tool execution results, summarize them in a concise way."""
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
                
                # Handle reasoning_content for deepseek-reasoner models
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    openai_message["reasoning_content"] = message.reasoning_content
                
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
        system_prompt = self._build_system_prompt_for_planning()

        if model in self.openai_llm_provider.get_available_models():
            self.llm_provider = self.openai_llm_provider
        elif model in self.deepseek_llm_provider.get_available_models():
            self.llm_provider = self.deepseek_llm_provider

        # logger.info(f"Planning tool sequence with message: {user_message[:50]}...")
        
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
                        "id": tc['id'],
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
        # Set context for tools
        file_extension = main_file_path.split('.')[-1].lower()

        if model in self.openai_llm_provider.get_available_models():
            self.llm_provider = self.openai_llm_provider
        elif model in self.deepseek_llm_provider.get_available_models():
            self.llm_provider = self.deepseek_llm_provider
      

        self.tool_registry.set_context(main_file_path, model)
        logger.info(f"Tool registry context set to: {main_file_path} with model: {model}")
      
    
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

        output_files = []
        tool_messages = []
        tool_calls_list = []
        
        for plan in tool_plans:
            tool_call_id = plan.get("id")
            tool_name = plan.get("tool")
            tool_args = plan.get("args", {})
            
            # Reconstruct tool_calls format for assistant message
            tool_calls_list.append({
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(tool_args)
                }
            })
            
            try:
                logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")
                result = self.tool_registry.execute_tool(tool_name, **tool_args)
                if result.get("success"):
                    output_file = result.get("output_file")
                    if output_file:
                        output_files.append(output_file)
                    
                    # Build tool result message
                    tool_status = f"Tool: {tool_name}\nStatus: {result.get('status')}"
                    if result.get("result"):
                        tool_status += f"\nResult: {result.get('result')}"
                    
                    tool_messages.append({
                        "role": "tool", 
                        "tool_call_id": tool_call_id,
                        "content": tool_status
                    })
                    logger.info(f"Tool '{tool_name}' executed successfully")
                else:
                    # Add error message as tool result
                    tool_messages.append({
                        "role": "tool", 
                        "tool_call_id": tool_call_id,
                        "content": f"Tool: {tool_name}\nStatus: {result.get('status')}"
                    })
                    logger.warning(f"Tool '{tool_name}' execution failed: {result.get('status')}")
            except Exception as e:
                tool_messages.append({
                    "role": "tool", 
                    "tool_call_id": tool_call_id,
                    "content": f"Tool: {tool_name}\nStatus: Error executing tool - {str(e)}"
                })
                logger.error(f"Error executing tool '{tool_name}': {str(e)}", exc_info=True)
        
        # Build messages with system prompt, chat history, user message, assistant message with tool_calls, and tool results
        system_prompt = self._build_system_prompt_for_summarization()
        
        history_for_api = self.build_messages(chat_history) if chat_history else []
        
        # Build assistant message - add reasoning_content for deepseek-reasoner model
        assistant_message = {"role": "assistant", "tool_calls": tool_calls_list}
        if model == "deepseek-reasoner":
            assistant_message["reasoning_content"] = ""
        
        summary_messages = [
            {"role": "system", "content": system_prompt}
        ] + history_for_api + [
            {"role": "user", "content": message},
            assistant_message
        ] + tool_messages
        
        summary_response = self.llm_provider.chat_completion(
            model=model,
            messages=summary_messages
        )
        output_text = summary_response["response"]
        reasoning_content = summary_response.get("reasoning_content")
        token_usage = summary_response.get("token_usage")
        cost = summary_response.get("cost")
        
        # Return first output file if available
        output_file = output_files[0] if output_files else None
        
        return {
            "response": output_text,
            "reasoning_content": reasoning_content,
            "token_usage": token_usage,
            "cost": cost,
            "output_file": output_file
        }