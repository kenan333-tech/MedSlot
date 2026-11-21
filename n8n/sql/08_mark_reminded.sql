-- W3 · Telegram göndərildikdən sonra təkrar getməsin
-- $1 = appointment id
-- Query Parameters: {{ [ $('Növbələri tap').item.json.id ] }}
UPDATE appointments
   SET reminded = true
 WHERE id = $1::int
RETURNING id;
