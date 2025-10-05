import json, os, uuid
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()

mongo = MongoClient(os.getenv("MONGODB_URI"))
db = mongo["docai"]
jobs       = db["ocr_results"]
feedback   = db["extraction_feedback"]

def set_nested(data, path, new_val):
    keys = path.strip("/").split("/")
    ref = data
    for k in keys[:-1]:
        try:
            k = int(k) if k.isdigit() else k
            ref = ref[k]
        except Exception:
            return False
    final_key = keys[-1]
    try:
        final_key = int(final_key) if final_key.isdigit() else final_key
        ref[final_key] = new_val
        return True
    except Exception:
        return False

export = []
for fb in feedback.find({"action": {"$in": ["edit", "approve"]}}):
    job = jobs.find_one({"job_id": fb["job_id"]})
    if not job: continue

    original = job["final_structured_data"]
    corrected = json.loads(json.dumps(original))  # deep copy

    if fb["action"] == "edit" and fb.get("new_value"):
        success = set_nested(corrected, fb["path"], fb["new_value"])
        if not success:
            print(f"❌ Failed to patch path: {fb['path']}")

    export.append({
        "messages": [
            {"role": "system", "content": "You are an intelligent document extractor."},
            {"role": "user", "content": json.dumps(original)},
            {"role": "assistant", "content": json.dumps(corrected)}
        ]
    })

outfile = f"verified_feedback_{uuid.uuid4().hex[:8]}.jsonl"
with open(outfile, "w", encoding="utf8") as f:
    for row in export:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"✅ Wrote {len(export)} samples to {outfile}")
