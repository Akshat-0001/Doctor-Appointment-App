import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
from database import SessionLocal


def doctor_summary_report(date: str) -> str:
    # build daily summary text
    db = SessionLocal()
    try:
        appts = db.query(models.Appointment).filter(models.Appointment.date == date).all()
    except Exception as exc:
        return f"Database error: {exc}"
    finally:
        db.close()

    total = len(appts)
    fever = sum(1 for a in appts if a.reason and "fever" in a.reason.lower())

    lines = [
        f"=== Report for {date} ===",
        f"Total appointments : {total}",
        f"Fever-related      : {fever}",
        "",
    ]
    for a in appts:
        lines.append(f"  {a.time} - {a.patient_name} (Dr. {a.doctor_name}) - {a.reason}")

    report = "\n".join(lines)
    return report + f"\n\n[Firebase] {_push_to_firebase(date, total, report)}"


def _push_to_firebase(date: str, total: int, body: str) -> str:
    # push report into firestore
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        file_path = os.path.join(backend_dir, env_path) if env_path and not os.path.isabs(env_path) else env_path
        fallback = os.path.join(backend_dir, "serviceAccount.json")
        cred_path = file_path if file_path and os.path.exists(file_path) else fallback if os.path.exists(fallback) else ""

        service_email = "unknown"
        if cred_path:
            with open(cred_path, "r", encoding="utf-8") as f:
                service_email = json.load(f).get("client_email", "unknown")

        if not firebase_admin._apps:
            if cred_path:
                firebase_admin.initialize_app(credentials.Certificate(cred_path))
            else:
                firebase_admin.initialize_app()

        fs = firestore.client()
        fs.collection("notifications").add(
            {
                "message": f"Daily Report - {total} patient(s) on {date}",
                "body": body,
                "date": date,
                "timestamp": firestore.SERVER_TIMESTAMP,
            }
        )
        return f"Notification saved (service account: {service_email})."
    except Exception as exc:
        return f"Firebase skipped: {exc}"
