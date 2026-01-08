import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from typing import List
from dotenv import load_dotenv

# OpenAI
import openai

load_dotenv()  # si tu veux tester en local

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY not set")

openai.api_key = OPENAI_KEY

# ================= APP =================
app = FastAPI(title="MASMM-IA Backend OpenAI")

UPLOAD_DIR = "uploads"
EXPORT_DIR = "exports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

# ================= MEMORY =================
conversation_memory = {}

# ================= MODELS =================
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    response: str

# ================= ROUTES =================
@app.get("/")
def root():
    return {"status": "Backend MASMM-IA + OpenAI OK"}

@app.post("/chat", response_model=ChatResponse)
async def chat(data: ChatRequest):
    session = data.session_id or "default"
    history: List[dict] = conversation_memory.setdefault(session, [])

    # Ajouter le message utilisateur à l'historique
    history.append({"role": "user", "content": data.message})

    try:
        # Appel OpenAI Chat
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=history,
            temperature=0.7,
            max_tokens=500
        )
        reply = completion.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Erreur OpenAI : {e}"

    # Ajouter la réponse à l'historique et limiter mémoire à 20 messages
    history.append({"role": "assistant", "content": reply})
    conversation_memory[session] = history[-20:]

    return {"response": reply}

# ================= FILE UPLOAD =================
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"file": path}

# ================= EXPORT PDF =================
@app.post("/export/pdf")
def export_pdf(text: str):
    filename = f"{EXPORT_DIR}/{uuid.uuid4()}.pdf"
    c = canvas.Canvas(filename)
    c.drawString(40, 800, text)
    c.save()
    return {"file": filename}
