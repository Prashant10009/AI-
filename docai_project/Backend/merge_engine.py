import copy

def deep_merge(primary: dict, secondary: dict) -> dict:
    """Merge two dictionaries deeply without overwriting non-empty primary fields."""
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        return primary or secondary

    result = copy.deepcopy(primary)

    for key, value in secondary.items():
        if key not in result:
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif isinstance(result[key], list) and isinstance(value, list):
            result[key] = merge_lists(result[key], value)
        elif not result[key] and value:
            result[key] = value

    return result

def merge_lists(primary_list, secondary_list):
    """Merge lists of dicts by comparing values and avoiding duplicates."""
    merged = list(primary_list)
    for sec in secondary_list:
        if isinstance(sec, dict):
            if not any(dicts_equal(sec, pri) for pri in merged):
                merged.append(sec)
        elif sec not in merged:
            merged.append(sec)
    return merged

def dicts_equal(d1, d2):
    if not isinstance(d1, dict) or not isinstance(d2, dict):
        return d1 == d2
    return sorted(d1.items()) == sorted(d2.items())

def merge_extractions(primary_data: dict, fallback_data: dict, ocr_text: str = "") -> dict:
    """
    Combines primary GPT extraction and fallback results (OCR/text-based recovery).
    Optional: store which fields were enriched.
    """
    merged = deep_merge(primary_data, fallback_data)
    return merged
def merge_outputs(primary_output: dict, fallback_output: dict) -> dict:
    """
    Combines two outputs (primary and fallback) into a unified final structure.
    Primary output is preferred; fallback fills gaps.
    """
    def deep_merge(a, b):
        for key, val in b.items():
            if key not in a:
                a[key] = val
            elif isinstance(a[key], dict) and isinstance(val, dict):
                deep_merge(a[key], val)
            elif isinstance(a[key], list) and isinstance(val, list):
                existing_items = {str(i) for i in a[key]}
                a[key].extend([item for item in val if str(item) not in existing_items])
        return a

    if not primary_output:
        return fallback_output or {}

    if not fallback_output:
        return primary_output or {}

    merged = deep_merge(primary_output.copy(), fallback_output)
    return merged
