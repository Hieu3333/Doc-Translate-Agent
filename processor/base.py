from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

class BaseDocumentProcessor(ABC):
    """Base class for document processors"""

    @abstractmethod
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def reconstruct_document(
        self, original_path: str, translated_content: Dict[str, Any], output_path: str
    ) -> str:
        pass

    