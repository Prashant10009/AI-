import re
from PIL import Image
import pytesseract
import io
from pdf2image import convert_from_bytes
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Dict, Any

# Load environment variables and init MongoDB
load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")
client = MongoClient(mongo_uri)
db = client["docai"]

# Lazy model holders
processor = None
model = None


def clean_text(text: str) -> str:
    """
    Normalize whitespace and remove non-printable characters.
    """
    text = text.replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_file(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    # Delay import to avoid circular dependency
    from strategy_router import route_extraction_strategy

    strategy = route_extraction_strategy(file_bytes)
    selected_model = strategy["ocr_engine"]

    result: Dict[str, Any] = {
        "filename": filename,
        "strategy": strategy,
        "used_model": selected_model,
        "tesseract_output": "",
        "trocr_output": "",
        "trocr_confidence": 0.0,
        "final_output": ""
    }

    if filename.lower().endswith(".pdf"):
        images = convert_from_bytes(file_bytes)
        texts = []

        for img in images:
            if selected_model == "trocr":
                global processor, model
                if processor is None or model is None:
                    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
                    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
                pixel_values = processor(images=img, return_tensors="pt").pixel_values
                outputs = model.generate(pixel_values)
                text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
                result["trocr_output"] += text + "\n"
                texts.append(text)
            else:
                txt = pytesseract.image_to_string(img)
                result["tesseract_output"] += txt + "\n"
                texts.append(txt)

        combined = "\n".join(texts)
        result.update({"final_output": combined})
        return result

    else:
        # Plain text or image file fallback
        try:
            decoded = file_bytes.decode("utf-8", errors="ignore")
            result.update({"used_model": "text decode", "final_output": decoded})
        except:
            result.update({"used_model": "binary fallback", "final_output": ""})
        return result

# Alias for backward compatibility
extract_text_with_fallback = extract_text_from_file