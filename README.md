# MedSlot — klinika üçün onlayn növbə sistemi

> Pasiyent şikayətini yazır → **Groq AI** uyğun ixtisası təklif edir → boş saat seçilir →
> eyni saata ikinci yazılış **mümkün deyil** → qəbuldan 2 saat əvvəl **Telegram** xatırlatması gəlir.

**Problem:** Klinikada növbələr telefonla yazılır. Eyni saata iki pasiyent düşür, bəziləri növbəni unudur və gəlmir.

**Alətlər (1-ci ay):** Docker · n8n (Webhook, Postgres, HTTP Request, IF, Code, Schedule, Telegram) ·
PostgreSQL · Python (SQLAlchemy, psycopg2, requests) · Groq API · Postman · HTML + Tailwind (AI ilə)

---

## Arxitektura

```
 Frontend (index.html)
     │  HTTP / JSON
     ▼
 n8n ──────────────► Groq API  (şikayət → ixtisas JSON)
  W1 Növbə API         
  W2 AI yönləndirmə    
  W3 Xatırlatma ─────► Telegram (pasiyent = sən)
     │  SQL
     ▼
 PostgreSQL (4 cədvəl) ◄──── Python: models.py, seed.py,
                                     slot_generator.py (SQLAlchemy),
                                     report.py (psycopg2)
```
n8n və Python bir-birini birbaşa çağırmır: Python slotları **bazaya yazır**, n8n onları **bazadan oxuyur**.

## Verilənlər bazası

| Cədvəl | Sütunlar | Qeyd |
|---|---|---|
| `doctors` | id · full_name · specialty · work_start · work_end | seed.py doldurur |
| `slots` | id · doctor_id · start_at · status | `free` / `booked`, (doctor_id, start_at) unikal |
| `patients` | id · full_name · phone · chat_id | phone unikal |
| `appointments` | id · slot_id · patient_id · complaint · status · reminded | `booked` / `cancelled`; bir slota 1 aktiv yazılış |

## API (n8n webhook-ları)

Baza ünvan: `http://localhost:5678/webhook/medslot`

| Metod | Yol | Body / parametrlər | Cavab |
|---|---|---|---|
| GET | `/doctors` | — | `{doctors: [...]}` |
| GET | `/slots` | `?doctor_id=1&date=2026-11-23` | `{slots: [{id, date, time}]}` · 400 |
| POST | `/triage` | `{complaint}` | `{specialty, reason, urgent, doctors}` · 400 |
| POST | `/book` | `{slot_id, full_name, phone, complaint}` | `{appointment}` · 400 · **409** |
| POST | `/cancel` | `{appointment_id}` | `{ok, freed}` · 404 |

## Qovluq

```
medslot/
├─ docker-compose.yml        n8n + PostgreSQL
├─ .env.example              açarların nümunəsi
├─ python/
│  ├─ db.py                  bağlantı
│  ├─ models.py              4 cədvəl (SQLAlchemy)
│  ├─ seed.py                cədvəllər + 6 həkim
│  ├─ slot_generator.py      7 günlük 30 dəq. slotlar (SQLAlchemy, while + sleep)
│  ├─ report.py              doluluq faizi (psycopg2)
│  └─ demo_double_book.py    "iki yazılış olmur" demosu
├─ n8n/
│  ├─ WORKFLOWS.md           node-node qurulma bələdçisi
│  ├─ sql/                   hazır SQL sorğuları
│  └─ W1/W2/W3 *.json        ← sən export edəcəksən
├─ postman/MedSlot.postman_collection.json
├─ frontend/index.html
└─ docs/screenshots/         ← ekran şəkilləri
```

---

# Addım-addım: sıfırdan təhvilə qədər

Hər addımın sonunda **✅ Yoxla** var. Yoxlama keçmədən növbəti addıma keçmə.

## Addım 0 · Hazırlıq (≈30 dəq)

1. Quraşdırılmalıdır: **Docker Desktop**, **Python 3.11+**, **Postman**, (istəyə görə) **DataGrip**.
2. **Groq açarı:** `console.groq.com` → qeydiyyat → **API Keys → Create** → `gsk_...` açarını saxla.
3. **Telegram bot:** Telegram-da `@BotFather` → `/newbot` → ad ver → **token** al.
4. Yeni bota özün `/start` yaz. Sonra brauzerdə aç:
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → `"chat":{"id": 123456789}` — bu sənin **chat_id**-ndir.
5. `.env.example` faylını `.env` adı ilə kopyala, dəyərləri yaz.

✅ **Yoxla:** Groq açarı, bot token və chat_id əlindədir.

## Addım 1 · Docker: n8n + PostgreSQL (≈20 dəq) · *Dərs 6*

