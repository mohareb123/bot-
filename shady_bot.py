#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 بوت شادي v4.0 - قنبلة الابتكار 💣
المطور: 6570434162
"""

import asyncio
import logging
import sqlite3
import random
import re
import json
import datetime
import math
from typing import Optional
from functools import wraps

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, ChatMemberAdministrator, ChatMemberOwner,
    ChatMember
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ChatMemberHandler
)
from telegram.constants import ParseMode, ChatType
from telegram.error import TelegramError

# ═══════════════════════════════════════════
#              الإعدادات الأساسية
# ═══════════════════════════════════════════

BOT_TOKEN = "8468271421:AAEZEtfr2oWzmCwmXiKDsjP40Y8JUgkhANE"
DEVELOPER_ID = 6570434162

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('shady_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ShadyBot")

# ═══════════════════════════════════════════
#              قاعدة البيانات
# ═══════════════════════════════════════════

class DB:
    def __init__(self, path="shady_bot.db"):
        self.path = path
        self._init()

    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self.conn() as c:
            c.executescript('''
                CREATE TABLE IF NOT EXISTS members (
                    user_id INTEGER, chat_id INTEGER,
                    username TEXT, full_name TEXT,
                    points INTEGER DEFAULT 0, coins INTEGER DEFAULT 100,
                    level INTEGER DEFAULT 1, messages_count INTEGER DEFAULT 0,
                    warnings INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
                    last_daily TEXT DEFAULT NULL,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, chat_id));

                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER, admin_id INTEGER, admin_name TEXT,
                    target_id INTEGER, target_name TEXT,
                    action TEXT, reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

                CREATE TABLE IF NOT EXISTS messages_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER, user_id INTEGER,
                    user_name TEXT, message_preview TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

                CREATE TABLE IF NOT EXISTS auto_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER, trigger_word TEXT, response TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

                CREATE TABLE IF NOT EXISTS whispers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER, sender_name TEXT,
                    recipient_id INTEGER, recipient_name TEXT,
                    message TEXT, chat_id INTEGER, is_read INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

                CREATE TABLE IF NOT EXISTS group_settings (
                    chat_id INTEGER PRIMARY KEY,
                    links_allowed INTEGER DEFAULT 0,
                    media_allowed INTEGER DEFAULT 1,
                    spam_protection INTEGER DEFAULT 1,
                    welcome_enabled INTEGER DEFAULT 1,
                    max_warnings INTEGER DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT, answer TEXT, options TEXT,
                    category TEXT DEFAULT 'عام');

                CREATE TABLE IF NOT EXISTS polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER, question TEXT,
                    options TEXT, votes TEXT DEFAULT '{}',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            ''')
            # بذر الأسئلة
            if c.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0] == 0:
                self._seed_questions(c)

    def _seed_questions(self, c):
        qs = [
            ("ما عاصمة المملكة العربية السعودية؟", "الرياض", '["الرياض","جدة","مكة المكرمة","الدمام"]', "جغرافيا"),
            ("كم عدد أيام السنة الميلادية؟", "365", '["360","365","366","354"]', "عام"),
            ("أكبر محيط في العالم؟", "المحيط الهادئ", '["المحيط الهادئ","المحيط الأطلسي","المحيط الهندي","البحر المتوسط"]', "جغرافيا"),
            ("أطول نهر في العالم؟", "نهر النيل", '["نهر النيل","نهر الأمازون","نهر الكونغو","نهر الفرات"]', "جغرافيا"),
            ("كم يساوي Pi تقريباً؟", "3.14", '["3.14","3.41","2.71","3.16"]', "رياضيات"),
            ("أكبر دولة في العالم مساحةً؟", "روسيا", '["روسيا","الصين","كندا","الولايات المتحدة"]', "جغرافيا"),
            ("من اخترع الهاتف؟", "غراهام بيل", '["غراهام بيل","نيكولا تيسلا","توماس إديسون","ماركوني"]', "علوم"),
            ("عاصمة اليابان؟", "طوكيو", '["طوكيو","أوساكا","كيوتو","هيروشيما"]', "جغرافيا"),
            ("كم لاعباً في فريق كرة القدم؟", "11", '["9","10","11","12"]', "رياضة"),
            ("أسرع حيوان على الأرض؟", "الفهد", '["الفهد","الأسد","النمر","الحصان"]', "علوم"),
            ("دولة مجلس التعاون الخليجي كم عددها؟", "6", '["4","5","6","7"]', "عام"),
            ("أكبر كوكب في المجموعة الشمسية؟", "المشتري", '["المريخ","زحل","المشتري","أورانوس"]', "علوم"),
            ("من كتب ألف ليلة وليلة؟", "مجهول", '["شهرزاد","مجهول","ابن خلدون","الجاحظ"]', "أدب"),
            ("كم يبلغ عدد سكان مصر تقريباً؟", "100 مليون", '["50 مليون","75 مليون","100 مليون","150 مليون"]', "جغرافيا"),
            ("ما العنصر الأكثر انتشاراً في الكون؟", "الهيدروجين", '["الأكسجين","الهيدروجين","الكربون","الهيليوم"]', "علوم"),
            ("ما عاصمة البرازيل؟", "برازيليا", '["ريو دي جانيرو","ساو باولو","برازيليا","بوينس آيرس"]', "جغرافيا"),
            ("من رسم الموناليزا؟", "ليوناردو دا فينشي", '["مايكل أنجلو","ليوناردو دا فينشي","رافائيل","بيكاسو"]', "فنون"),
            ("ما أصغر دولة في العالم؟", "الفاتيكان", '["موناكو","الفاتيكان","سان مارينو","ليختنشتاين"]', "جغرافيا"),
            ("كم ضلعاً في المثمن؟", "8", '["6","7","8","9"]', "رياضيات"),
            ("ما هو حامض DNA؟", "ديوكسي ريبوز نيوكليوتيد", '["ريبوز نيوكليوتيد","ديوكسي ريبوز نيوكليوتيد","أمينو حمض","بروتين"]', "علوم"),
        ]
        c.executemany("INSERT INTO quiz_questions (question,answer,options,category) VALUES (?,?,?,?)", qs)

    # ── أعضاء ──────────────────────────────────
    def upsert_member(self, uid, cid, username=None, name=None):
        with self.conn() as c:
            c.execute('''INSERT OR IGNORE INTO members (user_id,chat_id,username,full_name)
                         VALUES (?,?,?,?)''', (uid, cid, username, name))
            if username or name:
                c.execute('''UPDATE members SET username=COALESCE(?,username),
                             full_name=COALESCE(?,full_name) WHERE user_id=? AND chat_id=?''',
                          (username, name, uid, cid))

    def add_activity(self, uid, cid):
        with self.conn() as c:
            c.execute('''UPDATE members SET
                messages_count=messages_count+1,
                points=points+1,
                last_active=CURRENT_TIMESTAMP,
                level=CASE
                    WHEN points>=5000 THEN 10 WHEN points>=2000 THEN 9
                    WHEN points>=1000 THEN 8 WHEN points>=500  THEN 7
                    WHEN points>=200  THEN 6 WHEN points>=100  THEN 5
                    WHEN points>=50   THEN 4 WHEN points>=20   THEN 3
                    WHEN points>=10   THEN 2 ELSE 1 END
                WHERE user_id=? AND chat_id=?''', (uid, cid))

    def add_points(self, uid, cid, pts):
        with self.conn() as c:
            c.execute("UPDATE members SET points=points+?, coins=coins+? WHERE user_id=? AND chat_id=?",
                      (pts, pts // 2, uid, cid))

    def remove_coins(self, uid, cid, amount) -> bool:
        with self.conn() as c:
            row = c.execute("SELECT coins FROM members WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
            if not row or row['coins'] < amount:
                return False
            c.execute("UPDATE members SET coins=coins-? WHERE user_id=? AND chat_id=?", (amount, uid, cid))
            return True

    def transfer_coins(self, from_uid, to_uid, cid, amount) -> bool:
        if not self.remove_coins(from_uid, cid, amount):
            return False
        with self.conn() as c:
            c.execute("UPDATE members SET coins=coins+? WHERE user_id=? AND chat_id=?", (amount, to_uid, cid))
        return True

    def claim_daily(self, uid, cid):
        today = datetime.date.today().isoformat()
        with self.conn() as c:
            row = c.execute("SELECT last_daily FROM members WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
            if not row:
                return False, 0
            if row['last_daily'] == today:
                return False, 0
            reward = random.randint(50, 200)
            c.execute("UPDATE members SET last_daily=?, points=points+?, coins=coins+? WHERE user_id=? AND chat_id=?",
                      (today, reward, reward, uid, cid))
            return True, reward

    def member(self, uid, cid):
        with self.conn() as c:
            r = c.execute("SELECT * FROM members WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
            return dict(r) if r else None

    def top(self, cid, n=10):
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM members WHERE chat_id=? AND is_banned=0 ORDER BY points DESC LIMIT ?", (cid, n)).fetchall()]

    def add_warning(self, uid, cid):
        with self.conn() as c:
            c.execute("UPDATE members SET warnings=warnings+1 WHERE user_id=? AND chat_id=?", (uid, cid))
            r = c.execute("SELECT warnings FROM members WHERE user_id=? AND chat_id=?", (uid, cid)).fetchone()
            return r['warnings'] if r else 1

    def reset_warnings(self, uid, cid):
        with self.conn() as c:
            c.execute("UPDATE members SET warnings=0 WHERE user_id=? AND chat_id=?", (uid, cid))

    # ── سجلات ─────────────────────────────────
    def log_action(self, cid, aid, aname, tid, tname, action, reason=""):
        with self.conn() as c:
            c.execute('''INSERT INTO admin_logs (chat_id,admin_id,admin_name,target_id,target_name,action,reason)
                         VALUES (?,?,?,?,?,?,?)''', (cid, aid, aname, tid, tname, action, reason))

    def log_message(self, cid, uid, uname, preview):
        with self.conn() as c:
            c.execute("INSERT INTO messages_log (chat_id,user_id,user_name,message_preview) VALUES (?,?,?,?)",
                      (cid, uid, uname, preview[:100]))
            # نحتفظ فقط بآخر 500 رسالة
            c.execute("DELETE FROM messages_log WHERE id NOT IN (SELECT id FROM messages_log ORDER BY id DESC LIMIT 500)")

    def recent_logs(self, cid=None, n=20):
        with self.conn() as c:
            if cid:
                return [dict(r) for r in c.execute(
                    "SELECT * FROM admin_logs WHERE chat_id=? ORDER BY timestamp DESC LIMIT ?", (cid, n)).fetchall()]
            return [dict(r) for r in c.execute(
                "SELECT * FROM admin_logs ORDER BY timestamp DESC LIMIT ?", (n,)).fetchall()]

    def global_stats(self):
        with self.conn() as c:
            return {
                "total_users": c.execute("SELECT COUNT(DISTINCT user_id) FROM members").fetchone()[0],
                "total_groups": c.execute("SELECT COUNT(DISTINCT chat_id) FROM members").fetchone()[0],
                "total_actions": c.execute("SELECT COUNT(*) FROM admin_logs").fetchone()[0],
                "total_whispers": c.execute("SELECT COUNT(*) FROM whispers").fetchone()[0],
                "total_messages": c.execute("SELECT SUM(messages_count) FROM members").fetchone()[0] or 0,
                "bans_count": c.execute("SELECT COUNT(*) FROM admin_logs WHERE action='حظر'").fetchone()[0],
                "kicks_count": c.execute("SELECT COUNT(*) FROM admin_logs WHERE action='طرد'").fetchone()[0],
                "warns_count": c.execute("SELECT COUNT(*) FROM admin_logs WHERE action='تحذير'").fetchone()[0],
            }

    # ── ردود تلقائية ───────────────────────────
    def add_response(self, cid, trigger, response, uid):
        with self.conn() as c:
            c.execute("INSERT INTO auto_responses (chat_id,trigger_word,response,created_by) VALUES (?,?,?,?)",
                      (cid, trigger.lower(), response, uid))

    def get_response(self, cid, text):
        with self.conn() as c:
            r = c.execute("SELECT response FROM auto_responses WHERE chat_id=? AND ? LIKE '%'||trigger_word||'%'",
                          (cid, text.lower())).fetchone()
            return r['response'] if r else None

    def list_responses(self, cid):
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM auto_responses WHERE chat_id=?", (cid,)).fetchall()]

    def del_response(self, rid, cid):
        with self.conn() as c:
            c.execute("DELETE FROM auto_responses WHERE id=? AND chat_id=?", (rid, cid))

    # ── همسات ─────────────────────────────────
    def save_whisper(self, sid, sname, rid, rname, msg, cid):
        with self.conn() as c:
            c.execute('''INSERT INTO whispers (sender_id,sender_name,recipient_id,recipient_name,message,chat_id)
                         VALUES (?,?,?,?,?,?)''', (sid, sname, rid, rname, msg, cid))
            return c.lastrowid

    def get_whisper(self, wid):
        with self.conn() as c:
            r = c.execute("SELECT * FROM whispers WHERE id=?", (wid,)).fetchone()
            return dict(r) if r else None

    def read_whisper(self, wid):
        with self.conn() as c:
            c.execute("UPDATE whispers SET is_read=1 WHERE id=?", (wid,))

    # ── إعدادات ────────────────────────────────
    def settings(self, cid):
        with self.conn() as c:
            r = c.execute("SELECT * FROM group_settings WHERE chat_id=?", (cid,)).fetchone()
            if not r:
                c.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (cid,))
                r = c.execute("SELECT * FROM group_settings WHERE chat_id=?", (cid,)).fetchone()
            return dict(r)

    def set_setting(self, cid, key, val):
        with self.conn() as c:
            c.execute(f"UPDATE group_settings SET {key}=? WHERE chat_id=?", (val, cid))

    # ── اختبار ────────────────────────────────
    def random_question(self):
        with self.conn() as c:
            r = c.execute("SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT 1").fetchone()
            return dict(r) if r else None

    def members_list(self, cid=None, limit=50):
        with self.conn() as c:
            if cid:
                return [dict(r) for r in c.execute(
                    "SELECT * FROM members WHERE chat_id=? ORDER BY points DESC LIMIT ?", (cid, limit)).fetchall()]
            return [dict(r) for r in c.execute(
                "SELECT * FROM members ORDER BY points DESC LIMIT ?", (limit,)).fetchall()]

    def recent_messages(self, n=50):
        with self.conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM messages_log ORDER BY id DESC LIMIT ?", (n,)).fetchall()]

    def activity_by_day(self):
        with self.conn() as c:
            rows = c.execute('''
                SELECT DATE(timestamp) as day, COUNT(*) as msg_count
                FROM messages_log
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY day ASC
            ''').fetchall()
            return [dict(r) for r in rows]

    def action_by_day(self):
        with self.conn() as c:
            rows = c.execute('''
                SELECT DATE(timestamp) as day, COUNT(*) as action_count
                FROM admin_logs
                WHERE timestamp >= DATE('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY day ASC
            ''').fetchall()
            return [dict(r) for r in rows]


db = DB()

# ═══════════════════════════════════════════
#           مكتبة الردود والشخصية
# ═══════════════════════════════════════════

GREETINGS = ["السلام عليكم", "مرحبا", "هلا", "صباح الخير", "مساء الخير",
             "هاي", "هلو", "يسعد", "يسعدك", "الله يسعدك", "أهلا", "أهلين",
             "هلو", "hey", "hi", "hello", "وعليكم السلام"]

FAREWELL = ["باي", "مع السلامة", "وداعا", "إلى اللقاء", "تصبح على خير", "يسلمك"]

THANKS = ["شكرا", "شكراً", "مشكور", "يسلمو", "يسلموا", "ممنون", "شكر"]

QUESTIONS_WORDS = ["كيف", "ماهو", "ما هو", "ما هي", "ماهي", "من هو", "من هي", "أين",
                   "متى", "لماذا", "لماذ", "هل", "وين", "ليش", "ايش", "ايه"]

COMPLAIN_WORDS = ["زهقت", "تعبت", "مللت", "ما عندي", "مافي", "محتاج", "الله يعين",
                  "صعب", "مش قادر", "متعب", "متضايق", "زهق", "مضايق"]

LOVE_WORDS = ["بحبك", "أحبك", "احبك", "حبيبي", "حبيبتي", "زعلت", "عايشه", "غلطت"]

SHADY_NAMES = ["شادي", "شادى", "الشادي"]

SHADY_GREET_REPLIES = [
    "أهلاً وسهلاً! 🤖 كيف أقدر أساعدك؟",
    "هلا هلا! أنا هنا 👋",
    "نعم! في خدمتكم دائماً 🌟",
    "مرحباً! ماذا تحتاج؟ 😊",
    "يا هلا فيك! 💙",
]

SHADY_THANKS_REPLIES = [
    "العفو! يسعدني مساعدتك 😊",
    "بكل سرور! أنا دايم هنا 💙",
    "لا شكر على واجب! 🌟",
    "الله يسلمك! 😄",
]

RANDOM_COMMENTS = [
    "🤔 كلام وجيه!",
    "😂 هههه حلوة",
    "👀 معاك معاك",
    "💯 صح كلامك",
    "🔥 هههه",
    "😅 ايوه!",
    "🎯 بالضبط!",
    "👌 تمام تمام",
    "🌚 أوكي...",
    "😏 اهمم!",
    "😂 الله يكون في عونك",
]

WISDOM = [
    "💡 *حكمة اليوم:* من صبر ظفر.",
    "💡 *حكمة اليوم:* الوقت كالسيف، إن لم تقطعه قطعك.",
    "💡 *حكمة اليوم:* العلم في الصغر كالنقش على الحجر.",
    "💡 *حكمة اليوم:* لسانك حصانك، إن صنته صانك.",
    "💡 *حكمة اليوم:* من جد وجد، ومن زرع حصد.",
    "💡 *حكمة اليوم:* الصديق وقت الضيق.",
    "💡 *حكمة اليوم:* اطلب العلم من المهد إلى اللحد.",
    "💡 *حكمة اليوم:* اللي بيتعلم من التجارب أذكى من اللي بيتعلم من الكتب.",
]

JOKES = [
    "😂 واحد راح للطبيب قاله: دكتور أحس إن أحد يتجاهلني\nالدكتور: التالي!",
    "😂 قالوا للغبي: اكتب مقالة عن الجبن\nكتب: الجبن... الجبن... الجبن (3 صفحات)",
    "😂 واحد سأل: وين الساعة الثلاثة؟\nرد عليه: بين الثانية والرابعة 😐",
    "😂 معلم قال للطالب: اقرأ الفقرة\nالطالب: ما أقدر\nالمعلم: ليش؟\nالطالب: كتابتك ما تنقرأ",
    "😂 دخل ثلاثة على مسابقة ذكاء. الأول قال 2+2=4 طلعوه.\nالثاني قال 2+2=4 طلعوه.\nالثالث قال 2+2=4 طلعوه.\nالرابع قال 2+2=4 طلعوه.",
    "😂 سألوا الأخطبوط: بتلعب موسيقى؟\nقال: أيوه، وبنفس الوقت 🐙",
    "😂 الطالب للأستاذ: ليش الشمس ما تطلع الليل؟\nالأستاذ: لأنها بتطلع النهار يا ذكي!",
]

FORTUNE = [
    "🔮 حظك اليوم: نجوم المال في صفك! توقع مفاجأة مالية 💰",
    "🔮 حظك اليوم: أحذر من شخص يحمل وجهين... ربما صديقك القديم 👀",
    "🔮 حظك اليوم: يوم موفق جداً! اغتنم الفرص المتاحة ⭐",
    "🔮 حظك اليوم: ستلتقي بشخص مهم سيغير مسار حياتك 🌟",
    "🔮 حظك اليوم: الصحة بخير لكن قلل الجلوس! تحرك قليلاً 🏃",
    "🔮 حظك اليوم: يوم مثالي للبدء بمشروع جديد 🚀",
    "🔮 حظك اليوم: علاقاتك ستتحسن اليوم، تواصل مع أحبائك ❤️",
    "🔮 حظك اليوم: اليوم ليس مثالياً للقرارات الكبيرة، انتظر غداً 🌙",
]

ROASTS = [
    "أنت مثل الإنترنت بدون باسورد... متاح للكل 😂",
    "لو كان الذكاء مطراً، أنت صحراء! 🏜️",
    "وجهك يطفئ الشموع بدل ما يضيئها 🕯️😂",
    "تكلمت مع المرآة، قالتلي خذ يوم إجازة 🪞😂",
    "حتى الـ GPS بيتوه لما يوديك 🗺️😂",
    "قلت للجوجل عنك، وقفل الموقع 🔒😂",
    "أنت فريد من نوعك... والحمد لله على ذلك 😂",
]

COMPLIMENTS = [
    "والله أنت شخص رائع وإنسان من زمن التمر والعسل! 🍯",
    "ربنا يكرمك! قلبك أطهر من المطر 💙",
    "أنت من النوع النادر اللي العالم يحتاجه 🌟",
    "مبروك عليك عقلك الراقي وقلبك الكبير ❤️",
    "الله يزيدك من نعمته! إنسان من زمن الخير 😊",
    "أنت كنز مخفي 💎 والله يوفقك دائماً",
]

SYMPATHY = [
    "الله يعينك يا صديقي 💙 اصبر، بعد الضيق فرج",
    "ما تهون! كل الناس بتمر بظروف صعبة وبتعدي 🌟",
    "أنا هنا إذا محتاج أحد يسمعك 💙",
    "اللي ما يكسرك يقويك! إنت قوي أكثر مما تظن 💪",
    "روح استرح، بكرة أحسن إن شاء الله 🌈",
]

ANSWER_KNOW_WORDS = [
    "هاه! هذا سؤال ذكي 🤔",
    "سؤال ممتاز! دعني أفكر...",
    "آه! سؤال جيد 👆",
]

ANSWER_DONT_KNOW = [
    "صراحةً ما أعرف 😅 لكن جوجل يعرف!",
    "هذا خارج إمكانياتي الحالية 🤖 اسأل جوجل!",
    "والله ما عندي جواب محدد لهذا 🤷 لكن الله كريم",
    "سؤال صعب! حتى الروبوتات ما تعرف كل شيء 😅",
]


def name_mentioned(text: str) -> bool:
    t = text.lower()
    return any(n in t for n in SHADY_NAMES)


def is_greeting(text: str) -> bool:
    t = text.lower()
    return any(g in t for g in GREETINGS)


def is_farewell(text: str) -> bool:
    t = text.lower()
    return any(f in t for f in FAREWELL)


def is_thanks(text: str) -> bool:
    t = text.lower()
    return any(th in t for th in THANKS)


def is_question(text: str) -> bool:
    return text.strip().endswith("?") or text.strip().endswith("؟") or \
           any(w in text.lower() for w in QUESTIONS_WORDS)


def is_complaint(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in COMPLAIN_WORDS)


def is_love(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in LOVE_WORDS)


# ═══════════════════════════════════════════
#           دوال مساعدة
# ═══════════════════════════════════════════

async def is_admin(bot, cid, uid) -> bool:
    if uid == DEVELOPER_ID:
        return True
    try:
        m = await bot.get_chat_member(cid, uid)
        return isinstance(m, (ChatMemberAdministrator, ChatMemberOwner))
    except:
        return False


def admin_only(fn):
    @wraps(fn)
    async def wrap(update: Update, ctx: ContextTypes.DEFAULT_TYPE, *a, **kw):
        u = update.effective_user
        c = update.effective_chat
        if not u or not c:
            return
        if u.id == DEVELOPER_ID:
            return await fn(update, ctx, *a, **kw)
        if c.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                m = await ctx.bot.get_chat_member(c.id, u.id)
                if isinstance(m, (ChatMemberAdministrator, ChatMemberOwner)):
                    return await fn(update, ctx, *a, **kw)
                await update.message.reply_text("⛔ هذا الأمر للمشرفين فقط!")
            except:
                pass
        else:
            return await fn(update, ctx, *a, **kw)
    return wrap


async def get_target(update, ctx):
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        t = msg.reply_to_message.from_user
        return t, t.full_name
    if ctx.args:
        arg = ctx.args[0]
        try:
            uid = int(arg)
            chat = await ctx.bot.get_chat(uid)
            return chat, chat.full_name
        except:
            pass
        if arg.startswith('@'):
            try:
                chat = await ctx.bot.get_chat(arg)
                return chat, chat.full_name
            except:
                pass
    return None, None


# ═══════════════════════════════════════════
#           الأوامر الأساسية
# ═══════════════════════════════════════════

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    kb = [
        [InlineKeyboardButton("📋 الأوامر", callback_data="help_menu"),
         InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats")],
        [InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu"),
         InlineKeyboardButton("🏆 الترتيب", callback_data="leaderboard")],
        [InlineKeyboardButton("💰 محفظتي", callback_data="my_wallet"),
         InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_menu")],
        [InlineKeyboardButton("👨‍💻 المطور", url=f"tg://user?id={DEVELOPER_ID}")]
    ]
    if u.id == DEVELOPER_ID:
        kb.append([InlineKeyboardButton("🔧 لوحة المطور", callback_data="dev_panel")])

    await update.message.reply_text(
        f"🤖 <b>أهلاً {u.first_name}! أنا شادي 💣</b>\n\n"
        "🧠 أفهم كلامك حتى لو ما ذكرت اسمي!\n"
        "🎮 ألعاب + نقاط + عملة افتراضية\n"
        "🛡️ حماية وإدارة احترافية\n"
        "💌 همسات سرية بين الأعضاء\n"
        "😂 نكات + حكم + هجايص يومية\n\n"
        "<i>اختر من القائمة أو كلمني بشكل طبيعي 👇</i>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = """📚 <b>دليل بوت شادي الكامل</b>

