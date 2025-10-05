import os
import uuid
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from pymongo import MongoClient
from dotenv import load_dotenv

from ocr_utils import extract_text_from_file
from inference import analyze_document
from verifier import verify_extraction_alignment

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
_db = client["docai"]
ocrs = _db["ocr_results"]
feedback_collection = _db["extraction_feedback"]

# Static files & templates for dashboard (if needed)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Upload Endpoint ---
@app.post("/upload/")
async def upload_doc(file: UploadFile = File(...)):
    try:
        # Read uploaded file bytes
        file_bytes = await file.read()

        # 1) OCR step
        ocr_info = extract_text_from_file(file.filename, file_bytes)
        raw_text = ocr_info.get("final_output", "")

        # 2) Full extraction pipeline
        result = analyze_document(file.filename, file_bytes)

        # 3) Verification
        structured = result.get("final_structured_data", {})
        verdict = verify_extraction_alignment(raw_text, structured)

        # 4) Persist results
        job_id = str(uuid.uuid4())
        record = {
            "job_id": job_id,
            "filename": file.filename,
            "document_type": result.get("document_type"),
            "final_structured_data": structured,
            "fallback_triggered": result.get("fallback_triggered", False),
            "donut_used": result.get("donut_used", False),
            "verification_score": verdict["score"],
            "verification_status": verdict["status"],
            "unmatched_fields": verdict["unmatched_fields"],
            "timestamp": datetime.utcnow()
        }
        ocrs.insert_one(record)

        # 5) Return summary JSON
        return {
            "job_id": job_id,
            "document_type": record["document_type"],
            "verification_score": record["verification_score"],
            "fallback_triggered": record["fallback_triggered"],
            "donut_used": record["donut_used"],
            "final_structured_data": record["final_structured_data"]
        }
    except Exception as e:
        print("❌ REAL ERROR in upload_doc:", repr(e))
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

# --- Feedback Endpoint ---
class FieldFeedback(BaseModel):
    job_id: str
    path: str                # JSON-pointer to the field
    action: str              # "approve" | "reject" | "edit"
    new_value: str | None = None
    username: str | None = None

@app.post("/feedback/")
async def submit_feedback(fb: FieldFeedback):
    rec = fb.dict()
    rec["timestamp"] = datetime.utcnow()
    feedback_collection.insert_one(rec)
    return {"status": "saved"}

# --- Dashboard Endpoint ---
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    records = list(ocrs.find({"final_structured_data": {"$exists": True}})
                     .sort("timestamp", -1))
    valid = [r for r in records if isinstance(r.get("final_structured_data"), dict)]
    return templates.TemplateResponse("dashboard.html", {"request": request, "records": valid})
