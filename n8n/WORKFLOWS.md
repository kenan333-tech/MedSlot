# n8n workflow-ları

Bu sənəd hər workflow-un hansı node-lardan ibarət olduğunu və necə işlədiyini izah edir.
Hazır workflow-lar bu qovluqdadır, onları **⋯ → Import from File** ilə import etmək kifayətdir.
Aşağıdakı addımlar workflow-u sıfırdan qurmaq və ya dəyişmək istəyənlər üçündür.

| Fayl | Workflow | Trigger |
|---|---|---|
| `W1_novbe_api.json` | Növbə API | Webhook (4 endpoint) |
| `W2_ai_yonlendirme.json` | AI yönləndirmə | Webhook `POST /medslot/triage` |
| `W3_xatirlatma.json` | Xatırlatma | Schedule, hər 15 dəq |

Workflow-lardakı SQL sorğuları ayrıca `n8n/sql/` qovluğunda saxlanılır.

---

## 0. Credential-lar (bir dəfə)

n8n → sol menyu **Credentials → Add credential**:

**a) Postgres** — ad: `MedSlot DB`
- Host: `postgres` ← `localhost` YOX! (n8n konteynerin içindədir)
- Database: `layihe` · User: `app` · Password: `app123` · Port: `5432`
- **Test** → yaşıl olmalıdır.

**b) Groq** — tip: **Header Auth**, ad: `Groq API`
- Name: `Authorization`
- Value: `Bearer gsk_...` (söz `Bearer`, boşluq, sonra açar)

**c) Telegram** — tip: **Telegram API**, ad: `MedSlot Bot`
- Access Token: BotFather-dən aldığın token.

---

## Ümumi qaydalar (hər Webhook node üçün)

- **HTTP Method**: GET və ya POST (cədvəldə yazıldığı kimi)
- **Path**: məs. `medslot/slots` (əvvəlində `/` qoyma)
- **Respond**: `Using 'Respond to Webhook' Node`
- **Options → Allowed Origins (CORS)**: `*`
- Query parametrləri: `{{ $json.query.doctor_id }}` · Body: `{{ $json.body.slot_id }}`

**Postgres node**: Operation = **Execute Query**, sorğunu yapışdır,
**Options → Query Parameters** sahəsinə massiv ifadəsi yaz: `{{ [ ..., ... ] }}`.
Massiv forması vergüllü mətnləri (məs. "Bakı, Nəsimi") pozmur.

**Respond to Webhook node**: Respond With = **JSON**, Response Body = ifadə,
xəta cavabları üçün **Options → Response Code** (400 / 404 / 409).

---

## W1 · Növbə API

Bir workflow-da 4 ayrı Webhook node olacaq. Hər biri öz zənciri ilə.

### 1) GET /medslot/doctors
```
[Webhook GET medslot/doctors] → [Postgres: 01_doctors.sql] → [Respond: 200]
```
Respond body: `{{ { doctors: $json.doctors } }}`

### 2) GET /medslot/slots?doctor_id=&date=
```
[Webhook GET medslot/slots] → [IF: parametrlər düzdür?]
     ├─ true  → [Postgres: 02_slots.sql] → [Respond 200]
     └─ false → [Respond 400]
```
- IF şərti (Boolean → is true):
  `{{ /^\d+$/.test($json.query.doctor_id || '') && /^\d{4}-\d{2}-\d{2}$/.test($json.query.date || '') }}`
- Postgres Query Parameters: `{{ [ $json.query.doctor_id, $json.query.date ] }}`
- Respond 200: `{{ { slots: $json.slots } }}`
- Respond 400: `{{ { error: "doctor_id və date (YYYY-MM-DD) lazımdır" } }}`

### 3) POST /medslot/book
```
[Webhook POST medslot/book] → [IF: body düzdür?]
     ├─ true  → [Postgres: 03_book.sql] → [IF: appointment boş deyil?]
     │                                      ├─ true  → [Respond 200]
     │                                      └─ false → [Respond 409]
     └─ false → [Respond 400]
```
- IF #1 (Boolean → is true):
  `{{ Number.isInteger(Number($json.body.slot_id)) && ($json.body.full_name || '').trim().length >= 3 && /^\+?[0-9 ]{9,15}$/.test($json.body.phone || '') }}`
