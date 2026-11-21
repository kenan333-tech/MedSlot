-- W2 · AI-yə veriləcək ixtisas siyahısı
SELECT string_agg(DISTINCT specialty, ', ' ORDER BY specialty) AS specialties
  FROM doctors;
