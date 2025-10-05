from openai import OpenAI
import os

# Load OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def classify_document(text: str) -> str:
    """
    Uses LLM to classify the document type from the extracted text.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Replace with your fine-tuned model ID if available
            messages=[
                {
                    "role": "system",
                    "content": "You are a document classifier. Identify the type of document. \
                                Return one label only, such as 'resume', 'invoice', 'claim report', 'fuel tax return', etc."
                },
                {
                    "role": "user",
                    "content": f"{text[:3000]}"  # Truncate to stay within token limit
                }
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("❌ CLASSIFICATION ERROR:", e)
        return "Unknown"
