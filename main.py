import os
import uuid
import asyncio
import base64
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List
from openai import OpenAI
import fitz  # PyMuPDF

# ================= OPENAI CLIENT =================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ================= APP =================
app = FastAPI(title="MASMM-IA Backend")

# ================= MEMORY =================
conversation_memory: Dict[str, List[dict]] = {}

# ================= MODELS =================
class ChatRequest(BaseModel):
    session_id: str
    message: str

# ================= ROOT =================
@app.get("/")
def root():
    return {"status": "MASMM-IA backend OK"}

# ================= CHAT (NON STREAM) =================
@app.post("/chat")
async def chat(req: ChatRequest):
    session = conversation_memory.setdefault(req.session_id, [])
    session.append({"role": "user", "content": req.message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es une IA comme ChatGPT."},
            *session
        ]
    )

    answer = response.choices[0].message.content
    session.append({"role": "assistant", "content": answer})

    return {"response": answer}

# ================= CHAT STREAM =================
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):

    session = conversation_memory.setdefault(req.session_id, [])
    session.append({"role": "user", "content": req.message})

    async def generator():
        collected = ""

        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es une IA comme ChatGPT."},
                *session
            ],
            stream=True
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                collected += delta.content
                yield delta.content
                await asyncio.sleep(0.01)

        session.append({"role": "assistant", "content": collected})

    return StreamingResponse(generator(), media_type="text/plain")

# ================= PDF / TXT =================
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()

    if file.filename.endswith(".txt"):
        text = content.decode("utf-8")

    elif file.filename.endswith(".pdf"):
        doc = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)

    else:
        return {"analysis": "Format non supporté"}

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Analyse et résume ce document."},
            {"role": "user", "content": text[:12000]}
        ]
    )

    return {"analysis": response.choices[0].message.content}

# ================= VISION =================
@app.post("/vision")
async def vision(image: UploadFile = File(...)):
    img_bytes = await image.read()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Décris cette image en détail."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64.b64encode(img_bytes).decode()}"
                        }
                    }
                ]
            }
        ]
    )

    return {"response": response.choices[0].message.content}
