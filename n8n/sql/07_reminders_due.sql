-- W3 · 2 saat ərzində başlayacaq, hələ xatırlatma getməmiş növbələr
-- Bu sorğu hər sətir üçün AYRI item qaytarır (Telegram hər biri üçün işləyir)
SELECT a.id,
       p.full_name,
       p.chat_id,
       d.full_name AS doctor,
       d.specialty,
       to_char(s.start_at, 'HH24:MI')    AS time,
       to_char(s.start_at, 'DD.MM.YYYY') AS date
  FROM appointments a
  JOIN slots    s ON s.id = a.slot_id
  JOIN patients p ON p.id = a.patient_id
  JOIN doctors  d ON d.id = s.doctor_id
 WHERE a.status   = 'booked'
   AND a.reminded = false
   AND s.start_at BETWEEN now() AND now() + interval '2 hours';
