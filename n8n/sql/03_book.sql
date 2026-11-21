-- W1 · POST /medslot/book   body: {slot_id, full_name, phone, complaint}
-- $1 = slot_id, $2 = full_name, $3 = phone, $4 = complaint
-- Query Parameters: {{ [ $json.body.slot_id, $json.body.full_name, $json.body.phone, $json.body.complaint || '' ] }}
--
-- Əsas fikir: slotu YALNIZ status = 'free' olduqda tuturuq (atomik UPDATE).
-- İki nəfər eyni anda bassa, ikincisinin UPDATE-i 0 sətir dəyişir → yazılış yaranmır.
WITH s AS (
    UPDATE slots
       SET status = 'booked'
     WHERE id = $1::int
       AND status = 'free'
       AND start_at > now()
 RETURNING id, doctor_id, start_at
), p AS (
    INSERT INTO patients (full_name, phone)
    SELECT $2, $3
     WHERE EXISTS (SELECT 1 FROM s)
    ON CONFLICT (phone) DO UPDATE SET full_name = EXCLUDED.full_name
 RETURNING id
), a AS (
    INSERT INTO appointments (slot_id, patient_id, complaint, status, reminded)
    SELECT s.id, p.id, $4, 'booked', false
      FROM s, p
 RETURNING id, slot_id
)
SELECT (
    SELECT json_build_object(
             'appointment_id', a.id,
             'doctor',    d.full_name,
             'specialty', d.specialty,
             'start_at',  to_char(s.start_at, 'DD.MM.YYYY HH24:MI'))
      FROM a
      JOIN s ON s.id = a.slot_id
      JOIN doctors d ON d.id = s.doctor_id
) AS appointment;
-- appointment = null → saat artıq tutulub və ya keçib → 409 qaytar
