import fitz  # PyMuPDF
import re
from PIL import Image
import io
from document_classifier import classify_document
from ocr_utils import extract_text_from_file


def extract_text_and_classify(filename: str, file_bytes: bytes) -> tuple[str, str, str]:
    """
    Step 1: Extract raw text from document using OCR and fallback models
    Step 2: Classify document type using LLM
    Returns: raw_text (str), ocr_source (str), document_type (str)
    """
    # 1) OCR extraction
    ocr_info = extract_text_from_file(filename, file_bytes)
    raw_text = ocr_info.get("final_output", "")
    ocr_source = ocr_info.get("used_model", "")

    # 2) Document classification
    document_type = classify_document(raw_text)
    print(f"[DEBUG] classify_document → {document_type!r}")

    return raw_text, ocr_source, document_type


def route_extraction_strategy(pdf_bytes: bytes) -> dict:
    """
    Analyze layout and content of first page to choose OCR engine and layout
    Returns a dict with keys: ocr_engine, layout, require_llm, symbol_density
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)

    # estimate symbol density to choose layout strategy
    text = page.get_text()
    symbol_density = len(re.findall(r"\W", text)) / max(len(text), 1)
    layout = "tabular" if symbol_density > 0.05 else "unstructured"

    # convert page to image for handwriting/fallback detection
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes()))
    # Placeholder for handwriting detection
    has_handwriting = False
    ocr_engine = "trocr" if has_handwriting else "tesseract"

    return {
        "ocr_engine": ocr_engine,
        "layout": layout,
        "require_llm": layout == "unstructured",
        "symbol_density": symbol_density
    }