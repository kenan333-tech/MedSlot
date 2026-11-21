"""Hər həkimin iş saatlarından növbəti 7 gün üçün 30 dəqiqəlik boş saatlar yaradır.

İşə salma:
    python slot_generator.py --once   # bir dəfə işlə və çıx
    python slot_generator.py          # worker: hər saat yenidən yoxlayır

Mövcud saatlar təkrar yaradılmır (set ilə yoxlanılır).
Bazar günü klinika bağlıdır.
"""
import sys
import time as time_module
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from db import SessionLocal, TIMEZONE
from models import Doctor, Slot

TZ = ZoneInfo(TIMEZONE)
DAYS_AHEAD = 7
SLOT_MINUTES = 30
SLEEP_SECONDS = 3600
SUNDAY = 6


def build_times_for_day(day, work_start, work_end):
    """Bir gün üçün bütün slotların başlama vaxtları (list)."""
    start = datetime.combine(day, work_start, tzinfo=TZ)
    end = datetime.combine(day, work_end, tzinfo=TZ)
    times = []
    current = start
    while current + timedelta(minutes=SLOT_MINUTES) <= end:
        times.append(current)
        current += timedelta(minutes=SLOT_MINUTES)
    return times


def generate_once():
    session = SessionLocal()
    try:
        now = datetime.now(TZ)
        today = now.date()
        horizon = now + timedelta(days=DAYS_AHEAD + 1)

        # Artıq mövcud olan (doctor_id, start_at) cütləri — set
        existing = {
            (doctor_id, start_at)
            for doctor_id, start_at in session.query(Slot.doctor_id, Slot.start_at)
            .filter(Slot.start_at >= now, Slot.start_at < horizon)
            .all()
        }

        created = 0
        for doctor in session.query(Doctor).all():
            for offset in range(DAYS_AHEAD):
                day = today + timedelta(days=offset)
                if day.weekday() == SUNDAY:
                    continue
                for start_at in build_times_for_day(day, doctor.work_start, doctor.work_end):
                    if start_at <= now:
                        continue  # keçmiş saatları yaratmırıq
                    key = (doctor.id, start_at)
                    if key in existing:
                        continue
                    session.add(Slot(doctor_id=doctor.id, start_at=start_at, status="free"))
                    existing.add(key)
                    created += 1

        session.commit()
        print(f"[{now:%Y-%m-%d %H:%M}] ✓ {created} yeni slot yaradıldı")
        return created
    finally:
        session.close()


def main():
    if "--once" in sys.argv:
        generate_once()
        return

    print("Slot generator worker işləyir (dayandırmaq: Ctrl+C)")
    while True:
        try:
            generate_once()
        except Exception as e:  # baza müvəqqəti əlçatmaz olsa da worker ölməsin
            print("Xəta:", e)
        time_module.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
