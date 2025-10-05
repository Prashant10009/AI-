from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["docai"]
print("✅ Connected to MongoDB!")
print("Collections:", db.list_collection_names())
