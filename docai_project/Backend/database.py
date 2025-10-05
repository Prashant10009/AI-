import os
from dotenv import load_dotenv
from pymongo import MongoClient

# ✅ Load environment variables from .env
load_dotenv()

# ✅ Get the Mongo URI from the .env file (do NOT hardcode it)
MONGO_URI = os.getenv("MONGODB_URI")

# ✅ Connect to MongoDB using the URI from .env
client = MongoClient(MONGO_URI)
db = client["docai"]
collection = db["results"]

def save_analysis(text, result):
    collection.insert_one({"input": text, "output": result})
print("✅ Mongo URI in use:", repr(MONGO_URI))  # Add this line temporarily