```bash
cd medslot
docker compose up -d
docker compose ps        # hər ikisi "running" olmalıdır
```
`http://localhost:5678` aç → n8n hesabı yarat (lokaldır).

✅ **Yoxla:** DataGrip-də qoşul: host `localhost`, port `5432`, db `layihe`, user `app`, şifrə `app123`.

## Addım 2 · Python mühiti və cədvəllər (≈30 dəq) · *Dərs 1–5, 8*

```bash
cd python
python -m venv .venv
# Windows: .venv\Scripts\activate     Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python seed.py
```

✅ **Yoxla:** DataGrip-də 4 cədvəl var, `SELECT * FROM doctors;` → 6 həkim.

## Addım 3 · Slot generatoru (≈20 dəq)

```bash
python slot_generator.py --once
python slot_generator.py --once     # ikinci dəfə: "0 yeni slot" — təkrar yaratmır!
```

✅ **Yoxla:**
```sql
SELECT doctor_id, start_at::date, COUNT(*) FROM slots GROUP BY 1,2 ORDER BY 1,2;
```
Hər həkim üçün 6 iş günü görünür, bazar günü yoxdur.

> 💡 Kodu oxu və başa düş: `set` niyə istifadə olunub? (Cavab: mövcud saatları sürətli yoxlamaq üçün.)
> Təqdimatda bunu soruşa bilərlər.

## Addım 4 · n8n credential-ları (≈15 dəq) · *Dərs 7–8*

`n8n/WORKFLOWS.md` → **0. Credential-lar** bölməsi: Postgres (`host = postgres`!), Groq (Header Auth), Telegram.

✅ **Yoxla:** Postgres credential-ında **Test** yaşıldır.

## Addım 5 · W1 Növbə API (≈2–3 saat) · *Dərs 7, 8*

`WORKFLOWS.md` → **W1**. Sıra ilə qur: `doctors` → `slots` → `book` → `cancel`.
Hər endpoint-dən sonra Postman-da yoxla.

**Postman:** `Import` → `postman/MedSlot.postman_collection.json`.
Test zamanı kolleksiyanın `base_url` dəyişənini `http://localhost:5678/webhook-test` et.

✅ **Yoxla:**
- `GET slots` → saatlar siyahısı
- `POST book` → 200, `POST book` eyni slot_id ilə → **409**
- `POST cancel` → 200, təkrar → **404**
- Səhv body → **400**

## Addım 6 · W2 AI yönləndirmə — Groq (≈2 saat) · *Dərs 5, 7*

`WORKFLOWS.md` → **W2**. Ən vacib 3 şey:
1. URL: `https://api.groq.com/openai/v1/chat/completions`
2. Model: `openai/gpt-oss-120b`, `response_format: {type: "json_object"}`
3. Code node: AI səhv cavab versə → **Terapevt** (fallback).

✅ **Yoxla (Postman):**
- "başım tez-tez ağrıyır" → `Nevroloq`
- "qollarımda səpgi var" → `Dermatoloq`
- "sinəmdə ağrı, nəfəs ala bilmirəm" → `urgent: true`

## Addım 7 · W3 Telegram xatırlatma (≈1 saat) · *Dərs 7, 8*

`WORKFLOWS.md` → **W3**.

✅ **Yoxla:**
1. DataGrip-də test slotu yarat (1 saat sonraya):
   ```sql
   INSERT INTO slots (doctor_id, start_at, status) VALUES (1, now() + interval '1 hour', 'free') RETURNING id;
   ```
2. Postman ilə həmin `slot_id`-yə `POST book`.
3. W3-də **Execute Workflow** → Telegram-a mesaj gəlir.
4. Yenə **Execute** → mesaj **gəlmir** (reminded = true). ✔ "bir dəfə" qaydası.

## Addım 8 · Workflow-ları aktiv et (≈10 dəq)

Hər 3 workflow-da sağ yuxarıda **Active** ✓. İndi `/webhook/...` (test-siz) ünvanı işləyir.
Postman-da `base_url`-i yenidən `http://localhost:5678/webhook` et və bütün kolleksiyanı işlət (**Run collection**).

## Addım 9 · Frontend (≈1 saat)

`frontend/index.html` hazırdır (AI ilə yaradılıb, layihə qaydasına uyğun). Lokal serverlə aç:
```bash
cd frontend
python -m http.server 5500
```
Brauzer: `http://localhost:5500`

> Workflow aktiv deyilsə, yuxarıdakı **"n8n test rejimi"** qutusunu işarələ.
> Dizaynı dəyişmək istəsən, `n8n/WORKFLOWS.md`-dəki API-ni AI-yə ver və dəyişiklik istə.

