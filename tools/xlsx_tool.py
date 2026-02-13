from tools.base import BaseTool
from typing import Dict, Any, List
from processor.xlsx_processor import XLSXProcessor
from translator.openai_translator import OpenaiTranslator
from translator.deepseek_translator import DeepseekTranslator
from core.schemas.tool import ToolResponseSchema
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class XLSXExtractStructureTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="xlsx_extract_structure",
            description="Extract and return the structure of an XLSX file including sheet names, IDs, and total sheet count. Use this to understand the file structure before deciding which sheets to translate."
        )

    def execute(self) -> Dict[str, Any]:
        try:
            logger.info(f"Extracting structure from file: {self.main_file_path}")
            
            processor = XLSXProcessor()
            structure = processor.extract_structure(self.main_file_path)
            
            logger.info(f"File structure extracted: {structure}")
            return ToolResponseSchema(
                status="Structure extracted successfully.",
                success=True,
                tool=self.name,
                result=structure
            ).model_dump()
        except Exception as e:
            logger.error(f"Error extracting XLSX structure: {str(e)}", exc_info=True)
            return ToolResponseSchema(
                status=f"Error occured during structure extraction",
                success=False,
                tool=self.name
            ).model_dump()

    def get_schema(self) -> Dict[str, Any]: 
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }


class XLSXTranslateTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="xlsx_translate",
            description="Translate the content of an XLSX file to a specified target language. This tool already has access to the file content."
        )

    
    def execute(self, source_language: str, target_language: str, context: str = "") -> Dict[str, Any]:
        try:
            logger.info(f"Starting XLSX translation: source={source_language}, target={target_language}, model={self.model}")
            
            processor = XLSXProcessor()
            
            # Select translator based on model
            if self.model.startswith("deepseek"):
                translator = DeepseekTranslator()
                logger.info("Using Deepseek translator")
            else:
                translator = OpenaiTranslator()
                logger.info("Using OpenAI translator")
            
            logger.info(f"Extracting text from file: {self.main_file_path}")
            
            extracted_content = processor.extract_text(self.main_file_path)
            all_translatable_texts = processor.get_translatable_texts(extracted_content)
            logger.info(f"Translatable texts: {all_translatable_texts}")

            # Use self.model which is set by the agent via set_context
            logger.info(f"Before translation: {all_translatable_texts}")
            translated_data = translator.translate_texts(
                texts=list(all_translatable_texts.values()), 
                context=context, 
                source_language=source_language, 
                target_language=target_language, 
                model=self.model
            )
            
            logger.info(f"After translation: {translated_data}")
            translated_text_list = translated_data["translations"]
            
            # Map translations back to their keys
            final_translations = {}
            for key, translated_text in zip(all_translatable_texts.keys(), translated_text_list):
                final_translations[key] = translated_text
            
            translated_content = processor.apply_translations(extracted_content, final_translations)
            logger.info(f"\nTranslated content: {translated_content}")
            
            # Generate output file name with original extension
            input_path = Path(self.main_file_path)
            file_name = input_path.stem
            file_extension = input_path.suffix
            output_filename = f"{file_name}_translated{file_extension}"
            output_path = str(Path("data/output") / output_filename)
            
            output_file = processor.reconstruct_document(self.main_file_path, translated_content, output_path)
            
            logger.info(f"Translation completed successfully. Output file: {output_file}")
            return ToolResponseSchema(
                status="Translation completed successfully.",  
                success=True,
                tool=self.name,
                output_file=output_file,  
            ).model_dump()
        except Exception as e:
            logger.error(f"Error in XLSX translation: {str(e)}", exc_info=True)
            return ToolResponseSchema(
                status="Error occured during translation",
                success=False,
                tool=self.name
            ).model_dump()
    
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
                    }
                },
                "required": ["source_language", "target_language", "context"],
                "additionalProperties": False
            }
        }
        

class XLSXSearchTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="xlsx_search",
            description="Search for a word or phrase in the XLSX file and return all occurrences with their positions (sheet, cell, etc.)."
        )

    def execute(self, query: str, case_sensitive: bool = False) -> Dict[str, Any]:
        try:
            logger.info(f"Starting XLSX search: query='{query}', case_sensitive={case_sensitive}")
            
            processor = XLSXProcessor()
            
            logger.info(f"Extracting text from file: {self.main_file_path}")
            extracted_content = processor.extract_text(self.main_file_path)
            
            # Search through all sheets
            search_results = []
            query_lower = query.lower() if not case_sensitive else query
            
            for sheet_idx, sheet in enumerate(extracted_content.get('sheets', []), start=1):
                sheet_name = sheet.get('name', f'Sheet {sheet_idx}')
                
                # Search in sheet data (cells)
                for data in sheet.get('data', []):
                    cell_ref = data.get('cell', '')
                    text_chunks = data.get('text', [])
                    
                    # Handle text chunks (for rich text)
                    if isinstance(text_chunks, list):
                        for chunk_idx, chunk_text in enumerate(text_chunks):
                            chunk_str = str(chunk_text)
                            search_str = chunk_str.lower() if not case_sensitive else chunk_str
                            
                            if query_lower in search_str:
                                # Find the position(s) of the match
                                positions = []
                                search_pos = 0
                                while True:
                                    pos = search_str.find(query_lower, search_pos)
                                    if pos == -1:
                                        break
                                    positions.append(pos)
                                    search_pos = pos + 1
                                
                                for pos in positions:
                                    search_results.append({
                                        "sheet_index": sheet_idx,
                                        "sheet_name": sheet_name,
                                        "cell": cell_ref,
                                        "text": chunk_str,
                                        "chunk_index": chunk_idx + 1,
                                        "position": pos,
                                        "match_length": len(query)
                                    })
                    else:
                        # Handle single text value
                        text_str = str(text_chunks)
                        search_str = text_str.lower() if not case_sensitive else text_str
                        
                        if query_lower in search_str:
                            positions = []
                            search_pos = 0
                            while True:
                                pos = search_str.find(query_lower, search_pos)
                                if pos == -1:
                                    break
                                positions.append(pos)
                                search_pos = pos + 1
                            
                            for pos in positions:
                                search_results.append({
                                    "sheet_index": sheet_idx,
                                    "sheet_name": sheet_name,
                                    "cell": cell_ref,
                                    "text": text_str,
                                    "position": pos,
                                    "match_length": len(query)
                                })
            
            logger.info(f"Search completed. Found {len(search_results)} occurrences")
            
            return ToolResponseSchema(
                status=f"Search completed. Found {len(search_results)} occurrence(s) of '{query}'.",
                success=True,
                tool=self.name,
                result={"matches": search_results, "total": len(search_results)}
            ).model_dump()
        except Exception as e:
            logger.error(f"Error in XLSX search: {str(e)}", exc_info=True)
            return ToolResponseSchema(
                status=f"Error occurred during search: {str(e)}",
                success=False,
                tool=self.name
            ).model_dump()
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The word or phrase to search for in the XLSX file."
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search should be case-sensitive. Default is False.",
                        "default": False
                    }
                },
                "required": ["query", "case_sensitive"],
                "additionalProperties": False
            }
        }

# class XLSXGetSheetContentTool(BaseTool):

# class XLSXReplaceTool(BaseTool):
