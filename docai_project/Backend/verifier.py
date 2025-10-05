import difflib
import json
import re

def normalize_field(value: str) -> str:
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'[^a-zA-Z0-9]', '', value.lower().strip())

def verify_extraction_alignment(original_text: str, structured_json: dict, threshold: float = 0.75) -> dict:
    """
    Compares the original OCR text to the structured extracted JSON.
    Flags missing fields or values that aren't matched back in the text.
    Returns a score and list of unmatched fields.
    """
    if not isinstance(structured_json, dict):
        return {"score": 0.0, "status": "Invalid structured output", "unmatched_fields": []}

    structured_str = json.dumps(structured_json, indent=2)
    original_cleaned = normalize_field(original_text)
    structured_cleaned = normalize_field(structured_str)

    ratio = difflib.SequenceMatcher(None, original_cleaned, structured_cleaned).ratio()

    try:
        raw_fields = json.loads(structured_str)
    except:
        return {"score": ratio, "status": "Unparsable structured JSON", "unmatched_fields": []}

    def extract_leaf_values(d):
        result = []
        if isinstance(d, dict):
            for k, v in d.items():
                result.extend(extract_leaf_values(v))
        elif isinstance(d, list):
            for item in d:
                result.extend(extract_leaf_values(item))
        else:
            result.append(str(d))
        return result

    all_values = extract_leaf_values(raw_fields)
    unmatched = [v for v in all_values if normalize_field(v) not in original_cleaned]

    return {
        "score": round(ratio, 3),
        "status": "Verified with warnings" if ratio < threshold else "Verified",
        "unmatched_fields": unmatched[:20]
    }
def compute_confidence_score(extracted: dict, ocr_text: str) -> float:
    import re

    if not extracted or not ocr_text:
        return 0.0

    try:
        # Flatten all values from the extracted dict into a single string
        def flatten(d):
            result = []
            if isinstance(d, dict):
                for v in d.values():
                    result.extend(flatten(v))
            elif isinstance(d, list):
                for i in d:
                    result.extend(flatten(i))
            else:
                result.append(str(d))
            return result

        extracted_strings = flatten(extracted)
        total = len(extracted_strings)
        matches = 0

        for value in extracted_strings:
            value = re.sub(r"\s+", " ", value.strip())
            if value and value.lower() in ocr_text.lower():
                matches += 1

        return round(matches / total, 3) if total else 0.0
    except Exception as e:
        print(f"[!] Confidence Scoring Error: {e}")
        return 0.0
