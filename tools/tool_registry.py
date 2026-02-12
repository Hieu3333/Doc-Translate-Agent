from .base import BaseTool
from typing import Dict
class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict:
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        return tool.execute(**kwargs)
    def get_tool_schema(self, tool_name: str) -> Dict:
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        return tool.get_schema()
    
    def list_tools(self) -> Dict[str, str]:
        return {name: tool.get_schema() for name, tool in self.tools.items()}
    
    def set_context(self, main_file_path: str, model: str = None) -> None:
        for tool in self.tools.values():
            tool.set_content(main_file_path, model)