# Sahifa Quiz V35 — Premium AI Quiz

**Sahifa Quiz** — kitoblar bo‘yicha Telegram quiz platformasi. V35 eski V34 funksiyalarini saqlaydi, mavjud data oqimlarini mustahkamlaydi va faqat bitta yangi katta imkoniyat qo‘shadi: **🤖 AI-generated quiz**.

## Asosiy funksiyalar

### 👤 Foydalanuvchi
- 📚 Kitoblar katalogi va qidiruv
- 📖 Kitob tafsilotlari va savollar soni
- 🧠 Kitob bo‘yicha test
- 🎲 Tasodifiy test
- 🔥 Bugungi savol
- ❌ Xato savollarni qayta ishlash
- 🤖 AI-generated quiz
- 🏆 TOP reyting
- 👤 Profil va statistika
- 🔥 Streak
- ℹ️ Yordam va admin bilan aloqa
- 📢 Majburiy kanal obunasi

### 🛠 Admin
- 📚 Kitob CRUD va soft-delete
- ❓ Savol CRUD
- 📥 TXT import
- 👥 User qidiruvi va statistika
- 🚫 Block/unblock
- 🧹 User statistikasi + quiz tarixini izchil tozalash
- 📣 Broadcast
- 📢 Majburiy kanallar
- ❤️ Kanal reaction sozlamalari
- 🏆 TOP sozlamalari va reset
- ⚙️ Ball sozlamasi
- 🔥 Daily savolni tanlash
- 👑 Admin rollari

## 🤖 AI-generated quiz qanday ishlaydi

1. User kitobni tanlaydi.
2. 5/10/15 ta savoldan birini tanlaydi.
3. Bot Redis lock va qisqa cooldown bilan bir userning parallel AI so‘rovlarini cheklaydi.
4. AI OpenAI-compatible API orqali JSON formatida savollar yaratadi.
5. Javob JSON schema sifatida qayta tekshiriladi: A/B/C/D, bitta to‘g‘ri javob, duplicate savollar va bo‘sh variantlar rad qilinadi.
6. Mavjud normal savollar ichidan bir nechta namuna AIga faqat mavzu/qiyinlikni anglash uchun beriladi; ularni ko‘chirish taqiqlanadi.
7. AI savollari `source=ai` bilan alohida belgilanadi va oddiy katalog savollariga qo‘shilmaydi.
8. Shunga qaramay, ular odatdagi `QuizAttempt` va `QuizAnswer` oqimida ishlaydi, shuning uchun ball/statistika bir xil hisoblanadi.

## AI provider

Default provider: **OpenRouter** (`https://openrouter.ai/api/v1`). Model `.env` orqali almashtirilishi mumkin. Default qiymat `openai/gpt-4.1-nano`.

Kerakli env: 

```env
AI_API_KEY=...
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openai/gpt-4.1-nano
AI_QUIZ_DEFAULT_QUESTIONS=10
AI_QUIZ_MAX_QUESTIONS=15
AI_TIMEOUT_SECONDS=60
```

AI provider 429/5xx kabi vaqtinchalik xatolarda bitta qisqa retry qiladi. AI ishlamasa, foydalanuvchiga tushunarli xabar qaytariladi va odatiy quiz tizimi ishlashda davom etadi.

Streak kuni `APP_TIMEZONE` bo‘yicha hisoblanadi; default — `Asia/Tashkent`.

## Premium UI

- ✨ Kitob katalogi 3 xil visual formatni navbatlab ko‘rsatadi.
- 🔢 Kitoblar raqamlangan va normal savollar soni ko‘rsatiladi.
- 🪄 Kitob detail va AI quiz oqimlarida boy HTML bloklari ishlatiladi.
- 🎯 Quiz progress va natija matnlari markazlashtirilgan UI helperlar orqali boshqariladi.
- 🧹 Dynamic foydalanuvchi va kitob qiymatlari HTML-safe escape qilinadi.

## Render + PostgreSQL + Redis/Key Value

Render Blueprint quyidagi arxitekturadan foydalanadi:

```text
Telegram
   │
   ▼
FastAPI + aiogram webhook
   │
   ├── PostgreSQL / SQLAlchemy async
   └── Redis/Valkey / FSM + locks + cache
```

`render.yaml`da hozirgi Render konfiguratsiyasi uchun `type: keyvalue`, ichki `ipAllowList: []`, Web Service health check `/health` va PostgreSQL ichki ulanishi qo‘yilgan. UptimeRobot uchun:

```text
https://YOUR-SERVICE.onrender.com/live
```

`/health` PostgreSQL va Redis/Valkey holatini tekshiradi; `/live` esa monitoring uchun engil endpoint.

> Render Free Web Service uzoq inactivitydan keyin spin down qilishi mumkin. Uptime monitor uyg‘otishga yordam beradi, lekin platformaning bepul rejasidagi barcha cheklovlarni olib tashlamaydi.

## Deploy

```bash
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render `startCommand` migratsiyani va Uvicorn serverni avtomatik ishga tushiradi.

## TXT import

```text
1. Savol matni?
A: Variant A
B: Variant B
C: Variant C
D: Variant D
ANSWER: B

2. Ikkinchi savol?
A: Variant A
B: Variant B
C: Variant C
D: Variant D
ANSWER: 1
```

Maximum import: **100 savol**.

## Channel reaction

1. `TARGET_CHANNEL_ID` ni kiriting.
2. Botni kanalga administrator qiling.
3. Admin paneldan reactionni yoqing.
4. Yangi post yuborib tekshiring.
5. Zaruratda **🧪 TEST REACTION** tugmasidan foydalaning.

## Muhim xavfsizlik va consistency tuzatishlari

V35 quyidagilarni mustahkamlaydi:

- tugagan attemptni keyin abandonedga aylantirishning oldi olindi;
- answer/stop uchun bir attempt lock ishlatiladi;
- `/start` FSMni tozalaydi;
- menu orqali quizdan chiqish active attemptni yopadi;
- kitob o‘chirish soft-delete bo‘lib, tarixiy quiz yozuvlari saqlanadi;
- user statistikasi tozalanganda uning `QuizAttempt/QuizAnswer` tarixi ham izchil tozalanadi;
- inactive kitob callbacklari rad qilinadi;
- user yaratish concurrency race holatiga moslashtirildi;
- webhook update dedup oldindan tekshiriladi va faqat muvaffaqiyatli processingdan keyin marker yoziladi;
- webhook processing xatosida 500 qaytariladi;
- reaction va settings inputlarida validation kuchaytirildi.

## Verification

Build ichida bajarilgan offline tekshiruvlar:

```text
compileall: PASS
pytest: PASS
render.yaml: PASS
secret scan: PASS
```

Bu paket real Telegram tokeni, Render PostgreSQL va Redis/Valkey bilan production smoke-test o‘tkazilganini da’vo qilmaydi. Build konteynerida `aiogram` runtime dependency o‘rnatilmagan edi; shu sababli live Telegram import/smoke-test bajarilmadi. Dependency esa `requirements.txt` va Render deploy uchun to‘liq kiritilgan.
