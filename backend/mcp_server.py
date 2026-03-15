from mcp.server.fastmcp import FastMCP
import json
from datetime import date, timedelta

from tools.book_appointment import book_appointment
from tools.check_availability import check_doctor_availability
from tools.doctor_summary import doctor_summary_report
import database
import models

mcp = FastMCP("DoctorAssistant")


@mcp.tool()
def check_doctor_availability_tool(doctor_name: str, date: str, time_range: str = "all") -> str:
    # expose availability as tool
    return check_doctor_availability(doctor_name, date, time_range)


@mcp.tool()
def book_appointment_tool(
    doctor_name: str,
    patient_name: str,
    date: str,
    time: str,
    reason: str = "General Consultation",
    patient_email: str = "",
) -> str:
    # expose booking as tool
    return book_appointment(doctor_name, patient_name, date, time, reason, patient_email)


@mcp.tool()
def doctor_summary_report_tool(date: str) -> str:
    # expose summary as tool
    return doctor_summary_report(date)


@mcp.tool()
def doctor_appointments_tool(scope: str = "upcoming", date_value: str = "") -> str:
    # return filtered appointments json
    today = str(date.today())
    tomorrow = str(date.today() + timedelta(days=1))
    scope = (scope or 'upcoming').lower().strip()
    target = date_value or None

    db = database.SessionLocal()
    try:
        q = db.query(models.Appointment).filter(models.Appointment.doctor_name.ilike('%Akshat Shukla%'))
        if scope == 'today':
            q = q.filter(models.Appointment.date == today)
        elif scope == 'tomorrow':
            q = q.filter(models.Appointment.date == tomorrow)
        elif scope == 'custom' and target:
            q = q.filter(models.Appointment.date == target)
        elif scope != 'all':
            q = q.filter(models.Appointment.date >= today)

        rows = q.order_by(models.Appointment.date.asc(), models.Appointment.time.asc()).all()
        out = {
            "scope": scope,
            "date": target,
            "count": len(rows),
            "appointments": [
                {
                    "id": a.id,
                    "doctor_name": a.doctor_name,
                    "patient_name": a.patient_name,
                    "date": a.date,
                    "time": a.time,
                    "reason": a.reason,
                    "status": a.status,
                }
                for a in rows
            ],
        }
        return json.dumps(out)
    finally:
        db.close()


if __name__ == "__main__":
    # start mcp tool server
    mcp.run()
