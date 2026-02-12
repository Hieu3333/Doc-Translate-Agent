from abc import ABC, abstractmethod
from typing import Any, Dict
class BaseTool(ABC):    
    def __init__(self, name: str, description: str, main_file_path: str = None):
        self.name = name
        self.description = description
        self.main_file_path = main_file_path
        self.model = "gpt-4o-mini"  # Default model
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI function calling schema"""
        pass

    def set_content(self, main_file_path: str, model: str = None) -> None:
        self.main_file_path = main_file_path
        if model:
            self.model = model