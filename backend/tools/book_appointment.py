import os
import re
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
from database import SessionLocal

DOCTOR = 'Akshat Shukla'


def _clean_doctor(name: str) -> str:
    # normalize doctor name text
    s = (name or '').strip().lower()
    return s[4:].strip() if s.startswith('dr. ') else s[3:].strip() if s.startswith('dr ') else s


def _valid_time(t: str) -> bool:
    # validate hh:mm time format
    return bool(re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', (t or '').strip()))


def _is_email(v: str) -> bool:
    # quick email format check
    v = (v or '').strip()
    return '@' in v and '.' in v.split('@')[-1]


def _calendar(patient, date, time, reason, email):
    # create calendar event entry
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        load_dotenv()
        key = os.path.join(os.path.dirname(__file__), '..', 'serviceAccount.json')
        if not os.path.exists(key):
            return '[Google Calendar] Skipped - serviceAccount.json not found.'

        creds = service_account.Credentials.from_service_account_file(key, scopes=['https://www.googleapis.com/auth/calendar'])
        service = build('calendar', 'v3', credentials=creds)

        start = datetime.fromisoformat(f'{date}T{time}:00')
        event = {
            'summary': f'Appointment: {patient} with Dr. {DOCTOR}',
            'description': f'Reason: {reason}',
            'start': {'dateTime': start.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': (start + timedelta(minutes=30)).isoformat(), 'timeZone': 'Asia/Kolkata'},
        }
        if _is_email(email):
            event['attendees'] = [{'email': email}]

        created = service.events().insert(
            calendarId=os.getenv('GOOGLE_CALENDAR_ID', 'primary'),
            body=event,
            sendUpdates='all' if event.get('attendees') else 'none',
        ).execute()
        return f"[Google Calendar] Event created -> {created.get('htmlLink', '')}"
    except Exception as e:
        return f'[Google Calendar] Failed: {e}'


def _email(patient, date, time, reason, patient_email):
    # send booking confirmation email
    try:
        load_dotenv()
        user = os.getenv('GMAIL_USER', '')
        pwd = os.getenv('GMAIL_APP_PASSWORD', '')
        to = patient_email.strip() if _is_email(patient_email) else os.getenv('PATIENT_EMAIL', user)
        if not user or not pwd:
            return '[Email] Skipped - set GMAIL_USER and GMAIL_APP_PASSWORD.'

        msg = MIMEText(f'Dear {patient},\n\nAppointment confirmed with Dr. {DOCTOR}\nDate: {date}\nTime: {time}\nReason: {reason}')
        msg['Subject'] = f'Appointment Confirmed - Dr. {DOCTOR} on {date}'
        msg['From'] = user
        msg['To'] = to

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(user, pwd)
            smtp.sendmail(user, to, msg.as_string())
        return f'[Email] Confirmation sent to {to}'
    except Exception as e:
        return f'[Email] Failed: {e}'


def book_appointment(doctor_name: str, patient_name: str, date: str, time: str, reason: str = 'General Consultation', patient_email: str = '') -> str:
    # validate and save booking
    patient = (patient_name or '').strip()
    if not patient or patient.lower() in {'patient', 'unknown', 'na', 'n/a', 'none', 'not provided'}:
        return 'Patient name is required before booking.'
    if _clean_doctor(doctor_name) not in DOCTOR.lower():
        return f'Dr. {doctor_name} is not on our staff. Available doctors are: {DOCTOR}.'
    if not _valid_time(time):
        return 'Invalid time format. Use HH:MM.'

    db = SessionLocal()
    try:
        clash = db.query(models.Appointment).filter(
            models.Appointment.doctor_name.ilike(f'%{DOCTOR}%'),
            models.Appointment.date == date,
            models.Appointment.time == time,
        ).first()
        if clash:
            return f'Sorry, Dr. {DOCTOR} is already booked at {time} on {date}.'

        db.add(models.Appointment(doctor_name=DOCTOR, patient_name=patient, date=date, time=time, reason=reason, status='booked'))
        db.commit()
    except Exception as e:
        db.rollback()
        return f'Database error: {e}'
    finally:
        db.close()

    cal = _calendar(patient, date, time, reason, patient_email)
    mail = _email(patient, date, time, reason, patient_email)
    return (
        '✅ Appointment booked!\n'
        f'Patient : {patient}\nDoctor  : Dr. {DOCTOR}\nDate    : {date}\nTime    : {time}\nReason  : {reason}\n\n'
        f'{cal}\n{mail}'
    )
