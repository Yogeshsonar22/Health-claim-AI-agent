from __future__ import annotations

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name(".env"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import get_default_model_id, get_model_options
from data import seed_claims_file
from rag import ingest_document, delete_document, get_chunk_count, extract_text

app = FastAPI(title="InsureAssist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FILES_STORE: dict[str, dict] = {}

@app.on_event("startup")
def startup():
    seed_claims_file()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models")
def get_models():
    return {
        "models": get_model_options(),
        "default_model_id": get_default_model_id(),
    }


@app.get("/files")
def list_files():
    return list(FILES_STORE.values())


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    file_id = uuid.uuid4().hex

    text = extract_text(file.filename or "", content)
    has_text = bool(text.strip())

    chunk_count = 0
    if has_text:
        chunk_count = ingest_document(file_id, file.filename or "upload", content)

    record = {
        "file_id": file_id,
        "filename": file.filename or "upload",
        "size": len(content),
        "has_text": has_text,
        "chunk_count": chunk_count,
    }
    FILES_STORE[file_id] = record
    return record


@app.delete("/files/{file_id}")
def delete_file(file_id: str):
    if file_id not in FILES_STORE:
        raise HTTPException(status_code=404, detail="File not found")
    delete_document(file_id)
    del FILES_STORE[file_id]
    return {"deleted": file_id}


class AskRequest(BaseModel):
    question: str
    thread_id: str | None = None
    file_ids: list[str] = []
    history: list[dict] = []
    model_id: str | None = None
    search_all_files: bool = True


@app.post("/ask")
def ask(req: AskRequest):
    from agent import run_agent

    file_ids = None
    if not req.search_all_files and req.file_ids:
        file_ids = req.file_ids
    elif req.search_all_files:
        file_ids = None

    try:
        answer, sources = run_agent(
            question=req.question,
            history=req.history,
            file_ids=file_ids,
            model_id=req.model_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