<b>🎮 الترفيه:</b>
/quiz — لعبة الأسئلة (+5 نقاط للإجابة)
/hack [@user] — اختراق وهمي مضحك
/judgment — لعبة الأحكام والتصويت
/ship @user1 @user2 — قياس التوافق
/8ball [سؤال] — الكرة الكهربائية
/fortune — حظك اليوم
/joke — نكتة عشوائية
/roast [@user] — هجايص مضحكة
/compliment [@user] — مدح وإطراء
/wisdom — حكمة اليوم

<b>💰 الاقتصاد:</b>
/daily — مكافأة يومية (50-200 نقطة)
/gift @user [كمية] — هدية عملة
/wallet — رصيدك الحالي
/stats — إحصائياتك الكاملة
/top — أكثر الأعضاء نشاطاً

<b>🛡️ الإدارة (مشرفون):</b>
/ban — حظر عضو
/kick — طرد عضو
/mute [دقائق] — كتم عضو
/unmute — رفع الكتم
/warn [سبب] — تحذير
/promote — ترقية لمشرف
/settings — إعدادات المجموعة
/addresponse كلمة | رد — رد تلقائي
/delresponse [رقم] — حذف رد
/responses — الردود الحالية
/all — نداء عام

<b>💌 خاص:</b>
/whisper @user رسالة — همسة سرية
/calc [حساب] — آلة حاسبة