- Postgres Query Parameters:
  `{{ [ $json.body.slot_id, $json.body.full_name.trim(), $json.body.phone.replace(/\s/g, ''), $json.body.complaint || '' ] }}`
- IF #2 (Boolean → is true): `{{ !!$json.appointment }}`
- Respond 200: `{{ { appointment: $json.appointment } }}`
- Respond 409: `{{ { error: "Bu saat artıq tutulub. Başqa saat seçin." } }}`
- Respond 400: `{{ { error: "Ad (min. 3 hərf), telefon və slot_id düzgün olmalıdır" } }}`

> **Niyə iki yazılış mümkün deyil?** `03_book.sql`-də slot yalnız `status = 'free'` olduqda
> `booked` edilir. Bu, bir SQL əmrində baş verir — ikinci sorğu 0 sətir dəyişir. Üstəlik
> `models.py`-dakı unikal indeks bazanın özündə ikinci aktiv yazılışı qadağan edir.

**Əlavə: təsdiq mesajı.** `Cavab book` node-undan sonra `Təsdiq mesajı` (Telegram) gəlir.
Cavab əvvəlcə frontend-ə gedir, mesaj ondan sonra göndərilir, ona görə pasiyent gözləmir.
Telegram xəta versə belə (`On Error → Continue`), növbə yenə də qeydə alınır.

### 4) POST /medslot/cancel
```
[Webhook POST medslot/cancel] → [Postgres: 04_cancel.sql] → [IF: freed boş deyil?]
                                                              ├─ true  → [Respond 200]
                                                              └─ false → [Respond 404]
```
- Postgres Query Parameters: `{{ [ $json.body.appointment_id ] }}`
- IF (Boolean → is true): `{{ !!$json.freed }}`
- Respond 200: `{{ { ok: true, freed: $json.freed } }}`
- Respond 404: `{{ { error: "Aktiv növbə tapılmadı (artıq ləğv olunub?)" } }}`

**Əlavə:** `Cavab cancel`-dən sonra `Ləğv mesajı` (Telegram) gəlir.

---

## W2 · AI yönləndirmə (Groq)

```
[Webhook POST medslot/triage]
   → [IF: şikayət ≥ 5 simvol?]
        ├─ false → [Respond 400]
        └─ true  → [Postgres "İxtisaslar": 05_specialties.sql]
                     → [HTTP Request "Groq"]
                     → [Code "AI cavabını yoxla"]
                     → [Postgres: 06_doctors_by_specialty.sql]
                     → [Respond 200]
```

**IF**: `{{ ($json.body.complaint || '').trim().length >= 5 }}`
Respond 400: `{{ { error: "Şikayətinizi bir az ətraflı yazın" } }}`

**HTTP Request "Groq"**
- Method: `POST`
- URL: `https://api.groq.com/openai/v1/chat/completions`
- Authentication: **Generic Credential Type → Header Auth → Groq API**
- Send Body: ✓ · Body Content Type: **JSON** · Specify Body: **Using JSON**
- JSON (ifadə rejimində, `=` ilə başlayır):

```
{{ {
  model: "openai/gpt-oss-120b",
  temperature: 0.2,
  response_format: { type: "json_object" },
  messages: [
    {
      role: "system",
      content: "Sən klinikada qeydiyyat köməkçisisən. Pasiyentin şikayətinə görə YALNIZ bu siyahıdan BİR ixtisas seç: " + $json.specialties + ". Diaqnoz qoyma, dərman adı çəkmə. Əgər şikayətdə təcili hal əlaməti varsa (sinə ağrısı ilə təngnəfəslik, huşun itməsi, üz və ya qolda qəfil keyimə, güclü qanaxma), urgent = true yaz. Yalnız JSON qaytar, başqa heç nə yazma. Nümunə: {\"specialty\": \"Nevroloq\", \"reason\": \"Tez-tez təkrarlanan baş ağrısı nevroloji müayinə tələb edir.\", \"urgent\": false}. reason Azərbaycan dilində, 1 qısa cümlə olsun."
    },
    {
      role: "user",
      content: $('Webhook').item.json.body.complaint
    }
  ]
} }}
```
> Webhook node-unun adı fərqlidirsə, `$('Webhook')` hissəsini öz adına dəyiş.

