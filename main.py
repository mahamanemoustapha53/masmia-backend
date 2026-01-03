import json
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth
from reportlab.pdfgen import canvas
import os
import uuid

app = FastAPI()

# Firebase Admin (Render compatible)
firebase_json = os.environ.get("FIREBASE_CREDENTIALS")

if not firebase_json:
    raise ValueError("FIREBASE_CREDENTIALS not set")

cred_dict = json.loads(firebase_json)
cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class Chat(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "Backend OK"}

@app.post("/auth")
def verify_token(token: str):
    decoded = auth.verify_id_token(token)
    return {"uid": decoded["uid"]}

@app.post("/chat")
def chat(data: Chat):
    msg = data.message.lower()
    if "bonjour" in msg:
        reply = "Bonjour, comment puis-je t’aider ?"
    elif "temps" in msg:
        reply = "Je suis une IA hors ligne intelligente."
    else:
        reply = f"Réponse IA : {data.message}"
    return {"response": reply}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"file": path}

@app.post("/export/pdf")
def export_pdf(text: str):
    filename = f"exports/{uuid.uuid4()}.pdf"
    os.makedirs("exports", exist_ok=True)
    c = canvas.Canvas(filename)
    c.drawString(50, 800, text)
    c.save()
    return {"file": filename}
