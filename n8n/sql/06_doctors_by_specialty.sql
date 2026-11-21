-- W2 · AI-nin seçdiyi ixtisasın həkimləri
-- $1 = specialty
-- Query Parameters: {{ [ $json.specialty ] }}
SELECT COALESCE(
         json_agg(json_build_object(
           'id', id,
           'full_name', full_name,
           'specialty', specialty,
           'work_start', to_char(work_start, 'HH24:MI'),
           'work_end',   to_char(work_end,   'HH24:MI')
         )),
         '[]'::json) AS doctors
  FROM doctors
 WHERE specialty = $1;
