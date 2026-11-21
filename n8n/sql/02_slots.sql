-- W1 · GET /medslot/slots?doctor_id=&date=
-- $1 = doctor_id, $2 = date (YYYY-MM-DD)
-- Query Parameters: {{ [ $json.query.doctor_id, $json.query.date ] }}
SELECT COALESCE(
         json_agg(json_build_object(
           'id',   s.id,
           'date', to_char(s.start_at, 'YYYY-MM-DD'),
           'time', to_char(s.start_at, 'HH24:MI')
         ) ORDER BY s.start_at),
         '[]'::json) AS slots
  FROM slots s
 WHERE s.doctor_id     = $1::int
   AND s.start_at::date = $2::date
   AND s.status        = 'free'
   AND s.start_at      > now();