<b>🤖 شادي يرد على كل شيء تلقائياً!</b>"""
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════
#           الأوامر الإدارية
# ═══════════════════════════════════════════

@admin_only
async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    admin = update.effective_user
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة العضو أو اذكر اسمه!")
    reason = " ".join(ctx.args[1:]) if ctx.args and len(ctx.args) > 1 else "لم يُذكر"
    try:
        await ctx.bot.ban_chat_member(cid, target.id)
        db.log_action(cid, admin.id, admin.full_name, target.id, tname, "حظر", reason)
        await update.message.reply_text(
            f"🔨 <b>تم الحظر</b>\n👤 {tname}\n👮 {admin.full_name}\n📝 {reason}",
            parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ فشل: {e}")


@admin_only
async def kick_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    admin = update.effective_user
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة العضو!")
    reason = " ".join(ctx.args[1:]) if ctx.args and len(ctx.args) > 1 else "لم يُذكر"
    try:
        await ctx.bot.ban_chat_member(cid, target.id)
        await ctx.bot.unban_chat_member(cid, target.id)
        db.log_action(cid, admin.id, admin.full_name, target.id, tname, "طرد", reason)
        await update.message.reply_text(
            f"👢 <b>تم الطرد</b>\n👤 {tname}\n👮 {admin.full_name}\n📝 {reason}",
            parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ فشل: {e}")


@admin_only
async def mute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    admin = update.effective_user
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة العضو!")
    mins = 60
    try:
        if ctx.args:
            mins = int(ctx.args[0])
    except:
        pass
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=mins)
    try:
        await ctx.bot.restrict_chat_member(cid, target.id, ChatPermissions(can_send_messages=False), until_date=until)
        db.log_action(cid, admin.id, admin.full_name, target.id, tname, "كتم", f"{mins} دقيقة")
        await update.message.reply_text(
            f"🔇 <b>تم الكتم</b>\n👤 {tname}\n⏱️ {mins} دقيقة",
            parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ فشل: {e}")


@admin_only
async def unmute_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    admin = update.effective_user
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة العضو!")
    try:
        await ctx.bot.restrict_chat_member(cid, target.id, ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True,
            can_send_photos=True, can_send_videos=True, can_send_voice_notes=True,
            can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True
        ))
        db.log_action(cid, admin.id, admin.full_name, target.id, tname, "رفع كتم", "")
        await update.message.reply_text(f"🔊 تم رفع الكتم عن <b>{tname}</b>", parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ فشل: {e}")


@admin_only
async def warn_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    admin = update.effective_user
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة العضو!")
    reason = " ".join(ctx.args) if ctx.args else "مخالفة القواعد"
    db.upsert_member(target.id, cid, getattr(target, 'username', None), getattr(target, 'full_name', tname))
    w = db.add_warning(target.id, cid)
    s = db.settings(cid)
    max_w = s.get('max_warnings', 3)
    db.log_action(cid, admin.id, admin.full_name, target.id, tname, "تحذير", reason)
    if w >= max_w:
        try:
            await ctx.bot.ban_chat_member(cid, target.id)
            await ctx.bot.unban_chat_member(cid, target.id)
            db.reset_warnings(target.id, cid)
            await update.message.reply_text(
                f"🚨 <b>طرد تلقائي!</b>\n👤 {tname} — تجاوز {max_w} تحذيرات",
                parse_mode=ParseMode.HTML)
        except TelegramError as e:
            await update.message.reply_text(f"❌ فشل الطرد: {e}")
    else:
        await update.message.reply_text(
            f"⚠️ <b>تحذير #{w}/{max_w}</b>\n👤 {tname}\n📝 {reason}",
            parse_mode=ParseMode.HTML)


@admin_only
async def promote_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    admin = update.effective_user
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة العضو!")
    try:
        await ctx.bot.promote_chat_member(cid, target.id,
            can_delete_messages=True, can_restrict_members=True,
            can_pin_messages=True, can_invite_users=True)
        db.log_action(cid, admin.id, admin.full_name, target.id, tname, "ترقية", "")
        await update.message.reply_text(f"⭐ <b>{tname}</b> أصبح مشرفاً!", parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ فشل: {e}")


@admin_only
async def settings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    s = db.settings(cid)
    kb = [
        [InlineKeyboardButton(f"🔗 الروابط: {'✅' if s['links_allowed'] else '❌'}", callback_data=f"toggle_links_{cid}"),
         InlineKeyboardButton(f"📸 الوسائط: {'✅' if s['media_allowed'] else '❌'}", callback_data=f"toggle_media_{cid}")],
        [InlineKeyboardButton(f"🛡️ مكافحة السبام: {'✅' if s['spam_protection'] else '❌'}", callback_data=f"toggle_spam_{cid}"),
         InlineKeyboardButton(f"👋 ترحيب: {'✅' if s['welcome_enabled'] else '❌'}", callback_data=f"toggle_welcome_{cid}")],
        [InlineKeyboardButton("📋 سجل العمليات", callback_data=f"view_logs_{cid}"),
         InlineKeyboardButton("🔙 إغلاق", callback_data="close_menu")]
    ]
    await update.message.reply_text("⚙️ <b>إعدادات المجموعة</b>",
                                     reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)


@admin_only
async def all_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    try:
        admins = await ctx.bot.get_chat_administrators(cid)
        mentions = [f"@{a.user.username}" if a.user.username else
                    f"<a href='tg://user?id={a.user.id}'>{a.user.first_name}</a>"
                    for a in admins if not a.user.is_bot]
        if mentions:
            await update.message.reply_text(
                "📢 <b>نداء عام للمشرفين!</b>\n\n" + " ".join(mentions), parse_mode=ParseMode.HTML)
    except TelegramError as e:
        await update.message.reply_text(f"❌ {e}")


@admin_only
async def addresponse_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split("|", 1)
    if len(parts) < 2:
        return await update.message.reply_text("❌ الاستخدام:\n/addresponse كلمة | رد")
    trigger = parts[0].replace("/addresponse", "").strip()
    response = parts[1].strip()
    if not trigger or not response:
        return await update.message.reply_text("❌ يجب إدخال كلمة ورد!")
    db.add_response(update.effective_chat.id, trigger, response, update.effective_user.id)
    await update.message.reply_text(f"✅ تم!\n🔑 <b>{trigger}</b> → {response}", parse_mode=ParseMode.HTML)


@admin_only
async def responses_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rs = db.list_responses(update.effective_chat.id)
    if not rs:
        return await update.message.reply_text("لا توجد ردود تلقائية حالياً.")
    txt = "📋 <b>الردود التلقائية:</b>\n\n" + \
          "\n".join(f"#{r['id']} <b>{r['trigger_word']}</b> → {r['response'][:30]}" for r in rs)
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


@admin_only
async def delresponse_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("❌ مثال: /delresponse 3")
    try:
        db.del_response(int(ctx.args[0]), update.effective_chat.id)
        await update.message.reply_text(f"✅ تم حذف الرد #{ctx.args[0]}")
    except:
        await update.message.reply_text("❌ رقم غير صحيح!")


# ═══════════════════════════════════════════
#           الألعاب والترفيه
# ═══════════════════════════════════════════

async def quiz_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_quiz(update.message, update.effective_chat.id)


async def _send_quiz(msg, cid):
    q = db.random_question()
    if not q:
        return await msg.reply_text("❌ لا توجد أسئلة!")
    options = json.loads(q['options'])
    random.shuffle(options)
    kb = [[InlineKeyboardButton(opt, callback_data=f"quiz_{'c' if opt == q['answer'] else 'w'}_{q['id']}")]
          for opt in options]
    await msg.reply_text(
        f"🎯 <b>سؤال [{q['category']}]</b>\n\n❓ {q['question']}",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)


async def hack_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    tname = "مجهول"
    if msg.reply_to_message and msg.reply_to_message.from_user:
        tname = msg.reply_to_message.from_user.first_name
    elif ctx.args:
        tname = " ".join(ctx.args).lstrip('@')

    secrets = [
        f"🍕 يطلب بيتزا الساعة 3 صباحاً ولا يعترف",
        f"😴 ينام 14 ساعة ويقول 'تعبت'",
        f"📱 ينظر للهاتف كل 30 ثانية",
        f"🎮 يلعب بعد ما يقول 'راح أنام'",
        f"🔇 يشيل الصوت لما حد يكلمه",
        f"🍔 يطلب كبير ويأكل نص",
        f"💸 يشوف السعر ويقول 'غالي' وهو يشتريه",
        f"📺 يقول 'حلقة وحدة' ويكمل الموسم كله",
        f"🤫 يحفظ أسرار الكل لكن لا يكشف أسراره",
        f"☕ لو ما شرب قهوة الصبح يصير خطير",
    ]
    chosen = random.sample(secrets, 3)
    txt = (f"💻 <b>اختراق {tname}...</b>\n\n"
           "⚡ الاتصال بالخادم السري...\n"
           "🔓 تجاوز 7 جدران نارية...\n"
           "🕵️ فحص الملفات الشخصية...\n\n"
           f"🎯 <b>النتائج السرية:</b>\n" +
           "\n".join(f"• {s}" for s in chosen) +
           "\n\n<i>⚠️ هذا الكلام للضحك فقط 😄</i>")
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def judgment_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_judgment(update.message, update.effective_chat.id)


async def _send_judgment(msg, cid):
    members = db.top(cid, 20)
    names = [m.get('full_name', 'عضو') for m in members] if len(members) >= 2 else \
            ["المشترك الأول", "المشترك الثاني", "المشترك الثالث"]
    ids = [m.get('user_id', i + 1) for i, m in enumerate(members)] if len(members) >= 2 else [1, 2]

    if len(names) < 2:
        names = ["المشترك الأول", "المشترك الثاني"]
        ids = [1, 2]

    p1, p2 = random.sample(list(zip(names, ids)), 2)
    n1, id1 = p1
    n2, id2 = p2
    n1, n2 = n1[:20], n2[:20]

    qs = ["من الأذكى؟", "من الأكثر مرحاً؟", "من يطبخ أحسن؟", "من الأكثر كسلاً؟ 😄",
          "من يستحق جائزة نوبل؟", "من سيصبح مشهوراً؟", "من القيادي أكثر؟",
          "من صاحب القلب الكبير؟", "من الأكثر دراماً؟ 😂"]
    q = random.choice(qs)

    kb = [
        [InlineKeyboardButton(f"🔵 {n1}", callback_data=f"vote_1_{id1}"),
         InlineKeyboardButton(f"🔴 {n2}", callback_data=f"vote_2_{id2}")],
        [InlineKeyboardButton("🔀 لاعبون جدد", callback_data=f"new_judgment_{cid}"),
         InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]
    ]
    await msg.reply_text(
        f"⚖️ <b>لعبة الأحكام!</b>\n\n🎯 {q}\n\n🔵 <b>{n1}</b>\n🔴 <b>{n2}</b>\n\nصوّت! 👇",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)


async def ship_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    u1_name, u2_name = None, None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        u1_name = msg.reply_to_message.from_user.first_name
        u2_name = update.effective_user.first_name
    elif ctx.args and len(ctx.args) >= 2:
        u1_name = ctx.args[0].lstrip('@')
        u2_name = ctx.args[1].lstrip('@')
    elif ctx.args and len(ctx.args) == 1:
        u1_name = ctx.args[0].lstrip('@')
        u2_name = update.effective_user.first_name
    else:
        u1_name = update.effective_user.first_name
        u2_name = "شادي 🤖"

    pct = random.randint(10, 100)
    if pct >= 90:
        emoji = "💑 مثالييييين!"
        desc = "أحبكم في بعض! هذا ولع حقيقي 🔥"
    elif pct >= 70:
        emoji = "❤️ محبة قوية!"
        desc = "توافق ممتاز، الله يتمم بالخير! 💍"
    elif pct >= 50:
        emoji = "💙 لطيفين!"
        desc = "في أمل، بس محتاجين شوية شغل 😅"
    elif pct >= 30:
        emoji = "💛 أصدقاء!"
        desc = "الصداقة أجمل، اكتفوا بيها 😂"
    else:
        emoji = "💔 لا يا ناس!"
        desc = "الله يهداكم، مش مع بعض 😂"

    bar = "❤️" * (pct // 10) + "🖤" * (10 - pct // 10)
    await msg.reply_text(
        f"💘 <b>قياس التوافق</b>\n\n"
        f"👤 {u1_name}  +  👤 {u2_name}\n\n"
        f"{bar}\n\n"
        f"💯 النسبة: <b>{pct}%</b> {emoji}\n"
        f"📝 {desc}",
        parse_mode=ParseMode.HTML
    )


async def eightball_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    answers = [
        "🎱 نعم بالتأكيد!", "🎱 بالتأكيد لا!", "🎱 ربما...",
        "🎱 الأمور تبدو جيدة!", "🎱 لا تعتمد على ذلك!",
        "🎱 توقعاتي تقول نعم!", "🎱 من المشكوك فيه جداً!",
        "🎱 نعم!", "🎱 أجابتي لا.", "🎱 العلامات تشير للنعم!",
        "🎱 لا أستطيع التنبؤ الآن.", "🎱 ركّز واسأل مرة أخرى!",
        "🎱 اسأل لاحقاً.", "🎱 أفضل عدم الإجابة!",
        "🎱 المصادر تقول لا.", "🎱 النظرة غير واعدة."
    ]
    q = " ".join(ctx.args) if ctx.args else "سؤالك"
    await update.message.reply_text(
        f"🎱 <b>سؤالك:</b> {q}\n\n{random.choice(answers)}",
        parse_mode=ParseMode.HTML
    )


async def fortune_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(FORTUNE), parse_mode=ParseMode.MARKDOWN)


async def joke_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(JOKES))


async def roast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        tname = msg.reply_to_message.from_user.first_name
    elif ctx.args:
        tname = " ".join(ctx.args).lstrip('@')
    else:
        tname = update.effective_user.first_name
    await msg.reply_text(f"😂 <b>{tname}</b>، {random.choice(ROASTS)}", parse_mode=ParseMode.HTML)


async def compliment_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        tname = msg.reply_to_message.from_user.first_name
    elif ctx.args:
        tname = " ".join(ctx.args).lstrip('@')
    else:
        tname = update.effective_user.first_name
    await msg.reply_text(f"🌟 <b>{tname}</b>، {random.choice(COMPLIMENTS)}", parse_mode=ParseMode.HTML)


async def wisdom_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(WISDOM), parse_mode=ParseMode.MARKDOWN)


async def whisper_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        return await update.message.reply_text("❌ الاستخدام:\n/whisper @username رسالتك")
    sender = update.effective_user
    cid = update.effective_chat.id
    try:
        target = await ctx.bot.get_chat(ctx.args[0])
        tid = target.id
        tname = target.full_name
    except:
        return await update.message.reply_text("❌ لم يتم العثور على المستخدم!")
    msg_text = " ".join(ctx.args[1:])
    wid = db.save_whisper(sender.id, sender.full_name, tid, tname, msg_text, cid)
    kb = [[InlineKeyboardButton(f"🔐 فتح الهمسة ({tname})", callback_data=f"open_whisper_{wid}_{tid}")]]
    await update.message.reply_text(
        f"💌 <b>همسة سرية</b> من <b>{sender.full_name}</b> إلى <b>{tname}</b>\n"
        f"<i>فقط {tname} يمكنه فتحها 🔒</i>",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
    )


async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    cid = update.effective_chat.id
    db.upsert_member(u.id, cid, u.username, u.full_name)
    s = db.member(u.id, cid)
    if not s:
        return await update.message.reply_text("❌ لا توجد إحصائيات بعد!")
    await update.message.reply_text(_stats_text(u.first_name, s), parse_mode=ParseMode.HTML)


def _stats_text(name, s):
    pts = s['points']
    lvl = s['level']
    coins = s.get('coins', 0)
    thresholds = [0, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
    nt = thresholds[min(lvl, len(thresholds) - 1)]
    prog = min(10, int((pts / max(nt, 1)) * 10)) if nt > 0 else 10
    bar = "█" * prog + "░" * (10 - prog)
    return (f"📊 <b>إحصائيات {name}</b>\n\n"
            f"🎖️ المستوى: <b>{lvl}</b>\n"
            f"⭐ النقاط: <b>{pts}</b>\n"
            f"💰 العملات: <b>{coins}</b>\n"
            f"💬 الرسائل: <b>{s['messages_count']}</b>\n"
            f"⚠️ التحذيرات: <b>{s['warnings']}</b>\n\n"
            f"التقدم: [{bar}]")


async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    members = db.top(cid, 10)
    if not members:
        return await update.message.reply_text("❌ لا توجد بيانات بعد!")
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    txt = "🏆 <b>أكثر الأعضاء نشاطاً</b>\n\n"
    for i, m in enumerate(members):
        txt += f"{medals[i]} <b>{m.get('full_name','مجهول')[:18]}</b> — ⭐ {m.get('points',0)} | 💰 {m.get('coins',0)}\n"
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def daily_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    cid = update.effective_chat.id
    db.upsert_member(u.id, cid, u.username, u.full_name)
    ok, reward = db.claim_daily(u.id, cid)
    if ok:
        await update.message.reply_text(
            f"🎁 <b>مكافأة يومية!</b>\n\n"
            f"حصلت على <b>{reward} نقطة + {reward} عملة</b> 💰\n"
            f"<i>عد غداً للمكافأة التالية!</i>",
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("⏰ جمعت مكافأتك اليوم! عد غداً 🌙")


async def wallet_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    cid = update.effective_chat.id
    db.upsert_member(u.id, cid, u.username, u.full_name)
    s = db.member(u.id, cid)
    if not s:
        return await update.message.reply_text("❌ لا يوجد محفظة!")
    await update.message.reply_text(
        f"💰 <b>محفظة {u.first_name}</b>\n\n"
        f"⭐ النقاط: <b>{s['points']}</b>\n"
        f"💰 العملات: <b>{s.get('coins', 0)}</b>\n"
        f"🎖️ المستوى: <b>{s['level']}</b>",
        parse_mode=ParseMode.HTML)


async def gift_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    cid = update.effective_chat.id
    if not ctx.args or len(ctx.args) < 2:
        return await update.message.reply_text("❌ الاستخدام:\n/gift @username كمية")
    try:
        amount = int(ctx.args[-1])
        assert amount > 0
    except:
        return await update.message.reply_text("❌ الكمية يجب أن تكون رقماً موجباً!")
    target, tname = await get_target(update, ctx)
    if not target:
        return await update.message.reply_text("❌ ردّ على رسالة الشخص أو اذكر اسمه!")
    db.upsert_member(u.id, cid, u.username, u.full_name)
    db.upsert_member(target.id, cid, getattr(target, 'username', None), tname)
    if db.transfer_coins(u.id, target.id, cid, amount):
        await update.message.reply_text(
            f"🎁 <b>{u.first_name}</b> أهدى <b>{tname}</b> — {amount} عملة 💰!",
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ رصيدك غير كافٍ!")


async def calc_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("❌ مثال: /calc 25 * 4 + 10")
    expr = " ".join(ctx.args)
    # نظّف التعبير
    clean = re.sub(r'[^0-9+\-*/().\s]', '', expr)
    try:
        result = eval(clean, {"__builtins__": {}}, {"math": math})
        await update.message.reply_text(f"🧮 <b>{expr}</b>\n= <code>{result}</code>", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("❌ معادلة غير صحيحة!")


async def dev_panel_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        return
    gs = db.global_stats()
    kb = [[InlineKeyboardButton("📊 إحصائيات", callback_data="dev_full_stats"),
           InlineKeyboardButton("📋 السجلات", callback_data="dev_all_logs")]]
    await update.message.reply_text(
        f"🔧 <b>لوحة المطور</b>\n\n"
        f"👥 {gs['total_users']} مستخدم | 🏘️ {gs['total_groups']} مجموعة\n"
        f"⚡ {gs['total_actions']} عملية | 💬 {gs['total_messages']} رسالة\n"
        f"💌 {gs['total_whispers']} همسة",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML
    )


# ═══════════════════════════════════════════
#        معالج الأعضاء الجدد والمغادرين
# ═══════════════════════════════════════════

async def member_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return
    cid = result.chat.id
    member = result.new_chat_member
    user = member.user
    s = db.settings(cid)

    if member.status in ["member", "administrator", "creator"]:
        db.upsert_member(user.id, cid, user.username, user.full_name)
        if s.get('welcome_enabled', 1):
            welcomes = [
                f"🎉 أهلاً وسهلاً بـ <b>{user.first_name}</b>! يسعدنا وجودك معنا 💙",
                f"🌟 <b>{user.first_name}</b> انضم للعائلة! مرحباً بك 🤗",
                f"👋 يا هلا بـ <b>{user.first_name}</b>! نورت المجموعة ✨",
                f"🎊 <b>{user.first_name}</b> وصل! المجموعة زادت بهاءً 🌙",
            ]
            try:
                await ctx.bot.send_message(
                    cid,
                    random.choice(welcomes) + "\n\n💡 اكتب /help لمعرفة الأوامر!",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass

    elif member.status in ["left", "kicked", "banned"]:
        farewell = [
            f"👋 وداعاً <b>{user.first_name}</b>! نتمنى لك التوفيق 🌟",
            f"😢 <b>{user.first_name}</b> غادر، نفتقدك!",
            f"💔 <b>{user.first_name}</b> تركنا. يا خسارة!",
        ]
        try:
            await ctx.bot.send_message(cid, random.choice(farewell), parse_mode=ParseMode.HTML)
        except:
            pass


# ═══════════════════════════════════════════
#        معالج الرسائل الذكي الشامل
# ═══════════════════════════════════════════

# تتبع آخر رد في كل مجموعة لتجنب الإزعاج
_last_reply: dict = {}  # cid -> timestamp


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    u = update.effective_user
    chat = update.effective_chat
    msg = update.message
    text = msg.text or msg.caption or ""

    if u.is_bot:
        return

    # تسجيل الأعضاء والنشاط
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        db.upsert_member(u.id, chat.id, u.username, u.full_name)
        db.add_activity(u.id, chat.id)
        db.log_message(chat.id, u.id, u.first_name, text)

    if not text:
        return

    # ردود تلقائية (المشرفين أو إعدادات المجموعة)
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        auto = db.get_response(chat.id, text)
        if auto:
            return await msg.reply_text(auto)

    # ── تحقق من الكلمات المحرّكة ───────────────────

    mentioned = name_mentioned(text)
    greeting = is_greeting(text)
    farewell_msg = is_farewell(text)
    thanks = is_thanks(text)
    question = is_question(text)
    complaint = is_complaint(text)
    love = is_love(text)
    text_lower = text.lower()

    # في الخاص: دائماً يرد
    in_private = chat.type == ChatType.PRIVATE

    # في المجموعة: يرد إذا ذُكر الاسم أو بشكل عشوائي
    now = datetime.datetime.now().timestamp()
    last = _last_reply.get(chat.id, 0)
    cooldown = 8  # ثوانٍ بين الردود العشوائية
    can_random = (now - last) > cooldown

    # ── منطق الرد ─────────────────────────────────

    reply = None

    # إذا ذُكر الاسم صراحةً
    if mentioned or in_private:
        if greeting or in_private and greeting:
            reply = random.choice(SHADY_GREET_REPLIES)
        elif thanks:
            reply = random.choice(SHADY_THANKS_REPLIES)
        elif love:
            reply = random.choice(["💙 وأنا بحبك أكثر!", "❤️ الله يخليك!", "😊 أنا سعيد!"])
        elif complaint:
            reply = random.choice(SYMPATHY)
        elif question:
            # محاولة الإجابة على أسئلة بسيطة
            if any(w in text_lower for w in ["وقت", "ساعة", "التاريخ", "اليوم"]):
                now_dt = datetime.datetime.now()
                reply = f"🕐 الوقت الآن: <b>{now_dt.strftime('%H:%M')}</b>\n📅 التاريخ: <b>{now_dt.strftime('%Y-%m-%d')}</b>"
            elif any(w in text_lower for w in ["من أنت", "مين انت", "مين أنت", "ايش انت"]):
                reply = "🤖 أنا <b>شادي</b>! بوت ذكي لإدارة المجموعات 💣\nاكتب /help لمعرفة كل أوامري!"
            elif any(w in text_lower for w in ["كم عمرك", "عمرك كم", "عندك كم"]):
                reply = "🤖 عمري يُحسب بالتحديثات! إصدار v4.0 🚀"
            elif any(w in text_lower for w in ["حلو", "كيف", "عامل ايه", "عامل إيه", "شلونك", "كيف حالك"]):
                reply = random.choice(["أنا بخير تمام! وانت؟ 😊", "ممتاز والحمد لله! كيفك أنت؟ 💙", "تمام جداً 🤖"])
            else:
                reply = random.choice(ANSWER_DONT_KNOW)

        # الكلمات الخاصة بأوامر شادي
        elif re.search(r'اختراق|hack', text_lower):
            ctx.args = []
            return await hack_cmd(update, ctx)
        elif re.search(r'سؤال|كويز|quiz', text_lower):
            return await _send_quiz(msg, chat.id)
        elif re.search(r'نكتة|نكت|ضحك', text_lower):
            return await msg.reply_text(random.choice(JOKES))
        elif re.search(r'حكمة|wisdom', text_lower):
            return await msg.reply_text(random.choice(WISDOM), parse_mode=ParseMode.MARKDOWN)
        elif re.search(r'حظ|fortune|برجي|برجك', text_lower):
            return await msg.reply_text(random.choice(FORTUNE), parse_mode=ParseMode.MARKDOWN)
        elif re.search(r'إحصائيات|احصائيات|نقاطي|stats', text_lower):
            db.upsert_member(u.id, chat.id, u.username, u.full_name)
            s = db.member(u.id, chat.id)
            if s:
                return await msg.reply_text(_stats_text(u.first_name, s), parse_mode=ParseMode.HTML)
        elif re.search(r'ترتيب|top|أكثر.*نشاط', text_lower):
            members = db.top(chat.id, 5)
            if members:
                medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
                txt = "🏆 <b>أكثر الأعضاء نشاطاً:</b>\n"
                for i, m in enumerate(members):
                    txt += f"{medals[i]} {m.get('full_name','?')[:15]} — ⭐{m.get('points',0)}\n"
                return await msg.reply_text(txt, parse_mode=ParseMode.HTML)
        elif re.search(r'مساعدة|help|الأوامر', text_lower):
            return await help_cmd(update, ctx)

        # إذا لم يُطابق شيء — رد عام
        if not reply:
            reply = random.choice(SHADY_GREET_REPLIES)

    # في المجموعات: ردود تلقائية بدون ذكر الاسم (بشكل ذكي)
    elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and can_random:
        if greeting:
            # رد على التحيات دائماً
            reply = random.choice([
                f"هلا {u.first_name}! 👋",
                f"وعليكم السلام {u.first_name} 😊",
                f"أهلاً {u.first_name}! 🌟",
            ])
            _last_reply[chat.id] = now
        elif farewell_msg:
            reply = random.choice([
                f"إلى اللقاء {u.first_name}! 👋",
                f"مع السلامة {u.first_name} 🌟",
            ])
            _last_reply[chat.id] = now
        elif thanks and random.random() < 0.7:
            reply = random.choice(["العفو! 😊", "بكل سرور! 💙"])
            _last_reply[chat.id] = now
        elif random.random() < 0.07:
            # رد عشوائي 7% من الرسائل
            reply = random.choice(RANDOM_COMMENTS)
            _last_reply[chat.id] = now

    # ── حماية من الروابط ──────────────────────────
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        admin = await is_admin(ctx.bot, chat.id, u.id)
        if not admin:
            s = db.settings(chat.id)
            if not s.get('links_allowed', 0):
                if re.search(r'https?://|t\.me/|www\.', text, re.IGNORECASE):
                    try:
                        await msg.delete()
                        w = db.add_warning(u.id, chat.id)
                        warn_m = await ctx.bot.send_message(
                            chat.id,
                            f"⛔ {u.mention_html()} الروابط ممنوعة! تحذير #{w}",
                            parse_mode=ParseMode.HTML)
                        await asyncio.sleep(10)
                        try:
                            await warn_m.delete()
                        except:
                            pass
                        return
                    except:
                        pass

    # ── إرسال الرد ────────────────────────────────
    if reply:
        if "<" in reply and ">" in reply:
            await msg.reply_text(reply, parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text(reply)


# ═══════════════════════════════════════════
#           معالج الأزرار المضمنة
# ═══════════════════════════════════════════

async def button_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    user = q.from_user
    cid = q.message.chat_id

    try:
        # ── قوائم رئيسية ──────────────────────────

        if data == "main_menu":
            kb = [
                [InlineKeyboardButton("📋 الأوامر", callback_data="help_menu"),
                 InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats")],
                [InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu"),
                 InlineKeyboardButton("🏆 الترتيب", callback_data="leaderboard")],
                [InlineKeyboardButton("💰 محفظتي", callback_data="my_wallet"),
                 InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_menu")],
            ]
            if user.id == DEVELOPER_ID:
                kb.append([InlineKeyboardButton("🔧 لوحة المطور", callback_data="dev_panel")])
            await q.edit_message_text("🤖 <b>بوت شادي v4.0 💣</b>",
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "help_menu":
            kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
            await q.edit_message_text(
                "📚 <b>الأوامر الرئيسية</b>\n\n"
                "🎮 /quiz /hack /judgment /ship /8ball\n"
                "😄 /joke /roast /compliment /fortune /wisdom\n"
                "💰 /daily /wallet /gift /stats /top\n"
                "🛡️ /ban /kick /mute /unmute /warn /promote\n"
                "⚙️ /settings /addresponse /responses\n"
                "💌 /whisper /all /calc",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "my_stats":
            db.upsert_member(user.id, cid, user.username, user.full_name)
            s = db.member(user.id, cid)
            kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
            txt = _stats_text(user.first_name, s) if s else "لا توجد إحصائيات بعد!"
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "my_wallet":
            db.upsert_member(user.id, cid, user.username, user.full_name)
            s = db.member(user.id, cid)
            kb = [[InlineKeyboardButton("🎁 مكافأة يومية", callback_data="claim_daily"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
            txt = (f"💰 <b>محفظة {user.first_name}</b>\n\n"
                   f"⭐ نقاط: <b>{s['points'] if s else 0}</b>\n"
                   f"💰 عملات: <b>{s.get('coins', 0) if s else 0}</b>\n"
                   f"🎖️ مستوى: <b>{s['level'] if s else 1}</b>\n\n"
                   "<i>اضغط 'مكافأة يومية' لجمع نقاطك اليومية!</i>")
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "claim_daily":
            db.upsert_member(user.id, cid, user.username, user.full_name)
            ok, reward = db.claim_daily(user.id, cid)
            if ok:
                await q.answer(f"🎁 حصلت على {reward} نقطة + {reward} عملة!", show_alert=True)
                s = db.member(user.id, cid)
                kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="my_wallet")]]
                await q.edit_message_text(
                    f"🎁 <b>مكافأة يومية!</b>\n+{reward} نقطة +{reward} عملة 💰\n\n"
                    + (_stats_text(user.first_name, s) if s else ""),
                    reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
            else:
                await q.answer("⏰ جمعت مكافأتك اليوم! عد غداً 🌙", show_alert=True)

        elif data == "leaderboard":
            members = db.top(cid, 10)
            medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
            txt = "🏆 <b>أكثر الأعضاء نشاطاً</b>\n\n"
            if members:
                for i, m in enumerate(members):
                    txt += f"{medals[i]} <b>{m.get('full_name','?')[:15]}</b> — ⭐{m.get('points',0)} 💰{m.get('coins',0)}\n"
            else:
                txt += "لا توجد بيانات بعد!"
            kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        # ── الألعاب ───────────────────────────────

        elif data == "games_menu":
            kb = [
                [InlineKeyboardButton("🎯 لعبة الأسئلة", callback_data="start_quiz"),
                 InlineKeyboardButton("💻 الاختراق", callback_data="start_hack")],
                [InlineKeyboardButton("⚖️ الأحكام", callback_data="start_judgment"),
                 InlineKeyboardButton("💘 التوافق", callback_data="start_ship")],
                [InlineKeyboardButton("🎱 الكرة الكهربائية", callback_data="start_8ball"),
                 InlineKeyboardButton("🔮 الحظ", callback_data="start_fortune")],
                [InlineKeyboardButton("😂 نكتة", callback_data="start_joke"),
                 InlineKeyboardButton("💡 حكمة", callback_data="start_wisdom")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]
            await q.edit_message_text("🎮 <b>قسم الألعاب والترفيه</b>\n\nاختر لعبة:",
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "start_quiz":
            qobj = db.random_question()
            if not qobj:
                await q.edit_message_text("❌ لا توجد أسئلة!")
                return
            options = json.loads(qobj['options'])
            random.shuffle(options)
            kb = [[InlineKeyboardButton(opt, callback_data=f"quiz_{'c' if opt == qobj['answer'] else 'w'}_{qobj['id']}")]
                  for opt in options]
            await q.edit_message_text(
                f"🎯 <b>[{qobj['category']}]</b>\n\n❓ {qobj['question']}",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "start_hack":
            secrets = random.sample([
                "🍕 يطلب بيتزا الساعة 3 صباحاً",
                "😴 ينام أكثر من 12 ساعة",
                "📱 ينظر للهاتف كل دقيقة",
                "🔇 يشيل الصوت دايماً",
                "💸 يقول 'غالي' ثم يشتريه",
                "📺 يقول 'حلقة وحدة' ويكمل الموسم",
            ], 3)
            kb = [[InlineKeyboardButton("🔁 اختراق آخر", callback_data="start_hack"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]]
            await q.edit_message_text(
                "💻 <b>اختراق عشوائي!</b>\n\n" + "\n".join(f"• {s}" for s in secrets) + "\n\n<i>😄 مجرد مزحة!</i>",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "start_judgment":
            await q.edit_message_text("⏳ جارٍ اختيار اللاعبين...")
            await _send_judgment(q.message, cid)

        elif data == "start_ship":
            pct = random.randint(10, 100)
            bar = "❤️" * (pct // 10) + "🖤" * (10 - pct // 10)
            kb = [[InlineKeyboardButton("🔁 جرب مرة أخرى", callback_data="start_ship"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]]
            await q.edit_message_text(
                f"💘 <b>قياس التوافق العشوائي!</b>\n\n{bar}\n💯 النسبة: <b>{pct}%</b>",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "start_8ball":
            answers = ["نعم! ✅", "لا! ❌", "ربما 🤔", "بالتأكيد! 💯", "مشكوك فيه 😅", "اسأل لاحقاً ⏰"]
            kb = [[InlineKeyboardButton("🎱 اسأل مجدداً", callback_data="start_8ball"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]]
            await q.edit_message_text(
                f"🎱 <b>الكرة الكهربائية</b>\n\n{random.choice(answers)}",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "start_fortune":
            kb = [[InlineKeyboardButton("🔮 حظ جديد", callback_data="start_fortune"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]]
            await q.edit_message_text(
                random.choice(FORTUNE),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

        elif data == "start_joke":
            kb = [[InlineKeyboardButton("😂 نكتة أخرى", callback_data="start_joke"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]]
            await q.edit_message_text(
                random.choice(JOKES),
                reply_markup=InlineKeyboardMarkup(kb))

        elif data == "start_wisdom":
            kb = [[InlineKeyboardButton("💡 حكمة جديدة", callback_data="start_wisdom"),
                   InlineKeyboardButton("🔙 رجوع", callback_data="games_menu")]]
            await q.edit_message_text(
                random.choice(WISDOM),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

        # ── الاختبار ──────────────────────────────

        elif data.startswith("quiz_c_"):
            db.add_points(user.id, cid, 5)
            await q.answer("✅ إجابة صحيحة! +5 نقاط 🎉", show_alert=True)
            kb = [[InlineKeyboardButton("🎯 سؤال آخر", callback_data="start_quiz")]]
            await q.edit_message_text(
                f"✅ <b>أحسنت {user.first_name}!</b> +5 نقاط",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data.startswith("quiz_w_"):
            await q.answer("❌ إجابة خاطئة! حاول مجدداً 😢", show_alert=True)
            kb = [[InlineKeyboardButton("🎯 سؤال آخر", callback_data="start_quiz")]]
            await q.edit_message_text(
                f"❌ <b>خطأ يا {user.first_name}!</b> جرب سؤالاً آخر.",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        # ── لعبة الأحكام ──────────────────────────

        elif data.startswith("vote_"):
            num = data.split("_")[1]
            await q.answer(f"✅ صوّتك سُجِّل للمشترك {'الأول 🔵' if num == '1' else 'الثاني 🔴'}!")

        elif data.startswith("new_judgment_"):
            tcid = int(data.split("_")[-1])
            await _send_judgment(q.message, tcid)

        # ── الهمسات ───────────────────────────────

        elif data.startswith("open_whisper_"):
            parts = data.split("_")
            wid, rid = int(parts[2]), int(parts[3])
            if user.id != rid:
                return await q.answer("🔒 هذه الهمسة ليست لك!", show_alert=True)
            w = db.get_whisper(wid)
            if not w:
                return await q.answer("❌ الهمسة غير موجودة!", show_alert=True)
            db.read_whisper(wid)
            await q.answer(f"💌 من {w['sender_name']}:\n{w['message']}", show_alert=True)

        # ── الإعدادات ─────────────────────────────

        elif data == "admin_menu":
            if not await is_admin(ctx.bot, cid, user.id):
                return await q.answer("⛔ للمشرفين فقط!", show_alert=True)
            s = db.settings(cid)
            kb = [
                [InlineKeyboardButton(f"🔗 روابط: {'✅' if s['links_allowed'] else '❌'}", callback_data=f"toggle_links_{cid}"),
                 InlineKeyboardButton(f"📸 وسائط: {'✅' if s['media_allowed'] else '❌'}", callback_data=f"toggle_media_{cid}")],
                [InlineKeyboardButton(f"🛡️ سبام: {'✅' if s['spam_protection'] else '❌'}", callback_data=f"toggle_spam_{cid}"),
                 InlineKeyboardButton(f"👋 ترحيب: {'✅' if s['welcome_enabled'] else '❌'}", callback_data=f"toggle_welcome_{cid}")],
                [InlineKeyboardButton("📋 السجلات", callback_data=f"view_logs_{cid}"),
                 InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]
            await q.edit_message_text("⚙️ <b>إعدادات المجموعة</b>",
                                      reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data.startswith("toggle_"):
            if not await is_admin(ctx.bot, cid, user.id):
                return await q.answer("⛔ غير مصرح!", show_alert=True)
            parts = data.split("_")
            setting_map = {"links": "links_allowed", "media": "media_allowed",
                           "spam": "spam_protection", "welcome": "welcome_enabled"}
            key_name = parts[1]
            tcid = int(parts[-1])
            if key_name not in setting_map:
                return
            setting_key = setting_map[key_name]
            s = db.settings(tcid)
            nv = 0 if s[setting_key] else 1
            db.set_setting(tcid, setting_key, nv)
            await q.answer(f"{'✅ تم التفعيل' if nv else '❌ تم التعطيل'}")
            # تحديث الأزرار
            s2 = db.settings(tcid)
            kb = [
                [InlineKeyboardButton(f"🔗 روابط: {'✅' if s2['links_allowed'] else '❌'}", callback_data=f"toggle_links_{tcid}"),
                 InlineKeyboardButton(f"📸 وسائط: {'✅' if s2['media_allowed'] else '❌'}", callback_data=f"toggle_media_{tcid}")],
                [InlineKeyboardButton(f"🛡️ سبام: {'✅' if s2['spam_protection'] else '❌'}", callback_data=f"toggle_spam_{tcid}"),
                 InlineKeyboardButton(f"👋 ترحيب: {'✅' if s2['welcome_enabled'] else '❌'}", callback_data=f"toggle_welcome_{tcid}")],
                [InlineKeyboardButton("📋 السجلات", callback_data=f"view_logs_{tcid}"),
                 InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]
            ]
            await q.edit_message_reply_markup(InlineKeyboardMarkup(kb))

        elif data.startswith("view_logs_"):
            if not await is_admin(ctx.bot, cid, user.id):
                return await q.answer("⛔ غير مصرح!", show_alert=True)
            tcid = int(data.split("_")[-1])
            logs = db.recent_logs(tcid, 10)
            if not logs:
                return await q.answer("لا توجد سجلات بعد!", show_alert=True)
            txt = "📋 <b>آخر العمليات:</b>\n\n" + \
                  "\n".join(f"• {lg['action']} — {lg['target_name']} [{lg['timestamp'][:16]}]" for lg in logs)
            kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_menu")]]
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        # ── لوحة المطور ───────────────────────────

        elif data == "dev_panel":
            if user.id != DEVELOPER_ID:
                return await q.answer("⛔ للمطور فقط!", show_alert=True)
            gs = db.global_stats()
            kb = [[InlineKeyboardButton("📊 إحصائيات", callback_data="dev_full_stats"),
                   InlineKeyboardButton("📋 سجلات", callback_data="dev_all_logs")],
                  [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]
            await q.edit_message_text(
                f"🔧 <b>لوحة المطور</b>\n\n"
                f"👥 {gs['total_users']} مستخدم\n🏘️ {gs['total_groups']} مجموعة\n"
                f"⚡ {gs['total_actions']} عملية\n💬 {gs['total_messages']} رسالة",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "dev_full_stats":
            if user.id != DEVELOPER_ID:
                return await q.answer("⛔!", show_alert=True)
            gs = db.global_stats()
            kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="dev_panel")]]
            await q.edit_message_text(
                f"📊 <b>إحصائيات كاملة</b>\n\n"
                f"👥 مستخدمون: {gs['total_users']}\n🏘️ مجموعات: {gs['total_groups']}\n"
                f"💬 رسائل: {gs['total_messages']}\n⚡ عمليات: {gs['total_actions']}\n"
                f"🔨 حظر: {gs['bans_count']} | 👢 طرد: {gs['kicks_count']} | ⚠️ تحذير: {gs['warns_count']}\n"
                f"💌 همسات: {gs['total_whispers']}",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "dev_all_logs":
            if user.id != DEVELOPER_ID:
                return await q.answer("⛔!", show_alert=True)
            logs = db.recent_logs(n=15)
            kb = [[InlineKeyboardButton("🔙 رجوع", callback_data="dev_panel")]]
            txt = "📋 <b>آخر السجلات</b>\n\n" + \
                  ("\n".join(f"• [{lg.get('chat_id',0)}] {lg['action']} — {lg['target_name']}" for lg in logs) if logs else "لا توجد سجلات")
            await q.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

        elif data == "close_menu":
            await q.delete_message()

        else:
            logger.warning(f"زر غير معروف: {data}")

    except TelegramError as e:
        logger.error(f"Telegram خطأ [{data}]: {e}")
    except Exception as e:
        logger.error(f"خطأ عام [{data}]: {e}", exc_info=True)


# ═══════════════════════════════════════════
#           معالج الأخطاء
# ═══════════════════════════════════════════

async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"❌ خطأ: {ctx.error}", exc_info=ctx.error)


# ═══════════════════════════════════════════
#           تشغيل البوت
# ═══════════════════════════════════════════

def main():
    logger.info("🚀 بوت شادي v4.0 - قنبلة الابتكار 💣")

    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر أساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("all", all_cmd))
    app.add_handler(CommandHandler("dev", dev_panel_cmd))

    # ألعاب وترفيه
    app.add_handler(CommandHandler("quiz", quiz_cmd))
    app.add_handler(CommandHandler("hack", hack_cmd))
    app.add_handler(CommandHandler("judgment", judgment_cmd))
    app.add_handler(CommandHandler("ship", ship_cmd))
    app.add_handler(CommandHandler("8ball", eightball_cmd))
    app.add_handler(CommandHandler("fortune", fortune_cmd))
    app.add_handler(CommandHandler("joke", joke_cmd))
    app.add_handler(CommandHandler("roast", roast_cmd))
    app.add_handler(CommandHandler("compliment", compliment_cmd))
    app.add_handler(CommandHandler("wisdom", wisdom_cmd))

    # اقتصاد
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("wallet", wallet_cmd))
    app.add_handler(CommandHandler("gift", gift_cmd))
    app.add_handler(CommandHandler("calc", calc_cmd))

    # إدارة
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("promote", promote_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("addresponse", addresponse_cmd))
    app.add_handler(CommandHandler("responses", responses_cmd))
    app.add_handler(CommandHandler("delresponse", delresponse_cmd))
    app.add_handler(CommandHandler("whisper", whisper_cmd))

    # أعضاء جدد/مغادرون
    app.add_handler(ChatMemberHandler(member_update, ChatMemberHandler.CHAT_MEMBER))

    # أزرار
    app.add_handler(CallbackQueryHandler(button_callback))

    # رسائل نصية (يجب أن يكون أخيراً)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.CAPTION & ~filters.COMMAND, handle_message))

    app.add_error_handler(error_handler)

    logger.info("✅ جميع الأوامر مسجلة")
    logger.info(f"👨‍💻 المطور: {DEVELOPER_ID}")
    logger.info("⚠️ عطّل Privacy Mode في @BotFather لاستقبال كل الرسائل")
    logger.info("🤖 البوت جاهز!")

    app.run_polling(
        allowed_updates=["message", "callback_query", "chat_member"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
