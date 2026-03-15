from sqlalchemy import Column, Integer, String
from database import Base

# stores appointment row fields
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_name = Column(String, index=True)
    patient_name = Column(String, index=True)
    date = Column(String)      # YYYY-MM-DD
    time = Column(String)      # HH:MM
    reason = Column(String, default="General Consultation")
    status = Column(String, default="booked")