- **Options → Add option → Response → Response Format: `JSON`**. Bunu etməsən, n8n kodlaşdırmanı səhv təxmin edir və ə, ı, ü hərfləri Çin simvollarına çevrilir.
- **Settings** sekmesi: `Retry On Fail` ✓ (2 dəfə, 2000 ms) və
  `On Error` → **Continue** — Groq xəta versə də workflow dayanmasın, Code node fallback edəcək.

**Code "AI cavabını yoxla"** (Mode: Run Once for All Items) — bu, ayın JS Expressions mövzusudur:

```js
// AI-nin cavabı JSON olmaya və ya siyahıda olmayan ixtisas seçə bilər.
// Belə olanda Terapevt-ə yönləndiririk (ümumi həkim).
const allowed = $('İxtisaslar').first().json.specialties.split(', ');

let ai = {};
try {
  ai = JSON.parse($input.first().json.choices[0].message.content);
} catch (e) {
  ai = {};
}

const ok = allowed.includes(ai.specialty);

return [{
  json: {
    specialty: ok ? ai.specialty : 'Terapevt',
    reason: ok && ai.reason ? ai.reason : 'Əvvəlcə terapevt müayinəsi tövsiyə olunur.',
    urgent: ai.urgent === true,
    ai_ok: ok,
  },
}];
```

**Postgres**: `06_doctors_by_specialty.sql`, Query Parameters: `{{ [ $json.specialty ] }}`

**Respond 200**:
```
{{ {
  specialty: $('AI cavabını yoxla').item.json.specialty,
  reason:    $('AI cavabını yoxla').item.json.reason,
  urgent:    $('AI cavabını yoxla').item.json.urgent,
  doctors:   $json.doctors
} }}
```

> **Model xətası olsa:** Groq konsolunda (`console.groq.com/docs/models`) aktiv modellərə bax.
> `openai/gpt-oss-120b` işləməsə, `llama-3.3-70b-versatile` yaz — qalan hər şey eynidir.

---

## W3 · Xatırlatma

```
[Schedule: hər 15 dəqiqə] → [Postgres "Növbələri tap": 07_reminders_due.sql]
     → [Telegram: Send Message] → [Postgres: 08_mark_reminded.sql]
```

- **Postgres "Növbələri tap"**: Settings-də `Always Output Data` **SÖNÜLÜ** qalsın —
  növbə yoxdursa, workflow sakitcə dayanır.
- **Telegram node** → Resource: Message · Operation: **Send Message**
  - Chat ID: `{{ $json.chat_id || 'SƏNİN_CHAT_ID' }}` (demo-da bütün mesajlar sənə gəlir)
  - Text:
    ```
    🔔 MedSlot xatırlatma

    Hörmətli {{ $json.full_name }}, bu gün saat {{ $json.time }}-da
    {{ $json.doctor }} ({{ $json.specialty }}) qəbulunuz var.

    Növbə nömrəsi: #{{ $json.id }}
    Gələ bilməyəcəksinizsə, növbəni ləğv edin ki, saat başqasına qalsın.
    ```
  - Additional Fields → `Append n8n Attribution` söndür.
- **Postgres**: `08_mark_reminded.sql`, Query Parameters:
  `{{ [ $('Növbələri tap').item.json.id ] }}`

> Telegram node hər item üçün ayrı işləyir: 3 növbə varsa, 3 mesaj gedir və hər biri
> `reminded = true` olur. Növbəti 15 dəqiqədə həmin növbələr seçilmir → **bir dəfə** qaydası.

---

## Yoxlama

- Test rejimində `/webhook-test/...` ünvanı ilə Postman-dan sorğu göndər: düzgün JSON qayıtmalıdır.
- Səhv sorğu (boş body) 400 qaytarmalıdır.
- Workflow aktiv olanda `/webhook/...` (test-siz) ünvanı işləməlidir.
