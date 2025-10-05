import torch
from transformers import DonutProcessor, VisionEncoderDecoderModel
from pdf2image import convert_from_bytes
from PIL import Image
import json

# Load pretrained Donut model and processor
processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
model.eval()

def extract_donut_data(pdf_bytes: bytes) -> dict:
    try:
        pages = convert_from_bytes(pdf_bytes)
        all_outputs = []

        for i, page in enumerate(pages):
            # Prepare input
            pixel_values = processor(images=page, return_tensors="pt").pixel_values
            task_prompt = "<s_docvqa><s_question>extract this document<s_answer>"
            decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids

            # Inference
            with torch.no_grad():
                outputs = model.generate(
                    pixel_values,
                    decoder_input_ids=decoder_input_ids,
                    max_length=512,
                    num_beams=2,
                    early_stopping=True,
                    pad_token_id=processor.tokenizer.pad_token_id
                )

            result = processor.batch_decode(outputs, skip_special_tokens=True)[0]
            try:
                parsed = json.loads(result)
                all_outputs.append(parsed)
            except:
                all_outputs.append({"raw_output": result})

        return {"donut_output": all_outputs}

    except Exception as e:
        print("❌ Donut extraction failed:", e)
        return {"error": str(e)}
