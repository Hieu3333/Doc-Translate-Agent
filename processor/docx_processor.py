import zipfile
from lxml import etree
from pathlib import Path
from typing import Any, Dict, List

import re
import shutil

EXTRACT_DIR = "tmp"

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def recompile(extracted_dir: Path, output_xlsx: Path):
    """
    Rebuild an XLSX file from an extracted directory.
    """

    with zipfile.ZipFile(output_xlsx, "w", zipfile.ZIP_DEFLATED) as z:
        for file_path in extracted_dir.rglob("*"):
            if file_path.is_file():
                # IMPORTANT: keep relative path
                arcname = file_path.relative_to(extracted_dir)
                z.write(file_path, arcname) 
                
                

def unzip(xlsx_path: Path, extract_dir: Path) -> None:
    """
    Unzip an XLSX file into extract_dir.
    """
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(xlsx_path, "r") as z:
        z.extractall(extract_dir)    





class DOCXProcessor():
    """Processor for XLSX documents"""

    def extract_text( self, file_path: str) -> List[Dict[str, Any]]:
        
        unzip(Path(file_path), Path(EXTRACT_DIR))
        

        document = etree.parse(Path(EXTRACT_DIR) / "word" / "document.xml")
        root = document.getroot()
        
        paragraphs = []
        tables = []

        body = root.find("w:body", NS)

        for child in body:
            tag = child.tag

            # Normal paragraph 
            if tag == f"{{{NS['w']}}}p":
                texts = []
                for r in child.findall("w:r", NS):
                    t = r.find("w:t", NS)
                    if t is not None and t.text:
                        texts.append(t.text)
                if texts:
                    paragraphs.append(texts)

            # Table
            elif tag == f"{{{NS['w']}}}tbl":
                table = []
                for tr in child.findall("w:tr", NS):
                    for tc in tr.findall("w:tc", NS):
                        cell_texts = []
                        for p in tc.findall("w:p", NS):
                            paras = []
                            for r in p.findall("w:r", NS):
                                t = r.find("w:t", NS)
                                if t is not None and t.text:
                                    paras.append(t.text)
                            if paras:
                                cell_texts.append(paras)    
                        table.append(cell_texts) 
                tables.append(table)

        return {
            "paragraphs": paragraphs,
            "tables": tables
        }
    


    def clean_text(self, text: str) -> str:
        text = text.replace("\u3000", "")
        return re.sub(r"[\x00-\x1F\x7F]", "", text)

    def is_translatable_text(self, text: str) -> bool:
        text = text.strip()
        if not text:
            return False

        # Reject pure numbers (int / float / scientific)
        try:
            float(text)
            return False
        except ValueError:
            pass

        # Reject single symbol
        if len(text) == 1 and not text.isalnum():
            return False

        # Reject symbol-only strings
        if re.fullmatch(r"[\W_]+", text):
            return False

        # Accept if contains any letter (Unicode-safe)
        return any(ch.isalpha() for ch in text)
    
    def get_translatable_texts(self, extracted_data: Dict[str, Any]) -> List[str]:  
        translatable_texts = {}
        for p_idx,paragraph in enumerate(extracted_data.get("paragraphs", []),start=1):
            for r_idx,run in enumerate(paragraph,start=1):
                clean_text = self.clean_text(run)
                if self.is_translatable_text(clean_text):
                    key = f"paragraph {p_idx} run {r_idx}"
                    translatable_texts[key] = clean_text

        for t_idx, table in enumerate(extracted_data.get("tables", []),start=1):
                for c_idx, cell in enumerate(table,start=1):
                    for p_idx, para in enumerate(cell,start=1):
                        for r_idx, run in enumerate(para,start=1):
                            clean_text = self.clean_text(run)
                            if self.is_translatable_text(clean_text):
                                key = f"table {t_idx} cell {c_idx} paragraph {p_idx} run {r_idx}"
                                translatable_texts[key] = clean_text
        return translatable_texts
    
    def apply_translations(self, extracted_data: Dict[str, Any], translations: Dict[str, str]) -> Dict[str, Any]:  
        # Apply translations to paragraphs
        for p_idx,paragraph in enumerate(extracted_data.get("paragraphs", []),start=1):
            for r_idx,run in enumerate(paragraph,start=1):
                key = f"paragraph {p_idx} run {r_idx}"
                if key in translations:
                    extracted_data["paragraphs"][p_idx-1][r_idx-1] = translations[key]

        # Apply translations to tables
        for t_idx, table in enumerate(extracted_data.get("tables", []),start=1):
                for c_idx, cell in enumerate(table,start=1):
                    for p_idx, para in enumerate(cell,start=1):
                        for r_idx, run in enumerate(para,start=1):
                            key = f"table {t_idx} cell {c_idx} paragraph {p_idx} run {r_idx}"
                            if key in translations:
                                extracted_data["tables"][t_idx-1][c_idx-1][p_idx-1][r_idx-1] = translations[key]
        return extracted_data
    
    def reconstruct_document(self, original_path: str, translated_content: Dict[str, Any], output_path: str, target_lang: str) -> None:
        """
        Rebuild the DOCX document with modified content.
        """
        
        extract_dir = Path(EXTRACT_DIR)
        unzip(Path(original_path), extract_dir)
        document_path = extract_dir / "word" / "document.xml"
        document = etree.parse(document_path)
        root = document.getroot()
        body = root.find("w:body", NS)

        paragraphs = translated_content.get("paragraphs", [])
        tables = translated_content.get("tables", [])
        p_counter = 0
        t_counter = 0
        
        for child in body:
            tag = child.tag

            # Normal paragraph 
            if tag == f"{{{NS['w']}}}p":
                # Extract texts from this paragraph like we do in extract_text
                texts = []
                for r in child.findall("w:r", NS):
                    t = r.find("w:t", NS)
                    if t is not None and t.text:
                        texts.append(t.text)
                
                # Only update if this paragraph had text content (matching extraction logic)
                if texts and p_counter < len(paragraphs):
                    # Now replace the texts in this paragraph
                    r_counter = 0
                    for r in child.findall("w:r", NS):
                        t = r.find("w:t", NS)
                        if t is not None and t.text:
                            # Replace with translated text
                            if r_counter < len(paragraphs[p_counter]):
                                t.text = paragraphs[p_counter][r_counter]
                            r_counter += 1
                    p_counter += 1

            # Table
            elif tag == f"{{{NS['w']}}}tbl":
                cell_counter = 0
                for tr in child.findall("w:tr", NS):
                    for tc in tr.findall("w:tc", NS): 
                        cell_texts = []
                        para_list = tc.findall("w:p", NS)
                        
                        # Extract cell content structure like we do in extract_text
                        for p in para_list:
                            paras = []
                            for r in p.findall("w:r", NS):
                                t = r.find("w:t", NS)
                                if t is not None and t.text:
                                    paras.append(t.text)
                            if paras:
                                cell_texts.append(paras)
                        
                        # Only update if this cell had text content (matching extraction logic)
                        if cell_texts and t_counter < len(tables) and cell_counter < len(tables[t_counter]):
                            # Now replace the texts in this cell
                            para_counter = 0
                            for p in para_list:
                                r_counter = 0
                                for r in p.findall("w:r", NS):
                                    t = r.find("w:t", NS)
                                    if t is not None and t.text:
                                        # Check bounds before accessing
                                        if (para_counter < len(tables[t_counter][cell_counter]) and
                                            r_counter < len(tables[t_counter][cell_counter][para_counter])):
                                            t.text = tables[t_counter][cell_counter][para_counter][r_counter]
                                        r_counter += 1
                                # Only increment if this paragraph had text
                                paras = []
                                for r in p.findall("w:r", NS):
                                    t = r.find("w:t", NS)
                                    if t is not None and t.text:
                                        paras.append(t.text)
                                if paras:
                                    para_counter += 1
                        
                        cell_counter += 1
                t_counter += 1
        
        document.write(document_path, xml_declaration=True, encoding="UTF-8", standalone="yes")
     
        recompile(extract_dir, Path(output_path))
        shutil.rmtree(extract_dir)
        return output_path