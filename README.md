# Doctor Appointment Assistant (Agentic AI + MCP)

a minimal full-stack app showing **Agentic AI** in action using the **Model Context Protocol**. patients can book appointments through a chat interface, and doctors get a dashboard with ai-generated daily summaries.

## walkthrough

![App walkthrough](frontend/assets/walkthrough-video.gif)

## how it's built

- **Frontend (React)** — chat UI for patients + doctor dashboard
- **Backend (FastAPI)** — handles requests
- **Agent** — uses Groq LLM, talks to the MCP server via STDIO to discover and call tools
- **MCP Server** — exposes db operations as pure MCP tools. no direct function calls from agent logic
- **Database** — PostgreSQL for appointments
- **Extras** — Google Calendar & email integration so that appointments notif is sent to mail; Firebase Firestore handles real-time doctor notifications
---

## setup

### prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (optional). by default it runs on SQLite.

### backend
```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

set your env vars:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
export GROQ_API_KEY="your-groq-api-key"
export DOCTOR_USERNAME="akshat"
export DOCTOR_PASSWORD="akshat123"
```

if you want sqlite only, skip `DATABASE_URL` and it will use local `appointments.db`.

run it:
```bash
uvicorn main:app --host 127.0.0.1 --port 8030 --reload
```

### frontend
```bash
cd frontend
npm install
npm run dev -- --port 5173
```

> optionally, drop your Firebase config in `src/firebase.js`. if left empty, it just skips silently.

---

## things to try

## sample prompts

**as a patient:**
- *"What times are available for Dr. Akshat Shukla tomorrow morning?"*
- *"Book an appointment with Dr. Akshat Shukla for Sahil Rana at 10 AM tomorrow."*
- *"Book Dr. Akshat on 2026-03-20 at 14:30 for Rahul Mehra, fever and headache."*
- *"I want evening slots with Dr. Akshat on 2026-03-21."*

> heads up: the assistant will ask for a patient name if you forget to include one.

**as a doctor:**
- log in on the frontend and hit **"Generate Today's Report"**
- or just type: *"Generate the summary report for 2024-11-20."*
- *"Show upcoming appointments."*
- *"Show tomorrow appointments."*

---

## api usage summary

base url:
- backend: `http://127.0.0.1:8030`

main endpoints:

1. `POST /chat`
used by patient/doctor chat flow.

request body:
```json
{
	"message": "book dr akshat tomorrow at 10:00 for john doe",
	"history": [],
	"role": "patient"
}
```

2. `POST /doctor/login`
simple doctor-only login check.

request body:
```json
{
	"username": "akshat",
	"password": "akshat123"
}
```

3. `POST /doctor/report`
generates a daily summary report and pushes firestore notification.

request body:
```json
{
	"date": "2026-03-15"
}
```

4. `POST /doctor/appointments`
returns structured doctor appointment list.

request body:
```json
{
	"scope": "upcoming",
	"date": null
}
```

scope values:
- `today`
- `tomorrow`
- `upcoming`
- `all`
- `custom` (send date too)

---

## how MCP works here (quick version)

1. user sends a message → FastAPI picks it up
2. `agent.py` spawns `mcp_server.py` over stdio
3. agent calls `list_tools()` to discover what's available
4. Groq LLM picks the right tool based on the prompt
5. agent calls `call_tool()` → mcp server runs the logic (db, mocks, firebase)
6. result flows back through the LLM → user gets a clean response