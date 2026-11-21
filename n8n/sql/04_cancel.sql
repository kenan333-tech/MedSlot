-- W1 · POST /medslot/cancel   body: {appointment_id}
-- $1 = appointment_id
-- Query Parameters: {{ [ $json.body.appointment_id ] }}
WITH a AS (
    UPDATE appointments
       SET status = 'cancelled'
     WHERE id = $1::int
       AND status = 'booked'
 RETURNING slot_id
), s AS (
    UPDATE slots
       SET status = 'free'
     WHERE id IN (SELECT slot_id FROM a)
 RETURNING id, start_at
)
SELECT (
    SELECT json_build_object(
             'slot_id', s.id,
             'start_at', to_char(s.start_at, 'DD.MM.YYYY HH24:MI'))
      FROM s
) AS freed;
-- freed = null → belə aktiv yazılış yoxdur → 404 qaytar
