import os
import json
from datetime import date

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database
import models
import uvicorn

load_dotenv()
# make sure tables exist
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Doctor Appointment MCP Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PATIENT_PROMPT = (
    "You are a medical booking assistant. Only doctor is Dr. Akshat Shukla. "
    "Use MCP tools for availability, booking, summary. Ask for patient name and time in HH:MM. "
    "Use date format YYYY-MM-DD. Today is {today}."
)
DOCTOR_PROMPT = (
    "You are a doctor dashboard assistant for Dr. Akshat Shukla. "
    "Use tools for reports/appointments. Today is {today}."
)


class ChatRequest(BaseModel):
    message: str
    history: list = Field(default_factory=list)
    role: str = "patient"


class DoctorLoginRequest(BaseModel):
    username: str
    password: str


class DoctorReportRequest(BaseModel):
    date: str | None = None


class DoctorAppointmentsRequest(BaseModel):
    scope: str = "upcoming"  # today | tomorrow | upcoming | all | custom
    date: str | None = None


@app.post('/chat')
async def chat(req: ChatRequest):
    # handle user chat flow
    from agent import get_mcp_response

    prompt = DOCTOR_PROMPT if req.role == 'doctor' else PATIENT_PROMPT
    msgs = [{"role": "system", "content": prompt.format(today=date.today())}, *req.history, {"role": "user", "content": req.message}]
    try:
        return {"reply": await get_mcp_response(msgs)}
    except Exception as e:
        text = str(e).lower()
        if 'rate limit' in text or 'rate_limit_exceeded' in text:
            raise HTTPException(429, 'LLM rate limit reached. Retry in a few minutes.')
        raise HTTPException(503, 'AI service temporarily unavailable.')


@app.post('/doctor/login')
async def doctor_login(req: DoctorLoginRequest):
    # check doctor credentials only
    if req.username == os.getenv('DOCTOR_USERNAME', 'akshat') and req.password == os.getenv('DOCTOR_PASSWORD', 'akshat123'):
        return {"ok": True, "role": "doctor"}
    raise HTTPException(401, 'Invalid doctor credentials')


@app.post('/doctor/report')
async def doctor_report(req: DoctorReportRequest):
    # build daily doctor report
    from agent import call_mcp_tool
    d = req.date or str(date.today())
    return {"date": d, "report": await call_mcp_tool('doctor_summary_report_tool', {"date": d})}


@app.post('/doctor/appointments')
async def doctor_appointments(req: DoctorAppointmentsRequest):
    # fetch filtered appointments list
    from agent import call_mcp_tool
    scope = (req.scope or 'upcoming').lower().strip()
    text = await call_mcp_tool('doctor_appointments_tool', {"scope": scope, "date_value": req.date or ""})
    try:
        return json.loads(text)
    except Exception:
        raise HTTPException(500, 'Invalid MCP response for appointments.')


if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8030, reload=True)
