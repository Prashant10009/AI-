from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("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"))

try:
    response = client.models.list()
    print("✅ Your API key works! Available models:")
    for model in response.data:
        print("-", model.id)
except Exception as e:
    print("❌ Error:", e)
