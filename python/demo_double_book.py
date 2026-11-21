"""Demo: eyni saata iki yazılışın alınmadığını göstərir.

İşə salma:  python demo_double_book.py
(n8n-də W1 workflow-u aktiv olmalıdır.)
"""
from datetime import date, timedelta

import requests

BASE = "http://localhost:5678/webhook/medslot"


def main():
    doctors = requests.get(f"{BASE}/doctors", timeout=10).json()["doctors"]
    doctor = doctors[0]

    # Növbəti 7 gün içində ilk boş saatı tap
    slot = None
    for i in range(7):
        day = (date.today() + timedelta(days=i)).isoformat()
        slots = requests.get(f"{BASE}/slots",
                             params={"doctor_id": doctor["id"], "date": day},
                             timeout=10).json()["slots"]
        if slots:
            slot = slots[0]
            break

    if not slot:
        print("Boş saat tapılmadı. Əvvəlcə slot_generator.py işə sal.")
        return

    print(f"Həkim: {doctor['full_name']}, saat: {slot['date']} {slot['time']} (slot_id={slot['id']})\n")

    patients = [
        {"full_name": "Pasiyent Bir", "phone": "+994501111111"},
        {"full_name": "Pasiyent İki", "phone": "+994502222222"},
    ]
    for p in patients:
        body = {"slot_id": slot["id"], "complaint": "demo", **p}
        r = requests.post(f"{BASE}/book", json=body, timeout=10)
        print(f"{p['full_name']}: HTTP {r.status_code} → {r.json()}")


if __name__ == "__main__":
    main()
