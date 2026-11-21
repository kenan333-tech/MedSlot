"""Cədvəlləri yaradır və 6 demo həkim əlavə edir.

İşə salma:  python seed.py
Təkrar işə salmaq təhlükəsizdir: mövcud həkimlər yenidən yazılmır.
"""
from datetime import time

from sqlalchemy import text

from db import SessionLocal, engine, TIMEZONE
from models import Base, Doctor

DOCTORS = [
    {"full_name": "Dr. Aynur Məmmədova", "specialty": "Terapevt",
     "work_start": time(9, 0), "work_end": time(15, 0)},
    {"full_name": "Dr. Rəşad Əliyev", "specialty": "Nevroloq",
     "work_start": time(10, 0), "work_end": time(16, 0)},
    {"full_name": "Dr. Leyla Hüseynova", "specialty": "Kardioloq",
     "work_start": time(9, 0), "work_end": time(14, 0)},
    {"full_name": "Dr. Elvin Quliyev", "specialty": "Qastroenteroloq",
     "work_start": time(11, 0), "work_end": time(17, 0)},
    {"full_name": "Dr. Nərmin Kərimova", "specialty": "Dermatoloq",
     "work_start": time(9, 30), "work_end": time(15, 30)},
    {"full_name": "Dr. Kamran İsmayılov", "specialty": "LOR",
     "work_start": time(12, 0), "work_end": time(18, 0)},
]


def main():
    # 1. Bazanın saat qurşağı (n8n-in Postgres node-u da bunu görsün)
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text(f"ALTER DATABASE layihe SET timezone TO '{TIMEZONE}'")
        )

    # 2. Cədvəllər
    Base.metadata.create_all(engine)
    print("✓ Cədvəllər hazırdır: doctors, slots, patients, appointments")

    # 3. Həkimlər
    session = SessionLocal()
    try:
        existing = {name for (name,) in session.query(Doctor.full_name).all()}
        added = 0
        for d in DOCTORS:
            if d["full_name"] in existing:
                continue
            session.add(Doctor(**d))
            added += 1
        session.commit()
        print(f"✓ {added} yeni həkim əlavə olundu (cəmi {len(DOCTORS)})")
    finally:
        session.close()

    print("Növbəti addım: python slot_generator.py --once")


if __name__ == "__main__":
    main()
