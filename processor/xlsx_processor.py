"""
XLSX document processor
"""

import copy
import re
import shutil
from typing import Any, Dict, List, Tuple


from processor.base import BaseDocumentProcessor
import zipfile

from pathlib import Path
from lxml import etree
from typing import Dict, Any, List

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
SHEET_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
DRAWING_NS = {
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
EXTRACT_DIR = "tmp"

CELL_RE = re.compile(r"^([A-Z]+)([0-9]+)$")

def parse_cell_ref(cell_ref: str) -> Tuple[int, str]:
    """
    Parse Excel cell reference like 'AH39' into ('AH', 39)
    """
    m = CELL_RE.match(cell_ref)
    if not m:
        raise ValueError(f"Invalid cell reference: {cell_ref}")

    col_letters, row = m.groups()
    return int(row), col_letters

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

def build_shared_strings(shared_strings_path: Path) -> List[List[str]]:
        

        if not shared_strings_path.exists():
            return []

        tree = etree.parse(shared_strings_path)
        root = tree.getroot()

        shared_strings: List[List[str]] = []

        # Already exclude phonetic strings <si><rPh>

        for si in root.findall("a:si", SHEET_NS):
            texts: List[str] = []
            
            # Case 1: simple shared string <si><t>
            for t in si.findall("./a:t", SHEET_NS):
                if t.text:
                    texts.append(t.text)

            # Case 2: rich text runs <si><r><t>
            for t in si.findall("./a:r/a:t", SHEET_NS):
                if t.text:
                    texts.append(t.text)

            shared_strings.append(texts) #List of list of strings

        return shared_strings 

def extract_drawings(extract_dir: Path) -> list[Dict[str, Any]]:
    drawings = []

    drawings_dir = extract_dir / "xl" / "drawings"
    if not drawings_dir.exists():
        return drawings

    for drawing_file in sorted(drawings_dir.glob("drawing*.xml")):
        tree = etree.parse(drawing_file)
        root = tree.getroot()

        # twoCellAnchor + oneCellAnchor together
        for anchor in root.findall(".//xdr:twoCellAnchor", DRAWING_NS):
            for sp in anchor.findall(".//xdr:sp", DRAWING_NS):
                paragraphs: List[List[str]] = []

                for p in sp.findall(".//a:p", DRAWING_NS):
                    runs: List[str] = []

                    # IMPORTANT: iterate children to preserve order
                    for node in p:
                        local = etree.QName(node).localname

                        if local in ("r", "fld"):
                            t = node.find("a:t", DRAWING_NS)
                            if t is not None and t.text is not None:
                                runs.append(t.text)

                        elif local == "br":
                            runs.append("\n")

                    if runs:
                        paragraphs.append(runs)

                if paragraphs:
                    drawings.append({
                        "drawing_file": drawing_file.name,
                        "paragraphs": paragraphs,
                    })

        for anchor in root.findall(".//xdr:oneCellAnchor", DRAWING_NS):
            for sp in anchor.findall(".//xdr:sp", DRAWING_NS):
                paragraphs: List[List[str]] = []

                for p in sp.findall(".//a:p", DRAWING_NS):
                    runs: List[str] = []

                    # IMPORTANT: iterate children to preserve order
                    for node in p:
                        local = etree.QName(node).localname

                        if local in ("r", "fld"):
                            t = node.find("a:t", DRAWING_NS)
                            if t is not None and t.text is not None:
                                runs.append(t.text)

                        elif local == "br":
                            runs.append("\n")

                    if runs:
                        paragraphs.append(runs)

                if paragraphs:
                    drawings.append({
                        "drawing_file": drawing_file.name,
                        "paragraphs": paragraphs,
                    })

    return drawings

class XLSXProcessor(BaseDocumentProcessor):
    """Processor for XLSX documents"""

    def extract_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Extract the structure of an XLSX file.
        
        Returns a dict with:
        - "content": list of sheets with their name and id
        - "total_sheets": total number of sheets
        """
        try:
            unzip(Path(file_path), Path(EXTRACT_DIR))
            
            # Extract sheet information
            workbook = etree.parse(Path(EXTRACT_DIR) / "xl" / "workbook.xml")
            root = workbook.getroot()
            
            sheets = []
            for sheet in root.findall(".//a:sheets/a:sheet", NS):
                sheets.append({
                    "name": sheet.get("name")
                })
            
            return {
                "content": sheets,
                "total_sheets": len(sheets),
            }
        finally:
            try:
                shutil.rmtree(EXTRACT_DIR)
            except Exception:
                pass

    def extract_text( self, file_path: str) -> Dict[str, Any]:
        # content = {"worksheets": []}
        
        try:
            unzip(Path(file_path), Path(EXTRACT_DIR))
            

            #Extract sheet information
            workbook = etree.parse(Path(EXTRACT_DIR) / "xl" / "workbook.xml")
            root = workbook.getroot()

            sheets = []
            for sheet in root.findall(".//a:sheets/a:sheet", NS):
                sheets.append({
                    "name": sheet.get("name"),
                    "sheetId": sheet.get("sheetId"),
                    "rId": sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"),
                })
            # print(sheets)

            # Map sheet rId to actual sheet file paths
            relationships = etree.parse(Path(EXTRACT_DIR) / "xl" / "_rels" / "workbook.xml.rels")
            root = relationships.getroot()
            for sheet in sheets:
                for rel in relationships.findall("r:Relationship", REL_NS):
                    if rel.get("Id") == sheet.get("rId") and rel.get("Type") == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet":
                        sheet["sheet_path"] = rel.get("Target")

            shared_strings = build_shared_strings(Path(EXTRACT_DIR) / "xl" / "sharedStrings.xml")
            # print("Shared Strings:", len(shared_strings))
            # print(shared_strings[166])

            #Map each row of each sheet to its shared string values
            for sheet in sheets:
                sheet_file_path = Path(EXTRACT_DIR) / "xl" / sheet["sheet_path"]
                worksheet = etree.parse(sheet_file_path)
                root = worksheet.getroot()

                data = []
                for row in root.findall(".//a:sheetData/a:row", NS):
                    for c in row.findall("a:c", NS):
                        cell_type = c.get("t")
                        v = c.find("a:v", NS)
                        if v is not None and v.text is not None and cell_type == "s":
                            sst_index = int(v.text)
                            cell_value = {
                                "cell": c.get("r"),
                                "text": shared_strings[sst_index], #text here is a list of strings (for handling rich text)
                                "sst_index": sst_index                               
                            }
                        else:
                            cell_value = ""
                        if cell_value:
                            data.append(cell_value)

                sheet["data"] = data
            

            return {
                "sheets": sheets,
                "drawings": extract_drawings(Path(EXTRACT_DIR)),
            }
        finally:
            try:
                shutil.rmtree(EXTRACT_DIR)
            except Exception:
                pass

    
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

   
    
    def get_translatable_texts(self, extracted_content: Dict[str, Any]) -> Dict[str, str]:
        texts: Dict[str, str] = {}

        for sheet_idx, sheet in enumerate(extracted_content.get('sheets', []), start=1):
            sheet_name_text = str(sheet.get('name', '')).strip()
            name_key = f"sheet {sheet_idx} name"
            if sheet_name_text and self.is_translatable_text(sheet_name_text):
                texts[name_key] = self.clean_text(sheet_name_text)

            for data in sheet.get('data', []):
                chunk_texts = data.get('text', [])
                for idx,chunk_text in enumerate(chunk_texts,start=1):
                    if not chunk_text or not self.is_translatable_text(chunk_text):
                        continue

                    try:
                        row, col = parse_cell_ref(data.get('cell', ''))
                    except Exception:
                        continue
                    key = f"sheet {sheet_idx} row {row} col {col} chunk {idx}"
                    texts[key] = self.clean_text(chunk_text)

        # Extract drawing run texts
        for drawing_idx, drawing in enumerate(extracted_content.get("drawings", []),start=1):
            drawing_file = drawing.get("drawing_file")
   
            for p_idx, para in enumerate(drawing.get("paragraphs", []),start=1):
                for r_idx, run_text in enumerate(para,start=1):
                    if run_text == "\n":
                        continue             
                    if not run_text or not self.is_translatable_text(run_text):
                        continue

                    key = f"drawing {drawing_idx} para {p_idx} run {r_idx}"
                    texts[key] = self.clean_text(run_text)
        return texts




    def apply_translations(
        self,
        extracted_content: Dict[str, Any],
        translations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply translations back to extracted content structure.

        translations example (1-based indices for chunks):
            {
                "sheet 1 name": "New Sheet Name",
                "sheet 1 row 1 col A chunk 1": "Hello",
                "drawing 1 para 1 run 1": "Translated text",
            }
        """
        translated_content = copy.deepcopy(extracted_content)

        # Apply sheet name translations
        for sheet_idx, sheet in enumerate(translated_content.get('sheets', []), start=1):
            name_key = f"sheet {sheet_idx} name"
            if name_key in translations:
                sheet['name'] = translations[name_key]

        # Apply cell data translations
        for sheet_idx, sheet in enumerate(translated_content.get('sheets', []), start=1):
            for data in sheet.get('data', []):
                try:
                    row, col = parse_cell_ref(data.get('cell', ''))
                except Exception:
                    continue

                # Ensure data['text'] is a list
                current_text = data.get('text', [])
                if isinstance(current_text, str):
                    current_text = [current_text]
                    data['text'] = current_text

                # Apply translations to each chunk (1-indexed to match get_translatable_texts)
                for idx, chunk_text in enumerate(current_text, start=1):
                    key = f"sheet {sheet_idx} row {row} col {col} chunk {idx}"
                    if key in translations:
                        data['text'][idx - 1] = translations[key]

        # Apply drawing translations
        for drawing_idx, drawing in enumerate(translated_content.get("drawings", []),start=1):
   
            for p_idx, para in enumerate(drawing.get("paragraphs", []),start=1):
                for r_idx, run_text in enumerate(para,start=1):
                    if run_text == "\n":
                        continue             
                    if not run_text or not self.is_translatable_text(run_text):
                        continue

                    key = f"drawing {drawing_idx} para {p_idx} run {r_idx}"
                    if key in translations:
                        drawing["paragraphs"][p_idx - 1][r_idx - 1] = translations[key]
                    
        return translated_content


    
    def reconstruct_document(
        self, original_path: str, translated_content: Dict[str, Any], output_path: str
    ) -> str:
        """Reconstruct XLSX by updating sharedStrings, sheet names, and drawings."""
        try:
            extract_dir = Path(EXTRACT_DIR)
            unzip(Path(original_path), extract_dir)

            shared_string_path = extract_dir / "xl" / "sharedStrings.xml"
            workbook_path = extract_dir / "xl" / "workbook.xml"

            # Build mapping from shared string index -> translated text
            index_to_translation: Dict[int, List[str]] = {}
            sheet_name_map: Dict[int, str] = {}

            for sheet_idx, sheet in enumerate(translated_content.get("sheets", []), start=1):
                sheet_name_map[sheet_idx] = sheet.get("name", "")
                for data in sheet.get("data", []):
                    sst_idx = data.get("sst_index")
                    if sst_idx is None:
                        continue
                    try:
                        idx = int(sst_idx)
                    except Exception:
                        continue

                    textual = data.get("text", [])
                    # Flatten to list of strings
                    flattened: List[str] = []
                    if isinstance(textual, str):
                        flattened = [textual]
                    else:
                        for chunk in textual:
                            if isinstance(chunk, (list, tuple)):
                                flattened.extend([str(x) for x in chunk])
                            else:
                                flattened.append(str(chunk))

                    index_to_translation[idx] = flattened

            # Update sharedStrings.xml
            if shared_string_path.exists():
                tree = etree.parse(str(shared_string_path))
                root = tree.getroot()
                si_nodes = root.findall("a:si", SHEET_NS)

                for idx, si in enumerate(si_nodes):
                    if idx not in index_to_translation:
                        continue

                    new_texts = index_to_translation[idx]
                    t_nodes = si.findall(".//a:t", SHEET_NS)

                    # Assign to existing <t> nodes in order
                    for i, t_node in enumerate(t_nodes):
                        if i < len(new_texts):
                            t_node.text = new_texts[i]
                        else:
                            t_node.text = ""

                tree.write(
                    str(shared_string_path),
                    encoding="UTF-8",
                    xml_declaration=True,
                    standalone=True,
                )

            # Update workbook sheet names
            if workbook_path.exists():
                workbook_tree = etree.parse(str(workbook_path))
                workbook_root = workbook_tree.getroot()
                workbook_sheets = workbook_root.findall(".//a:sheets/a:sheet", NS)

                for sheet_idx, sheet_elem in enumerate(workbook_sheets, start=1):
                    if sheet_idx in sheet_name_map and sheet_name_map[sheet_idx]:
                        sheet_elem.set("name", sheet_name_map[sheet_idx])

                workbook_tree.write(
                    str(workbook_path),
                    encoding="UTF-8",
                    xml_declaration=True,
                    standalone=True,
                )

            # Reconstruct drawings -> parsing the drawing files the same way as extract_drawings to map the texts back correctly
            drawings_dir = extract_dir / "xl" / "drawings"
            if drawings_dir.exists():
                # Group translations by drawing filename
                drawings_by_file: Dict[str, List[Dict[str, Any]]] = {}
                for d in translated_content.get("drawings", []):
                    fname = d.get("drawing_file")
                    if not fname:
                        continue
                    drawings_by_file.setdefault(fname, []).append(d)

                for drawing_file in sorted(drawings_dir.glob("drawing*.xml")):
                    fname = drawing_file.name
                    entries = drawings_by_file.get(fname, [])
                    if not entries:
                        continue

                    tree = etree.parse(str(drawing_file))
                    root = tree.getroot()

                    entry_idx = 0

              
                    for anchor in root.findall(".//xdr:twoCellAnchor", DRAWING_NS):
                        for sp in anchor.findall(".//xdr:sp", DRAWING_NS):
                            p_nodes = sp.findall(".//a:p", DRAWING_NS)
                            if not p_nodes:
                                continue

                            has_content = False
                            for p in p_nodes:
                                for node in p:
                                    local = etree.QName(node).localname
                                    if local in ("r", "fld"):
                                        t = node.find('{%s}t' % DRAWING_NS['a'])
                                        if t is not None and t.text is not None:
                                            has_content = True
                                            break
                                    elif local == "br":
                                        has_content = True
                                        break
                                if has_content:
                                    break

                            if not has_content:
                                continue

                            if entry_idx >= len(entries):
                                break

                            entry = entries[entry_idx]
                            para_trans_list = entry.get("paragraphs", [])

                            for p_idx, p_node in enumerate(p_nodes):
                                if p_idx >= len(para_trans_list):
                                    break

                                trans_para = para_trans_list[p_idx]
                                run_idx = 0

                           
                                for node in p_node:
                                    local = etree.QName(node).localname

                                    if local in ("r", "fld"):
                                        if run_idx < len(trans_para):
                                            t = node.find('{%s}t' % DRAWING_NS['a'])
                                            if t is not None:
                                                t.text = trans_para[run_idx]
                                        run_idx += 1
                                    elif local == "br":
                                        run_idx += 1

                            entry_idx += 1

                
                    for anchor in root.findall(".//xdr:oneCellAnchor", DRAWING_NS):
                        for sp in anchor.findall(".//xdr:sp", DRAWING_NS):
                            p_nodes = sp.findall(".//a:p", DRAWING_NS)
                            if not p_nodes:
                                continue

                          
                            has_content = False
                            for p in p_nodes:
                                for node in p:
                                    local = etree.QName(node).localname
                                    if local in ("r", "fld"):
                                        t = node.find('{%s}t' % DRAWING_NS['a'])
                                        if t is not None and t.text is not None:
                                            has_content = True
                                            break
                                    elif local == "br":
                                        has_content = True
                                        break
                                if has_content:
                                    break

                            if not has_content:
                                continue

                            if entry_idx >= len(entries):
                                break

                            entry = entries[entry_idx]
                            para_trans_list = entry.get("paragraphs", [])

                
                            for p_idx, p_node in enumerate(p_nodes):
                                if p_idx >= len(para_trans_list):
                                    break

                                trans_para = para_trans_list[p_idx]
                                run_idx = 0

                              
                                for node in p_node:
                                    local = etree.QName(node).localname

                                    if local in ("r", "fld"):
                                        if run_idx < len(trans_para):
                                            t = node.find('{%s}t' % DRAWING_NS['a'])
                                            if t is not None:
                                                t.text = trans_para[run_idx]
                                        run_idx += 1
                                    elif local == "br":
                                        run_idx += 1

                            entry_idx += 1

                    tree.write(str(drawing_file), encoding="UTF-8", xml_declaration=True, standalone=True)

            

            recompile(extract_dir, Path(output_path))
            return output_path
        finally:
            try:
                shutil.rmtree(EXTRACT_DIR)
            except Exception:
                pass
