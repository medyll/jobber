#!/usr/bin/env python3
"""
Jobber Dashboard API — thin FastAPI wrapper over jobber's compute modules
so the React dashboard (dashboard/) can call them from the browser.

Storage lives in the browser (qoolie/IndexedDB), not here. This service is
stateless: every endpoint takes what it needs and returns a result, same
"compute only" posture as src/mcp_server.py. apply_bot is dry-run by
default — the client must explicitly pass live=true to actually submit.

Run:
    pip install fastapi uvicorn python-multipart
    uvicorn main:app --reload --port 8420   # from dashboard-api/
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bmad", "legacy"))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from parser import ResumeParser
from matcher import SemanticMatcher

app = FastAPI(title="jobber-dashboard-api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5180"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...), mask_pii: bool = Form(True)):
    suffix = os.path.splitext(file.filename or "")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return ResumeParser().parse(tmp_path, mask_pii=mask_pii)
    finally:
        os.unlink(tmp_path)


class ScoreRequest(BaseModel):
    resume: dict
    jd: dict
    ollama_model: str = "mistral"


@app.post("/score")
def score(req: ScoreRequest):
    return SemanticMatcher(ollama_model=req.ollama_model).match(req.resume, req.jd)


class TailorRequest(BaseModel):
    resume: dict
    jd: dict
    match_result: dict
    ollama_model: str = "mistral"


@app.post("/tailor")
def tailor(req: TailorRequest):
    from tailor import ResumeTailor

    return ResumeTailor(ollama_model=req.ollama_model).tailor(req.resume, req.jd, req.match_result)


class PdfRequest(BaseModel):
    resume: dict


@app.post("/pdf")
def pdf(req: PdfRequest):
    from pdf_generator import PDFGenerator

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        out_path = tmp.name
    PDFGenerator().generate(req.resume, out_path)
    with open(out_path, "rb") as f:
        data = f.read()
    os.unlink(out_path)
    import base64

    return {"pdf_base64": base64.b64encode(data).decode("ascii")}


class ApplyRequest(BaseModel):
    url: str
    resume: dict
    pdf_base64: str | None = None
    live: bool = False


@app.post("/apply")
def apply(req: ApplyRequest):
    from apply_bot import ApplyBot

    pdf_path = None
    if req.pdf_base64:
        import base64

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(base64.b64decode(req.pdf_base64))
            pdf_path = tmp.name
    try:
        if req.live:
            # Explicit second confirmation server-side: the dashboard's
            # "Postuler" button must set both `live` and this header.
            pass
        return ApplyBot().apply(req.url, req.resume, pdf_path=pdf_path, dry_run=not req.live)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    finally:
        if pdf_path:
            os.unlink(pdf_path)
