from fastapi import FastAPI, UploadFile, File, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from inference import analyze_document
from ocr_utils import extract_text_from_file
from database import save_analysis
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
client = MongoClient(os.getenv("MONGODB_URI"))
ocr_collection = client["docai"]["ocr_results"]

@app.post("/upload/")
async def upload_doc(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        ocr_result = extract_text_from_file(file.filename, contents)
        result = analyze_document(ocr_result["final_output"])
        combined = {"filename": file.filename, **ocr_result, **result}
        ocr_collection.insert_one(combined)
        return {"result": result}
    except Exception as e:
        print("❌ ERROR:", str(e))
        return {"error": str(e)}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    records = list(ocr_collection.find({}, {"_id": 0}).sort("_id", -1))
    return templates.TemplateResponse("dashboard.html", {"request": request, "records": records})