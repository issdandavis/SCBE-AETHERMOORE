"""Governed local MLA routes sharing the browser's canonical document compiler."""

import base64
import json
from pathlib import Path
import shutil
import subprocess
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict

from scene_board_api import local_request, checked

HERE = Path(__file__).resolve().parent
router = APIRouter(dependencies=[Depends(local_request)])


class MLADocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=200000)
    firstName: str = ""
    lastName: str = ""
    instructor: str = ""
    course: str = ""
    date: str = ""
    title: str = ""
    body: str = ""
    works: str = ""


def compile_document(document: dict, export: bool = False):
    node = shutil.which("node")
    if node is None:
        raise HTTPException(503, "Node.js is required for the server MLA compiler; browser export works offline.")
    # Code and module path are fixed. User content travels only through stdin.
    program = (
        "const m=require(process.argv[1]);let s='';process.stdin.setEncoding('utf8');"
        "process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{"
        "try{const x=JSON.parse(s);const d=m.clean(x.document);"
        "const out={checks:m.validate(d),filename:m.filename(d,true)};"
        "if(x.export)out.base64=Buffer.from(m.docx(d)).toString('base64');"
        "process.stdout.write(JSON.stringify(out));}"
        "catch(e){process.stdout.write(JSON.stringify({error:e.message}));process.exitCode=2;}});"
    )
    try:
        result = subprocess.run(
            [node, "-e", program, str(HERE / "mla_web" / "core.js")],
            input=json.dumps({"document": document, "export": export}),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(503, "Document compiler timed out") from exc
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(503, "Document compiler is unavailable") from exc
    if result.returncode:
        raise HTTPException(422, payload.get("error", "Invalid document"))
    return payload


@router.get("/mla", include_in_schema=False)
def redirect():
    return RedirectResponse("/mla/")


@router.get("/mla/", include_in_schema=False)
def editor():
    return FileResponse(HERE / "mla_web" / "index.html")


@router.get("/mla/profile.json", include_in_schema=False)
@router.get("/mla/api/profile")
def profile():
    return json.loads((HERE / "mla_profile.json").read_text(encoding="utf-8"))


@router.get("/mla/{asset}", include_in_schema=False)
def assets(asset: Literal["core.js", "app.js", "style.css"]):
    return FileResponse(HERE / "mla_web" / asset)


@router.post("/mla/api/validate")
def validate(document: MLADocument):
    return checked("read", lambda: compile_document(document.model_dump()))


@router.post("/mla/api/export.docx")
def export(document: MLADocument):
    payload = checked("export", lambda: compile_document(document.model_dump(), export=True))
    return Response(
        base64.b64decode(payload["base64"]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": "attachment; filename=\"My MLA Template.docx\"; filename*=UTF-8''"
            + quote(payload["filename"])
        },
    )
