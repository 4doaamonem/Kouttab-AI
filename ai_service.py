"""
ai_service.py
FastAPI service exposing the functions in model.py over HTTP
for the Node.js backend.

Run (from the folder that contains this file and model.py):
    pip install fastapi uvicorn transformers torch python-multipart
    uvicorn ai_service:app --host 0.0.0.0 --port 8000
"""


import os
import shutil
import tempfile
from pathlib import Path
from typing import List
 
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
 
from model import classify, classify_batch, transcribe  # models load once here

import json
from fastapi import Form
from quran_compare import compare_recitation


app = FastAPI(title="AI Service")

with open(Path(__file__).parent / "quran_text_simple_plain.json", encoding="utf-8") as f:
    REFERENCE = json.load(f)


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class BatchRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify")
def classify_endpoint(req: TextRequest):
    try:
        return classify(req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/classify-batch")
def classify_batch_endpoint(req: BatchRequest):
    try:
        return {"results": classify_batch(req.texts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe")
def transcribe_endpoint(file: UploadFile = File(...)):
    """Upload an audio file (wav/mp3/m4a...) -> {"text": "..."}"""
    suffix = Path(file.filename or "").suffix or ".wav"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        return {"text": transcribe(tmp_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)



@app.post("/quran/check")
def quran_check_endpoint(
    file: UploadFile = File(...),
    ayah: str = Form(...),               # e.g. "1:1"
    lenient_tashkeel: bool = Form(True),
):
    """Audio + ayah key -> transcription + mistakes (word / letter / tashkeel)"""
    if ayah not in REFERENCE:
        raise HTTPException(status_code=404, detail=f"Unknown ayah key: {ayah}")

    suffix = Path(file.filename or "").suffix or ".wav"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        text = transcribe(tmp_path)
        result = compare_recitation(ayah, REFERENCE[ayah], text,
                                    lenient_tashkeel=lenient_tashkeel)
        result["transcription"] = text
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)




#run : & "$env:LOCALAPPDATA\KouttabProject\venv\Scripts\python.exe" -m uvicorn ai_service:app --host 127.0.0.1 --port 8000