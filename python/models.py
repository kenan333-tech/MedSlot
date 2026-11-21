"""MedSlot: 4 cədvəlin SQLAlchemy modelləri.

doctors       — həkimlər və iş saatları
slots         — 30 dəqiqəlik vaxtlar (free / booked)
patients      — pasiyentlər (telefon unikaldır)
appointments  — yazılışlar (booked / cancelled)
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    specialty = Column(String(50), nullable=False)
    work_start = Column(Time, nullable=False)  # məs. 09:00
    work_end = Column(Time, nullable=False)    # məs. 15:00

    slots = relationship("Slot", back_populates="doctor")

    __table_args__ = (
        CheckConstraint("work_start < work_end", name="ck_doctor_hours"),
    )


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(10), nullable=False, default="free")

    doctor = relationship("Doctor", back_populates="slots")

    __table_args__ = (
        # Eyni həkimə eyni saat iki dəfə yaradılmasın
        UniqueConstraint("doctor_id", "start_at", name="uq_slot_doctor_time"),
        CheckConstraint("status IN ('free', 'booked')", name="ck_slot_status"),
    )


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True)
    chat_id = Column(String(30))  # boşdursa, Telegram demo chat_id-yə gedir


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    complaint = Column(Text)
    status = Column(String(10), nullable=False, default="booked")
    reminded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('booked', 'cancelled')", name="ck_appt_status"),
        # İkinci qoruma qatı: bir slota yalnız BİR aktiv yazılış ola bilər.
        # Ləğv olunmuş yazılışlar bu qaydaya daxil deyil.
        Index(
            "uq_active_appointment_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'booked'"),
        ),
    )