✅ **Yoxla:** şikayət → AI kartı → həkim → tarix → saat → ad/telefon → təsdiq → ləğv. Hamısı işləyir.

## Addım 10 · Hesabat və iki yazılış demosu (≈20 dəq) · *Dərs 9 (psycopg2)*

```bash
cd python
python report.py              # həkimlər üzrə doluluq faizi
python demo_double_book.py    # 1-ci: 200, 2-ci: 409
```

## Addım 11 · Export və sənədləşmə (≈1 saat)

- [ ] n8n: hər workflow → `⋯ → Download` → `n8n/W1_novbe_api.json`, `W2_ai_yonlendirme.json`, `W3_xatirlatma.json`
- [ ] **JSON-larda açar olmadığını yoxla** (credential-lar export-a daxil olmur, amma kodda əl ilə yazılmış token qalmasın)
- [ ] `docs/screenshots/`: frontend 4 addım, n8n-in 3 workflow-u, Telegram mesajı, DataGrip-də cədvəllər, `report.py` nəticəsi
- [ ] Bu README-də ekran şəkillərinə link əlavə et
- [ ] `.env` faylı repoda **YOXDUR**, `.env.example` **VAR**
- [ ] (İstəyə görə) 2 dəqiqəlik ekran videosu

## Addım 12 · Təqdimat, 5–7 dəqiqə

| Vaxt | Nə göstərirsən |
|---|---|
| 0:00–0:45 | **Problem:** telefonla növbə, eyni saata iki pasiyent, unudulan növbələr |
| 0:45–2:00 | **Demo 1 — AI:** "başım tez-tez ağrıyır" → AI nevroloqu təklif edir ✨ |
| 2:00–3:00 | **Demo 2 — WOW:** iki brauzer pəncərəsində eyni saatı tut → ikincisi "artıq tutulub" alır |
| 3:00–3:30 | **Demo 3:** ləğv et → saat yenidən boş görünür |
| 3:30–4:15 | **Demo 4:** W3-ü işə sal → telefonunda Telegram xatırlatması |
| 4:15–5:30 | **Kapotun altı:** n8n workflow-ları → DataGrip-də cədvəllər → `slot_generator.py` → `report.py` |
| 5:30–6:00 | Öyrəndiklərin + növbəti addım (bonus) |

> Təqdimatdan **bir gün əvvəl** slot_generator.py-ni yenidən işə sal ki, slotlar təzə olsun.

---

## Minimum tələblər (PDF-ə uyğun)

- [x] 4 cədvəl SQLAlchemy ilə, seed.py həkimləri doldurur
- [x] slot_generator.py 7 günlük boş saatları yaradır
- [x] Eyni saata iki yazılış mümkün deyil (atomik UPDATE + unikal indeks)
- [x] AI şikayətə görə ixtisas təklif edir (Groq)
- [x] Növbədən 2 saat əvvəl Telegram xatırlatması bir dəfə gedir
- [x] 3 n8n workflow (2 Webhook, 1 Schedule) · 2 Python skripti (SQLAlchemy + psycopg2)
- [x] Bütün endpoint-lər Postman kolleksiyasında

## Bonus (vaxt qalsa)

- **Gözləmə siyahısı:** `waitlist` cədvəli; ləğv olunan saat ilk gözləyənə Telegram ilə təklif olunur.
- **Admin səhifəsi:** günün cədvəli + doluluq faizi (`GET /medslot/admin/today`).
- **Gəlməyənlər:** `appointments.status`-a `no_show` əlavə et, report.py-də statistika.

## Tez-tez rast gəlinən xətalar

| Xəta | Həll |
|---|---|
| Brauzerdə CORS xətası | Webhook node → Options → Allowed Origins = `*`; frontend-i `http.server` ilə aç |
| Webhook 404 | Workflow aktiv deyil → `webhook-test` istifadə et və n8n-də "Listen for test event" bas |
| n8n Postgres-ə qoşulmur | Host `postgres` olmalıdır, `localhost` yox |
| Groq 401 | Header dəyəri `Bearer gsk_...` olmalıdır (Bearer + boşluq) |
| Groq 429 | Dəqiqəlik limit dolub → 1 dəq gözlə; Retry On Fail aktivdir |
| Groq "model not found" | `console.groq.com/docs/models`-a bax, `llama-3.3-70b-versatile` yaz |
| AI JSON yox, mətn qaytarır | `response_format: json_object` və prompt-da nümunə JSON olsun |
| Saatlar 4 saat fərqli görünür | `python seed.py`-ni yenidən işə sal (bazanın timezone-u Asia/Baku olur) |
| Telegram mesajı getmir | Əvvəlcə bota özün yaz; chat_id-ni yoxla |
| Windows: `ZoneInfoNotFoundError` | `pip install tzdata` |
