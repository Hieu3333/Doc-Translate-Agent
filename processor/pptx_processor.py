import copy
import re
import shutil
from .base import BaseDocumentProcessor
import zipfile
from lxml import etree
from pathlib import Path
from typing import Any, Dict, List

EXTRACT_DIR = "tmp"
def unzip(path: Path, extract_dir: Path) -> None:
    """
    Unzip an XLSX file into extract_dir.
    """
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(path, "r") as z:
        z.extractall(extract_dir)    

def recompile(extracted_dir: Path, output_file: Path):

    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as z:
        for file_path in extracted_dir.rglob("*"):
            if file_path.is_file():
                # IMPORTANT: keep relative path
                arcname = file_path.relative_to(extracted_dir)
                z.write(file_path, arcname) 

NS = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}

class PPTXProcessor(BaseDocumentProcessor):


    def extract_text( self, file_path: str) -> Dict[str, Any]:

        slides = []
        unzip(Path(file_path), Path(EXTRACT_DIR))
        slides_dir = Path(EXTRACT_DIR) / "ppt" / "slides"

        if not slides_dir.exists():
            return slides
        
        for slide_file in sorted(slides_dir.glob("slide*.xml")):
            tree = etree.parse(str(slide_file))
            root = tree.getroot()

            slide_content = {"slide_name": slide_file.name, "texts": []}

            for paragraph in root.findall('.//a:p', NS):
                para_texts = []
                for run in paragraph.findall('a:r', NS):
                    text_elem = run.find('a:t', NS)
                    if text_elem is not None and text_elem.text is not None:
                        para_texts.append(text_elem.text)
                if para_texts:
                    slide_content["texts"].append(para_texts)
            slides.append(slide_content)

        # Extract comments
        comments = []
        comment_dir = Path(EXTRACT_DIR) / "ppt" / "comments"
        if comment_dir.exists():
            for comment_file in sorted(comment_dir.glob("comment*.xml")):
                comment_content = {
                    "comment_file": comment_file.name,
                    "texts": []
                }
                comment_tree = etree.parse(str(comment_file))
                comment_root = comment_tree.getroot()
                for comment in comment_root.findall('.//p:cm', NS):
                    text_elem = comment.find('p:text', NS)
                    if text_elem is not None and text_elem.text is not None:
                        comment_content["texts"].append(text_elem.text)
                comments.append(comment_content)

        #Extract slide notes
        notes = []
        notes_dir = Path(EXTRACT_DIR) / "ppt" / "notesSlides"
        if notes_dir.exists():
            for notes_file in sorted(notes_dir.glob("notesSlide*.xml")):
                notes_content = {
                    "notes_file": notes_file.name,
                    "texts": []
                }
                notes_tree = etree.parse(str(notes_file))
                notes_root = notes_tree.getroot()
                for paragraph in notes_root.findall('.//a:p', NS):
                    para_texts = []
                    for run in paragraph.findall('a:r', NS):
                        text_elem = run.find('a:t', NS)
                        if text_elem is not None and text_elem.text is not None:
                            para_texts.append(text_elem.text)

                    #Note texts could be stored as 1 char in a <r> node if user type it by hand
                    #But if user paste the texts to notes, a <r> node will contain string
                    if para_texts:
                        if all(len(t) == 1 for t in para_texts): #Case of single character runs
                            para_texts = ''.join(para_texts) 
                            notes_content["texts"].append(para_texts)
                        else:
                            #Or join them all into 1 string
                            notes_content["texts"].append(' '.join(para_texts))
                notes.append(notes_content)
        return {
            "slides": slides,
            "comments": comments,
            "notes": notes
        }


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


    def clean_text(self, text: str) -> str:
        text = text.replace("\u3000", "")
        return re.sub(r"[\x00-\x1F\x7F]", "", text)

    

    def apply_translations(self, extracted_content, translations) -> Dict[str, Any]:
        translated_content = copy.deepcopy(extracted_content)
        for slide_idx, slide in enumerate(translated_content.get("slides", []), start=1):
            for para_index, para in enumerate(slide.get("texts", []),start=1):
                for run_idx, run in enumerate(para, start=1):
                    cleaned_text = self.clean_text(run)
                    if self.is_translatable_text(cleaned_text):
                        key = f"slide {slide_idx} para {para_index} run {run_idx}"
                        if key in translations:
                            slide["texts"][para_index - 1][run_idx - 1] = translations[key]
        
        if extracted_content.get("comments"):
            for comment_idx, comment in enumerate(translated_content["comments"],start=1):
                for idx, text in enumerate(comment.get("texts", []), start=1):
                    cleaned_text = self.clean_text(text)
                    if self.is_translatable_text(cleaned_text):
                        key = f"comment slide {comment_idx} text {idx}"
                        comment["texts"][idx - 1] = translations[key]

        if extracted_content.get("notes"):
            for note_idx, note in enumerate(translated_content["notes"],start=1):
                for idx, text in enumerate(note.get("texts", []), start=1):
                    cleaned_text = self.clean_text(text)
                    if self.is_translatable_text(cleaned_text):
                        key = f"note slide {note_idx} text {idx}"
                        note["texts"][idx - 1] = translations[key]

        return translated_content
    
    def reconstruct_document(self, original_path, translated_content, output_path, target_lang):
        unzip(Path(original_path), Path(EXTRACT_DIR))
        slides_dir = Path(EXTRACT_DIR) / "ppt" / "slides"

        slides = translated_content.get("slides", [])
        for slide in slides:
            file_name = slide.get("slide_name")
            slide_file = slides_dir / file_name
            flattened_texts = []   
            for para in slide.get("texts", []):
                para_texts = []
                for run in para:
                    para_texts.append(run)
                flattened_texts.extend(para_texts)

            if not slide_file.exists():
                continue
            tree = etree.parse(str(slide_file))
            root = tree.getroot()

            idx = 0
            for paragraph in root.findall('.//a:p', NS):
                for run in paragraph.findall('a:r', NS):
                    text_elem = run.find('a:t', NS)
                    if text_elem is not None and text_elem.text is not None:
                        if idx < len(flattened_texts):
                            text_elem.text = flattened_texts[idx]
                            idx += 1
        
            tree.write(
                str(slide_file),
                encoding="UTF-8",
                xml_declaration=True,
                standalone=True,
            )       

        if translated_content.get("comments"):
            comment_dir = Path(EXTRACT_DIR) / "ppt" / "comments"
            for comment in translated_content["comments"]:
                file_name = comment.get("comment_file")
                comment_file = comment_dir / file_name
                if not comment_file.exists():
                    continue
                tree = etree.parse(str(comment_file))
                root = tree.getroot()
                texts = comment.get("texts", [])
                idx = 0
                for comment_elem in root.findall('.//p:cm', NS):
                    text_elem = comment_elem.find('p:text', NS)
                    if text_elem is not None and text_elem.text is not None:
                        if idx < len(texts):
                            text_elem.text = texts[idx]
                            idx += 1
                tree.write(
                    str(comment_file),
                    encoding="UTF-8",
                    xml_declaration=True,
                    standalone=True,
                )
        
        if translated_content.get("notes"):
            notes_dir = Path(EXTRACT_DIR) / "ppt" / "notesSlides"
            for note in translated_content["notes"]:
                file_name = note.get("notes_file")
                notes_file = notes_dir / file_name
                if not notes_file.exists():
                    continue
                tree = etree.parse(str(notes_file))
                root = tree.getroot()
                texts = note.get("texts", [])

                idx = 0
                for paragraph in root.findall('.//a:p', NS):
                    run_elems = paragraph.findall('a:r', NS)
                    if not run_elems:
                        # Skip paragraphs with no runs
                        continue
                    
           
                    if idx < len(texts):
                        run_texts = texts[idx]
                        idx += 1
                        
                        first_run_elem = run_elems[0] 
                        first_text_elem = first_run_elem.find('a:t', NS)
                        if first_text_elem is not None:
                            first_text_elem.text = run_texts

                        #Remove all remaining run elements
                        for run_elem in run_elems[1:]:
                            paragraph.remove(run_elem)

                tree.write(
                    str(notes_file),
                    encoding="UTF-8",
                    xml_declaration=True,
                    standalone=True,
                )
        
        recompile(Path(EXTRACT_DIR), Path(output_path))
        try:
            shutil.rmtree(EXTRACT_DIR)
        except Exception as e:
            print("Failed to remove temporary directory with error ", str(e) )

        return output_path

    
    # def get_pairs_translation(self, translated_content):
    #     pairs = {}
    #     for slide_idx, slide in enumerate(translated_content.get("slides", []), start=1):
    #         for para_index, para in enumerate(slide.get("texts", []),start=1):
    #             for run_idx, run in enumerate(para, start=1):
    #                 cleaned_text = self.clean_text(run)
    #                 if self.is_translatable_text(cleaned_text):
    #                     pairs[cleaned_text] = cleaned_text    #Store translated text only, If needed to map back to original, find a way to do so
    #     return pairs
