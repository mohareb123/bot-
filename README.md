# 🤖 AI Telegram Bot

بوت تيليجرام متكامل يعمل بالذكاء الاصطناعي مع لوحة تحكم قوية وتجربة استخدام نظيفة.

## ✨ الميزات

### 🧠 الذكاء الاصطناعي
- **شات ذكي** - محادثة طبيعية مع حفظ السياق
- **تحليل الصور** - وصف وتحليل أي صورة بالذكاء الاصطناعي
- **إنشاء صور** - إنشاء صور من النص باستخدام AI
- **تعديل صور** - تعديل الصور بتعليمات نصية
- **نظام Fallback** - تبديل تلقائي بين مقدمي الخدمة (Gemini → OpenAI → Free)

### 📥 تحميل الوسائط
- تحميل فيديو من: فيسبوك، تيك توك، إنستغرام، يوتيوب، تويتر
- تحويل الفيديو إلى MP3
- دعم الروابط المباشرة
- دعم ربط حساب جوجل للفيديوهات المقيدة

### 🔊 نظام الصوت
- **تحويل النص لصوت (TTS)** - دعم 11+ صوت بعدة لغات
- **تحويل الصوت لنص (STT)** - دعم العربية والإنجليزية
- اختيار الصوت المفضل

### 🎛️ لوحة التحكم
- إدارة المجموعات (تفعيل/تعطيل ميزات)
- إدارة القنوات (الاشتراك الإجباري)
- إدارة المستخدمين (ترقية/تخفيض/حظر)
- نظام الإضافات (Plugins)
- إحصائيات شاملة
- بث رسائل لجميع المستخدمين

### 🔐 الأمان
- Rate Limiting
- حماية من السبام
- تسجيل جميع العمليات
- نظام صلاحيات متعدد المستويات

### 💬 تجربة استخدام نظيفة
- تعديل الرسائل بدلاً من إرسال جديدة
- أزرار Inline تفاعلية
- حذف الرسائل المؤقتة تلقائياً
- فيديو نجاح بعد كل عملية ناجحة

## 🚀 التشغيل

### المتطلبات
- Node.js 18+
- MongoDB
- FFmpeg (لتحويل الوسائط)
- yt-dlp (اختياري - لتحميل الفيديو)
- edge-tts (اختياري - لتحويل النص لصوت)

### التثبيت

```bash
# استنساخ المشروع
git clone https://github.com/mohareb123/bot-.git
cd bot-

# تثبيت الاعتماديات
npm install

# نسخ ملف البيئة
cp .env.example .env
# قم بتعديل .env وإضافة المفاتيح المطلوبة

# بناء المشروع
npm run build

# تشغيل البوت
npm start
```

### التطوير

```bash
# تشغيل في وضع التطوير (إعادة تحميل تلقائي)
npm run dev
```

### باستخدام Docker

```bash
docker build -t ai-telegram-bot .
docker run -d --env-file .env ai-telegram-bot
```

## ⚙️ إعداد المتغيرات (.env)

| المتغير | الوصف | مطلوب |
|---------|-------|-------|
| `BOT_TOKEN` | توكن البوت من @BotFather | ✅ |
| `MONGODB_URI` | رابط اتصال MongoDB | ✅ |
| `ADMIN_IDS` | معرفات الأدمن (مفصولة بفواصل) | ✅ |
| `GEMINI_API_KEY` | مفتاح Google Gemini API | مُوصى |
| `WIT_AI_TOKEN` | توكن Wit.ai لتحويل الصوت لنص | اختياري |
| `REQUIRED_CHANNELS` | قنوات الاشتراك الإجباري | اختياري |
| `SUCCESS_VIDEO_URL` | رابط فيديو النجاح | اختياري |

راجع `.env.example` للقائمة الكاملة.

## 📝 الأوامر

### أوامر المستخدم
| الأمر | الوصف |
|-------|-------|
| `/start` | بدء البوت |
| `/help` | عرض المساعدة |
| `/imagine [وصف]` | إنشاء صورة |
| `/edit_image [وصف]` | تعديل صورة (كرد على صورة) |
| `/tts [نص]` | تحويل النص لصوت |
| `/voice` | اختيار الصوت |
| `/download [رابط]` | تحميل فيديو |
| `/mp3 [رابط]` | تحميل كـ MP3 |
| `/clear` | مسح سجل المحادثة |
| `/stats` | إحصائياتك |

### أوامر الأدمن
| الأمر | الوصف |
|-------|-------|
| `/admin` | لوحة التحكم |
| `/addchannel [username]` | إضافة قناة إجبارية |
| `/removechannel [username]` | حذف قناة |
| `/promote [user_id]` | ترقية لأدمن |
| `/demote [user_id]` | تخفيض رتبة |
| `/ban [user_id]` | حظر مستخدم |
| `/unban [user_id]` | إلغاء حظر |
| `/broadcast [رسالة]` | بث رسالة للجميع |

## 🏗️ هيكل المشروع

```
src/
├── index.ts              # نقطة البدء
├── bot.ts                # إعداد البوت
├── config.ts             # إعدادات البيئة
├── database.ts           # اتصال MongoDB
├── types/                # تعريفات TypeScript
├── models/               # نماذج قاعدة البيانات
│   ├── User.ts
│   ├── Group.ts
│   ├── Channel.ts
│   ├── Plugin.ts
│   └── Log.ts
├── middleware/            # برامج وسيطة
│   ├── auth.ts           # مصادقة المستخدمين
│   ├── subscription.ts   # التحقق من الاشتراك
│   ├── rateLimit.ts      # تحديد الطلبات
│   └── loggerMiddleware.ts
├── handlers/             # معالجات الأوامر
│   ├── start.ts          # /start, /help
│   ├── ai.ts             # ذكاء اصطناعي
│   ├── media.ts          # تحميل وسائط
│   ├── voice.ts          # TTS + STT
│   ├── admin.ts          # لوحة التحكم
│   └── callbacks.ts      # أزرار Inline
├── services/             # خدمات خارجية
│   ├── ai/
│   │   ├── provider.ts   # مدير مقدمي AI
│   │   ├── chat.ts       # Gemini + OpenAI + Free
│   │   └── imageGeneration.ts
│   ├── media/
│   │   ├── downloader.ts # Cobalt + yt-dlp
│   │   └── converter.ts  # FFmpeg
│   └── voice/
│       ├── tts.ts        # Edge TTS
│       └── stt.ts        # Wit.ai + Whisper
├── admin/                # API لوحة التحكم
│   ├── server.ts
│   └── routes/
└── utils/                # أدوات مساعدة
    ├── logger.ts
    ├── messages.ts
    ├── keyboard.ts
    └── helpers.ts
```

## 🐳 Docker

```dockerfile
FROM node:20-alpine
RUN apk add --no-cache ffmpeg python3 py3-pip
RUN pip3 install edge-tts yt-dlp
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY dist/ ./dist/
COPY assets/ ./assets/
CMD ["node", "dist/index.js"]
```

## 📜 الترخيص

MIT License
