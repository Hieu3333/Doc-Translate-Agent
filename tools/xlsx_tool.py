from tools.base import BaseTool
from typing import Dict, Any
from processor.xlsx_processor import XLSXProcessor
from translator.openai_translator import OpenaiTranslator

class XLSXTranslateTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="xlsx_translate",
            description="Translate the content of an XLSX file to a specified target language."
        )
    
    def execute(self, main_file_path: str , context: str, source_language: str, target_language: str, sheet_idx_to_translate=None) -> Dict[str, Any]:
        try:
            processor = XLSXProcessor()
            translator = OpenaiTranslator()
            extracted_content = processor.extract_text(main_file_path, sheet_idx_to_translate)
            translatable_texts = processor.get_translatable_texts(extracted_content)
            translated_texts = translator.translate_texts(translatable_texts, context, source_language=source_language, target_language=target_language)
            translated_content = processor.apply_translations(extracted_content, translated_texts)
            output_file = processor.reconstruct_document(main_file_path, translated_content)
            return {
                "output_file": output_file,
                "status": "Translation completed successfully.",
                "success": True
                }
        except Exception as e:
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
                    "main_file_path": {
                        "type": "string",
                        "description": "Path to the main XLSX file to be translated."
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional document context for consistent translation."
                    },
                    "source_language": {
                        "type": ["string","auto"],
                        "description": "Source language of the document."
                    },
                    "target_language": {
                        "type": "string",
                        "description": "Target language for translation."
                    },
                    "sheet_idx_to_translate": {
                        "type": ["integer", "null"],
                        "description": "Optional index of the sheet to translate. If null, all sheets will be translated."
                    }
                },
                "required": ["main_file_path", "source_language", "target_language"]
            }
        }
        



# class XLSXSearchTool(BaseTool):

# class XLSXPreviewTool(BaseTool):

# class XLSXGetSheetContentTool(BaseTool):

# class XLSXReplaceTool(BaseTool):
