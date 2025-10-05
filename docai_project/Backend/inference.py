import os
import json
import uuid
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from donut_extractor import extract_donut_data
from verifier import compute_confidence_score
from merge_engine import merge_outputs
from strategy_router import extract_text_and_classify
from ocr_utils import clean_text
from database import save_analysis

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
print("✅ OpenAI Key in use.")


def call_openai(prompt: str, model: str = "gpt-4") -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a document extraction assistant."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3
        )
        return resp.choices[0].message.content
    except OpenAIError as e:
        print("❌ OpenAI API error:", e)
        return ""


def validate_extraction(original_text: str, extracted_text: str) -> bool:
    words = original_text.split()
    ext_words = str(extracted_text).split()
    digit_ratio = sum(c.isdigit() for c in original_text) / max(len(original_text), 1)
    symbol_noise = sum(original_text.count(ch) for ch in ['|','=', '(', ')', '{', '}', '[', ']'])
    return (
        len(ext_words) < 0.5 * len(words)
        or digit_ratio > 0.15
        or symbol_noise > 50
    )


def run_secondary_pass(original_text: str, previous_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ask the LLM to extract ONLY the missing/new data in JSON.
    """
    fallback_prompt = f"""
The following document may not have been fully extracted. Please carefully re-analyze it.
Your task is to identify any missing fields, rows, or values that were skipped and return them ONLY.
Maintain the same JSON schema.

-------------------
Original Text:
{original_text}

Previous Extraction:
{json.dumps(previous_result, indent=2)}
"""
    # Debug secondary prompt
    print("[DEBUG] Secondary extraction prompt (first 500 chars):")
    print(fallback_prompt[:500])

    corrected = call_openai(fallback_prompt)
    # Debug secondary output
    print(f"[DEBUG] secondary_output_str (first 500 chars): {corrected[:500]!r}")
    try:
        return json.loads(corrected)
    except Exception:
        print("[DEBUG] Failed JSON parse of secondary_output_str")
        return {"error": "Fallback extraction parse failed", "raw_output": corrected}


def analyze_document(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    End-to-end: OCR → classify → clean → primary LLM extract →
    [validate→Donut→secondary LLM] → merge → score → save.
    """
    job_id = str(uuid.uuid4())
    fallback_triggered = False
    donut_used = False

    try:
        # 1) OCR + Classification
        raw_text, ocr_source, doc_type = extract_text_and_classify(filename, file_bytes)
        print(f"[DEBUG] OCR raw_text (first 200 chars): {raw_text[:200]!r}")
        print(f"[DEBUG] classify_document → {doc_type!r}")

        # 2) Clean text
        cleaned = clean_text(raw_text)
        print(f"[DEBUG] cleaned_text (first 200 chars): {cleaned[:200]!r}")

        # 3) Primary LLM Extraction
        primary_prompt = f"""
You are an intelligent document extraction assistant.

Your job is to perform **complete, exhaustive extraction** of all information present — every field, table, number, and record.

INSTRUCTIONS:
1. Return **every** field exactly as shown; do NOT summarize or infer missing data.
2. Preserve exact field names and values.
3. For repeating entries (tables), return a JSON list of objects.
4. Organize output into sections:
   - PII: names, addresses, IDs, emails, phones  
   - Important: core content (invoices, claims, summaries)  
   - Misc: disclaimers, footers, etc.
5. Provide a "Relationships" section linking entities to their data.

-------------------
Document Text:
{cleaned}
"""
        print("[DEBUG] Primary extraction prompt (first 500 chars):")
        print(primary_prompt[:500])

        primary_output_str = call_openai(primary_prompt)
        print(f"[DEBUG] primary_output_str (first 500 chars): {primary_output_str[:500]!r}")

        # Parse primary JSON
        primary_json: Dict[str, Any] = {}
        try:
            if primary_output_str:
                primary_json = json.loads(primary_output_str)
        except Exception:
            print("[DEBUG] Failed JSON parse of primary_output_str")

        # 4) Validate & Fallback
        if validate_extraction(cleaned, primary_output_str):
            print("[DEBUG] validate_extraction → True; triggering Donut + secondary pass")
            fallback_triggered = True
            donut_raw = extract_donut_data(file_bytes)
            donut_used = True
            secondary_json = run_secondary_pass(cleaned, donut_raw)
            merged_json = merge_outputs(primary_json, secondary_json)
        else:
            print("[DEBUG] validate_extraction → False; using primary only")
            merged_json = primary_json

        # 5) Confidence Scoring
        confidence = compute_confidence_score(merged_json, cleaned)

        # 6) Persist & Return
        record = {
            "job_id": job_id,
            "filename": filename,
            "document_type": doc_type,
            "ocr_source": ocr_source,
            "fallback_triggered": fallback_triggered,
            "donut_used": donut_used,
            "verification_score": confidence,
            "final_structured_data": merged_json
        }
        save_analysis(cleaned, record)
        return record

    except Exception as e:
        print(f"[DEBUG] analyze_document exception: {e}")
        return {"job_id": job_id, "error": str(e)}