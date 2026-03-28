"""
Aethermoor Outreach -- FastAPI backend.
Civic and business workflow engine for Port Angeles, WA.

This is an assistive interface, not an official government agent.
Human review is required on all outbound messages.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as SASession

from .models import (
    Base,
    Case,
    CaseEvent,
    Document,
    Message,
    Project,
    RoutingTarget,
    WorkflowStep,
    get_engine,
    get_session,
    init_db,
)
from .services.documents import generate_document, get_available_doc_types
from .services.intent import classify_intent, get_all_intents
from .services.opportunity import get_all_locations, get_opportunity_profile
from .services.routing import get_routing_targets, seed_routing_targets_to_db
from .services.workflow import generate_workflow

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DB_DIR / "outreach.db"
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Aethermoor Outreach",
    description="AI-powered civic and business workflow engine for Port Angeles, WA. "
                "This is an assistive interface -- not an official government agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _db() -> SASession:
    return get_session(str(DB_PATH))


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class IntakeRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=100)
    intent: str = Field(..., min_length=1)


class IntentCompileRequest(BaseModel):
    text: str = Field(..., min_length=1)


class DocumentGenerateRequest(BaseModel):
    case_id: int
    doc_type: str
    context: Optional[dict] = None


class RoutingRecommendRequest(BaseModel):
    intent: str


class MessageDraftRequest(BaseModel):
    case_id: int
    routing_target_id: Optional[int] = None
    to_email: Optional[str] = None
    subject: Optional[str] = None
    doc_type: Optional[str] = "general_inquiry"
    context: Optional[dict] = None


class CaseCreateRequest(BaseModel):
    project_id: int


class CaseEventRequest(BaseModel):
    event_type: str
    description: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "aethermoor-outreach",
        "version": "1.0.0",
        "notice": "This is an assistive interface -- not an official government agent.",
    }


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------

@app.post("/api/intake")
def submit_intake(req: IntakeRequest):
    """Submit an intent -- creates a project, classifies intent, generates workflow, and creates a case."""
    session = _db()
    try:
        # Classify
        classification = classify_intent(req.intent)

        # Create project
        project = Project(
            name=req.name,
            location=req.location,
            intent=req.intent,
            intent_classified=classification["intent"],
        )
        session.add(project)
        session.flush()

        # Create case
        case = Case(project_id=project.id, status="open")
        session.add(case)
        session.flush()

        # Generate workflow and persist steps
        steps = generate_workflow(classification["intent"])
        for s in steps:
            ws = WorkflowStep(
                case_id=case.id,
                step_number=s["step_number"],
                description=s["description"],
                agency=s.get("agency", ""),
                estimated_time=s.get("estimated_time", ""),
                required_docs=s.get("required_docs", ""),
                status="pending",
            )
            session.add(ws)

        # Log intake event
        event = CaseEvent(
            case_id=case.id,
            event_type="intake_submitted",
            description=f"Intake submitted by {req.name} for '{req.intent}' in {req.location}. Classified as: {classification['intent']}.",
        )
        session.add(event)
        session.commit()

        return {
            "project_id": project.id,
            "case_id": case.id,
            "classification": classification,
            "workflow_steps": steps,
            "message": "Intake received. Workflow generated. Case created.",
        }
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/intake/{project_id}")
def get_intake(project_id: int):
    """Get project details including cases and workflow steps."""
    session = _db()
    try:
        project = session.query(Project).filter_by(id=project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        cases = []
        for case in project.cases:
            steps = [
                {
                    "id": ws.id,
                    "step_number": ws.step_number,
                    "description": ws.description,
                    "agency": ws.agency,
                    "estimated_time": ws.estimated_time,
                    "required_docs": ws.required_docs,
                    "status": ws.status,
                    "completed_at": ws.completed_at.isoformat() if ws.completed_at else None,
                }
                for ws in sorted(case.workflow_steps, key=lambda w: w.step_number)
            ]
            events = [
                {
                    "id": ev.id,
                    "event_type": ev.event_type,
                    "description": ev.description,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
                for ev in sorted(case.events, key=lambda e: e.created_at)
            ]
            cases.append({
                "id": case.id,
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None,
                "workflow_steps": steps,
                "events": events,
                "documents_count": len(case.documents),
                "messages_count": len(case.messages),
            })

        return {
            "id": project.id,
            "name": project.name,
            "location": project.location,
            "intent": project.intent,
            "intent_classified": project.intent_classified,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "cases": cases,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Intent
# ---------------------------------------------------------------------------

@app.post("/api/intent/compile")
def compile_intent(req: IntentCompileRequest):
    """Classify intent text and return structured workflow."""
    classification = classify_intent(req.text)
    steps = generate_workflow(classification["intent"])
    return {
        "classification": classification,
        "workflow_steps": steps,
        "available_doc_types": get_available_doc_types(),
    }


# ---------------------------------------------------------------------------
# Locations / Opportunity
# ---------------------------------------------------------------------------

@app.get("/api/locations")
def list_locations():
    """List all available location profiles."""
    return {"locations": get_all_locations()}


@app.get("/api/locations/{location}/opportunity")
def get_location_opportunity(location: str):
    """Get the opportunity profile for a location area."""
    profile = get_opportunity_profile(location)
    if not profile:
        raise HTTPException(status_code=404, detail=f"No opportunity profile for '{location}'. Available: downtown, waterfront, east_side, west_end")
    return profile


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.post("/api/documents/generate")
def gen_document(req: DocumentGenerateRequest):
    """Generate a document for a case."""
    session = _db()
    try:
        case = session.query(Case).filter_by(id=req.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        project = case.project
        ctx = req.context or {}
        ctx.setdefault("name", project.name)
        ctx.setdefault("location", project.location)
        ctx.setdefault("intent", project.intent)

        doc_data = generate_document(req.doc_type, ctx)

        doc = Document(
            case_id=case.id,
            doc_type=doc_data["doc_type"],
            title=doc_data["title"],
            content=doc_data["content"],
        )
        session.add(doc)

        event = CaseEvent(
            case_id=case.id,
            event_type="document_generated",
            description=f"Generated document: {doc_data['title']} ({doc_data['doc_type']})",
        )
        session.add(event)
        session.commit()

        return {
            "document_id": doc.id,
            "title": doc_data["title"],
            "doc_type": doc_data["doc_type"],
            "content": doc_data["content"],
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/documents/types")
def list_doc_types():
    """List all available document types."""
    return {"doc_types": get_available_doc_types()}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

@app.post("/api/routing/recommend")
def recommend_routing(req: RoutingRecommendRequest):
    """Get routing targets for an intent."""
    targets = get_routing_targets(req.intent)
    if not targets:
        targets = get_routing_targets()  # Fall back to all targets
    return {
        "intent": req.intent,
        "targets": targets,
        "notice": "Contact information is provided for reference. Please verify hours and availability before visiting.",
    }


@app.get("/api/routing/targets")
def list_all_routing():
    """List all routing targets."""
    return {"targets": get_routing_targets()}


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@app.post("/api/messages/draft")
def draft_message(req: MessageDraftRequest):
    """Draft an outreach message for a case. HUMAN REVIEW REQUIRED before sending."""
    session = _db()
    try:
        case = session.query(Case).filter_by(id=req.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        project = case.project
        ctx = req.context or {}
        ctx.setdefault("name", project.name)
        ctx.setdefault("location", project.location)
        ctx.setdefault("intent", project.intent)

        doc_data = generate_document(req.doc_type or "general_inquiry", ctx)

        msg = Message(
            case_id=case.id,
            routing_target_id=req.routing_target_id,
            to_email=req.to_email or "",
            subject=req.subject or doc_data["title"],
            body=doc_data["content"],
            status="draft",
        )
        session.add(msg)

        event = CaseEvent(
            case_id=case.id,
            event_type="message_drafted",
            description=f"Message drafted: {msg.subject}. HUMAN REVIEW REQUIRED before sending.",
        )
        session.add(event)
        session.commit()

        return {
            "message_id": msg.id,
            "subject": msg.subject,
            "body": msg.body,
            "status": "draft",
            "notice": "HUMAN REVIEW REQUIRED. This message has NOT been sent. Review and edit before sending manually.",
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

@app.post("/api/cases")
def create_case(req: CaseCreateRequest):
    """Create a new case for an existing project."""
    session = _db()
    try:
        project = session.query(Project).filter_by(id=req.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        case = Case(project_id=project.id, status="open")
        session.add(case)
        session.flush()

        # Generate workflow for the project's classified intent
        steps = generate_workflow(project.intent_classified or "general_inquiry")
        for s in steps:
            ws = WorkflowStep(
                case_id=case.id,
                step_number=s["step_number"],
                description=s["description"],
                agency=s.get("agency", ""),
                estimated_time=s.get("estimated_time", ""),
                required_docs=s.get("required_docs", ""),
                status="pending",
            )
            session.add(ws)

        event = CaseEvent(
            case_id=case.id,
            event_type="case_created",
            description=f"New case created for project #{project.id} ({project.name}).",
        )
        session.add(event)
        session.commit()

        return {
            "case_id": case.id,
            "project_id": project.id,
            "status": case.status,
            "workflow_steps": steps,
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.get("/api/cases/{case_id}")
def get_case(case_id: int):
    """Get case details including workflow steps, documents, messages, and events."""
    session = _db()
    try:
        case = session.query(Case).filter_by(id=case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        steps = [
            {
                "id": ws.id,
                "step_number": ws.step_number,
                "description": ws.description,
                "agency": ws.agency,
                "estimated_time": ws.estimated_time,
                "required_docs": ws.required_docs,
                "status": ws.status,
                "completed_at": ws.completed_at.isoformat() if ws.completed_at else None,
            }
            for ws in sorted(case.workflow_steps, key=lambda w: w.step_number)
        ]

        documents = [
            {
                "id": d.id,
                "doc_type": d.doc_type,
                "title": d.title,
                "content": d.content,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in case.documents
        ]

        messages = [
            {
                "id": m.id,
                "to_email": m.to_email,
                "subject": m.subject,
                "body": m.body,
                "status": m.status,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            }
            for m in case.messages
        ]

        events = [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "description": ev.description,
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in sorted(case.events, key=lambda e: e.created_at)
        ]

        return {
            "id": case.id,
            "project_id": case.project_id,
            "project_name": case.project.name,
            "status": case.status,
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "updated_at": case.updated_at.isoformat() if case.updated_at else None,
            "workflow_steps": steps,
            "documents": documents,
            "messages": messages,
            "events": events,
        }
    finally:
        session.close()


@app.post("/api/cases/{case_id}/events")
def add_case_event(case_id: int, req: CaseEventRequest):
    """Add an event to a case timeline."""
    session = _db()
    try:
        case = session.query(Case).filter_by(id=case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        event = CaseEvent(
            case_id=case.id,
            event_type=req.event_type,
            description=req.description,
        )
        session.add(event)
        session.commit()

        return {
            "event_id": event.id,
            "case_id": case.id,
            "event_type": event.event_type,
            "description": event.description,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/api/dashboard")
def dashboard():
    """Get summary of all projects and cases."""
    session = _db()
    try:
        projects = session.query(Project).order_by(Project.created_at.desc()).all()
        result = []
        for p in projects:
            cases_summary = []
            for c in p.cases:
                total_steps = len(c.workflow_steps)
                completed_steps = len([ws for ws in c.workflow_steps if ws.status == "completed"])
                cases_summary.append({
                    "id": c.id,
                    "status": c.status,
                    "total_steps": total_steps,
                    "completed_steps": completed_steps,
                    "documents_count": len(c.documents),
                    "messages_count": len(c.messages),
                    "events_count": len(c.events),
                })
            result.append({
                "id": p.id,
                "name": p.name,
                "location": p.location,
                "intent": p.intent,
                "intent_classified": p.intent_classified,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "cases": cases_summary,
            })
        return {
            "total_projects": len(result),
            "projects": result,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Intents (reference)
# ---------------------------------------------------------------------------

@app.get("/api/intents")
def list_intents():
    """List all known intent categories."""
    return {"intents": get_all_intents()}


# ---------------------------------------------------------------------------
# Frontend static files (must be last to avoid catching API routes)
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
