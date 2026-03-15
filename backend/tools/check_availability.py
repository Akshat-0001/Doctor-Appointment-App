import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
from database import SessionLocal

VALID_DOCTOR = "Akshat Shukla"
ALL_SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
]
MORNING = [t for t in ALL_SLOTS if t < "12:00"]
AFTERNOON = [t for t in ALL_SLOTS if t >= "14:00"]


def _clean_doctor(name: str) -> str:
    # normalize doctor name input
    name = (name or "").strip().lower()
    if name.startswith("dr. "):
        name = name[4:]
    elif name.startswith("dr "):
        name = name[3:]
    return name.strip()


def check_doctor_availability(doctor_name: str, date: str, time_range: str = "all") -> str:
    # return open slots list
    requested = _clean_doctor(doctor_name)
    if requested not in VALID_DOCTOR.lower():
        return f"Dr. {doctor_name} is not on our staff. Available doctors are: {VALID_DOCTOR}."

    db = SessionLocal()
    try:
        booked = db.query(models.Appointment).filter(
            models.Appointment.doctor_name.ilike(f"%{VALID_DOCTOR}%"),
            models.Appointment.date == date,
        ).all()
    finally:
        db.close()

    booked_times = {a.time for a in booked}
    pool = MORNING if "morning" in time_range.lower() else AFTERNOON if "afternoon" in time_range.lower() else ALL_SLOTS
    available = [t for t in pool if t not in booked_times]

    if not available:
        return f"Dr. {VALID_DOCTOR} has NO available slots for {time_range} on {date}."
    return f"Available slots for Dr. {VALID_DOCTOR} on {date} ({time_range}): {', '.join(available)}"
