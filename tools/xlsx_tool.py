from tools.base import BaseTool
from typing import Dict, Any, List
from processor.xlsx_processor import XLSXProcessor
from translator.openai_translator import OpenaiTranslator
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class XLSXTranslateTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="xlsx_translate",
            description="Translate the content of an XLSX file to a specified target language. This tool already has access to the file content."
        )

    
    def execute(self, source_language: str, target_language: str, context: str = "", sheet_idx_to_translate: List[int] = None) -> Dict[str, Any]:
        try:
            logger.info(f"Starting XLSX translation: source={source_language}, target={target_language}, model={self.model}")
            
            processor = XLSXProcessor()
            translator = OpenaiTranslator()
            # Convert empty list to None for consistency
            sheet_indices = [str(idx) for idx in sheet_idx_to_translate] if sheet_idx_to_translate else None
            logger.info(f"Extracting text from file: {self.main_file_path}")
            
            extracted_content = processor.extract_text(self.main_file_path, sheet_indices)
            translatable_texts = processor.get_translatable_texts(extracted_content)
            logger.info(f"Found {len(translatable_texts)} translatable texts")
            
            # Use self.model which is set by the agent via set_context
            logger.info(f"Translating texts with model: {self.model}")
            translated_data = translator.translate_texts(
                texts=translatable_texts, 
                context=context, 
                source_language=source_language, 
                target_language=target_language, 
                model=self.model
            )
            
            logger.info(f"Translation response type: {type(translated_data)}, keys: {translated_data.keys() if isinstance(translated_data, dict) else 'N/A'}")
            translated_texts = translated_data["translations"]
            
            logger.info(f"Applying translations to document")
            translated_content = processor.apply_translations(extracted_content, translated_texts)
            
            # Generate output file name with original extension
            input_path = Path(self.main_file_path)
            file_name = input_path.stem
            file_extension = input_path.suffix
            output_filename = f"{file_name}_translated{file_extension}"
            output_path = str(Path("outputs") / output_filename)
            
            output_file = processor.reconstruct_document(self.main_file_path, translated_content, output_path)
            
            logger.info(f"Translation completed successfully. Output file: {output_file}")
            return {
                "output_file": output_file,
                "translation_cost": translated_data["total_cost"],
                "status": "Translation completed successfully.",
                "success": True
                }
        except Exception as e:
            logger.error(f"Error in XLSX translation: {str(e)}", exc_info=True)
            return {
                "status": f"Error occured during translation: {str(e)}",
                "success": False
            }
    
    def get_schema(self) -> Dict[str, Any]: 
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "source_language": {
                        "type": "string",
                        "description": "Source language of the document (e.g., 'English', 'auto' for auto-detection)."
                    },
                    "target_language": {
                        "type": "string",
                        "description": "Target language for translation (e.g., 'Spanish', 'French')."
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional document context for better translation.",
                        "default": ""
                    },
                    "sheet_idx_to_translate": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of sheet indices to translate. Sheets indices start from 1. If not provided, all sheets will be translated.",
                        "default": []
                    }
                },
                "required": ["source_language", "target_language", "context", "sheet_idx_to_translate"],
                "additionalProperties": False
            }
        }
        



# class XLSXSearchTool(BaseTool):

# class XLSXPreviewTool(BaseTool):

# class XLSXGetSheetContentTool(BaseTool):

# class XLSXReplaceTool(BaseTool):
