"""Hər həkim üzrə növbə sayı və doluluq faizi (psycopg2 ilə).

İşə salma:  python report.py          # növbəti 7 gün
            python report.py 30       # növbəti 30 gün
"""
import sys

import psycopg2
import psycopg2.extras

from db import PSYCOPG_DSN

QUERY = """
SELECT d.full_name,
       d.specialty,
       COUNT(s.id)                                        AS total_slots,
       COUNT(s.id) FILTER (WHERE s.status = 'booked')     AS booked_slots,
       (SELECT COUNT(*)
          FROM appointments a
          JOIN slots s2 ON s2.id = a.slot_id
         WHERE s2.doctor_id = d.id
           AND a.status = 'cancelled')                    AS cancelled
  FROM doctors d
  LEFT JOIN slots s
         ON s.doctor_id = d.id
        AND s.start_at >= now()
        AND s.start_at <  now() + make_interval(days => %s)
 GROUP BY d.id
 ORDER BY d.full_name;
"""


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    conn = psycopg2.connect(PSYCOPG_DSN)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(QUERY, (days,))
            rows = cur.fetchall()  # hər sətir dict-dir
    finally:
        conn.close()

    print(f"\nMedSlot hesabatı — növbəti {days} gün\n")
    print(f"{'Həkim':<26}{'İxtisas':<17}{'Slot':>6}{'Dolu':>6}{'Doluluq':>10}{'Ləğv':>6}")
    print("-" * 71)

    totals = {"total": 0, "booked": 0}
    for r in rows:
        total, booked = r["total_slots"], r["booked_slots"]
        percent = (booked / total * 100) if total else 0
        totals["total"] += total
        totals["booked"] += booked
        print(f"{r['full_name']:<26}{r['specialty']:<17}{total:>6}{booked:>6}"
              f"{percent:>9.1f}%{r['cancelled']:>6}")

    print("-" * 71)
    overall = (totals["booked"] / totals["total"] * 100) if totals["total"] else 0
    print(f"{'CƏMİ':<43}{totals['total']:>6}{totals['booked']:>6}{overall:>9.1f}%\n")


if __name__ == "__main__":
    main()
