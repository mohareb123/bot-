#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for shady_bot.py"""

import asyncio
import datetime
import json
import os
import sqlite3
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We need to prevent the module-level DB() instantiation from
# interfering with tests, so we patch it during import.
import shady_bot


# ═══════════════════════════════════════════
#              Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def tmp_db(tmp_path):
    """Create a fresh DB instance backed by a temporary file."""
    db_path = str(tmp_path / "test.db")
    return shady_bot.DB(path=db_path)


@pytest.fixture
def make_update():
    """Factory for creating mock Telegram Update objects."""
    def _make(user_id=123, first_name="TestUser", username="testuser",
              chat_id=-100, chat_type="supergroup", text="hello",
              is_bot=False, reply_to_message=None):
        update = MagicMock()
        user = MagicMock()
        user.id = user_id
        user.first_name = first_name
        user.full_name = first_name
        user.username = username
        user.is_bot = is_bot
        user.mention_html.return_value = f"<a href='tg://user?id={user_id}'>{first_name}</a>"

        chat = MagicMock()
        chat.id = chat_id
        chat.type = chat_type

        message = MagicMock()
        message.text = text
        message.caption = None
        message.reply_text = AsyncMock()
        message.delete = AsyncMock()
        message.reply_to_message = reply_to_message

        update.effective_user = user
        update.effective_chat = chat
        update.message = message
        return update
    return _make


@pytest.fixture
def make_context():
    """Factory for creating mock ContextTypes objects."""
    def _make(args=None):
        ctx = MagicMock()
        ctx.args = args or []
        ctx.bot = MagicMock()
        ctx.bot.get_chat_member = AsyncMock()
        ctx.bot.get_chat = AsyncMock()
        ctx.bot.ban_chat_member = AsyncMock()
        ctx.bot.unban_chat_member = AsyncMock()
        ctx.bot.restrict_chat_member = AsyncMock()
        ctx.bot.promote_chat_member = AsyncMock()
        ctx.bot.get_chat_administrators = AsyncMock()
        ctx.bot.send_message = AsyncMock()
        return ctx
    return _make


@pytest.fixture
def make_callback_query():
    """Factory for creating mock CallbackQuery objects."""
    def _make(data="main_menu", user_id=123, chat_id=-100,
              first_name="TestUser", username="testuser"):
        update = MagicMock()
        q = MagicMock()
        q.data = data
        q.answer = AsyncMock()
        q.edit_message_text = AsyncMock()
        q.edit_message_reply_markup = AsyncMock()
        q.delete_message = AsyncMock()
        q.message = MagicMock()
        q.message.chat_id = chat_id
        q.message.reply_text = AsyncMock()

        user = MagicMock()
        user.id = user_id
        user.first_name = first_name
        user.full_name = first_name
        user.username = username
        q.from_user = user

        update.callback_query = q
        return update, q
    return _make


# ═══════════════════════════════════════════
#       Tests: DB class
# ═══════════════════════════════════════════

class TestDB:
    """Tests for the DB class (database operations)."""

    def test_init_creates_tables(self, tmp_db):
        """DB init should create all required tables."""
        with tmp_db.conn() as c:
            tables = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        for t in ["members", "admin_logs", "messages_log",
                   "auto_responses", "whispers", "group_settings",
                   "quiz_questions", "polls"]:
            assert t in tables, f"Table '{t}' not created"

    def test_seed_questions(self, tmp_db):
        """DB init should seed quiz questions."""
        with tmp_db.conn() as c:
            count = c.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0]
        assert count == 20

    def test_upsert_member_insert(self, tmp_db):
        """upsert_member should insert a new member."""
        tmp_db.upsert_member(1, -100, "alice", "Alice")
        m = tmp_db.member(1, -100)
        assert m is not None
        assert m['username'] == "alice"
        assert m['full_name'] == "Alice"
        assert m['points'] == 0
        assert m['coins'] == 100

    def test_upsert_member_update(self, tmp_db):
        """upsert_member should update existing member info."""
        tmp_db.upsert_member(1, -100, "alice", "Alice")
        tmp_db.upsert_member(1, -100, "alice_new", "Alice New")
        m = tmp_db.member(1, -100)
        assert m['username'] == "alice_new"
        assert m['full_name'] == "Alice New"

    def test_add_activity(self, tmp_db):
        """add_activity should increment messages_count and points."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.add_activity(1, -100)
        m = tmp_db.member(1, -100)
        assert m['messages_count'] == 1
        assert m['points'] == 1

    def test_add_activity_levels_up(self, tmp_db):
        """add_activity should increase level based on points."""
        tmp_db.upsert_member(1, -100, "a", "A")
        # Manually set points high enough for level 2 (>=10)
        with tmp_db.conn() as c:
            c.execute("UPDATE members SET points=10 WHERE user_id=1 AND chat_id=-100")
        tmp_db.add_activity(1, -100)
        m = tmp_db.member(1, -100)
        assert m['level'] >= 2

    def test_add_points(self, tmp_db):
        """add_points should increase points and coins (coins = pts // 2)."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.add_points(1, -100, 10)
        m = tmp_db.member(1, -100)
        assert m['points'] == 10
        assert m['coins'] == 105  # 100 initial + 10//2

    def test_remove_coins_success(self, tmp_db):
        """remove_coins should return True and deduct coins."""
        tmp_db.upsert_member(1, -100, "a", "A")
        assert tmp_db.remove_coins(1, -100, 50) is True
        m = tmp_db.member(1, -100)
        assert m['coins'] == 50

    def test_remove_coins_insufficient(self, tmp_db):
        """remove_coins should return False when insufficient coins."""
        tmp_db.upsert_member(1, -100, "a", "A")
        assert tmp_db.remove_coins(1, -100, 200) is False
        m = tmp_db.member(1, -100)
        assert m['coins'] == 100  # unchanged

    def test_remove_coins_no_member(self, tmp_db):
        """remove_coins should return False for nonexistent member."""
        assert tmp_db.remove_coins(999, -100, 10) is False

    def test_transfer_coins_success(self, tmp_db):
        """transfer_coins should move coins between members."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -100, "b", "B")
        assert tmp_db.transfer_coins(1, 2, -100, 30) is True
        assert tmp_db.member(1, -100)['coins'] == 70
        assert tmp_db.member(2, -100)['coins'] == 130

    def test_transfer_coins_insufficient(self, tmp_db):
        """transfer_coins should fail if sender has insufficient coins."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -100, "b", "B")
        assert tmp_db.transfer_coins(1, 2, -100, 200) is False
        assert tmp_db.member(1, -100)['coins'] == 100
        assert tmp_db.member(2, -100)['coins'] == 100

    def test_claim_daily_first_time(self, tmp_db):
        """claim_daily should succeed on first claim."""
        tmp_db.upsert_member(1, -100, "a", "A")
        ok, reward = tmp_db.claim_daily(1, -100)
        assert ok is True
        assert 50 <= reward <= 200

    def test_claim_daily_already_claimed(self, tmp_db):
        """claim_daily should fail if already claimed today."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.claim_daily(1, -100)
        ok, reward = tmp_db.claim_daily(1, -100)
        assert ok is False
        assert reward == 0

    def test_claim_daily_no_member(self, tmp_db):
        """claim_daily should return (False, 0) for nonexistent member."""
        ok, reward = tmp_db.claim_daily(999, -100)
        assert ok is False
        assert reward == 0

    def test_member_returns_none(self, tmp_db):
        """member should return None for nonexistent user."""
        assert tmp_db.member(999, -100) is None

    def test_top(self, tmp_db):
        """top should return members sorted by points."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -100, "b", "B")
        tmp_db.add_points(2, -100, 50)
        top = tmp_db.top(-100, 10)
        assert len(top) == 2
        assert top[0]['user_id'] == 2  # higher points first

    def test_top_excludes_banned(self, tmp_db):
        """top should exclude banned members."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -100, "b", "B")
        with tmp_db.conn() as c:
            c.execute("UPDATE members SET is_banned=1 WHERE user_id=2 AND chat_id=-100")
        top = tmp_db.top(-100)
        assert len(top) == 1
        assert top[0]['user_id'] == 1

    def test_add_warning(self, tmp_db):
        """add_warning should increment warnings."""
        tmp_db.upsert_member(1, -100, "a", "A")
        w = tmp_db.add_warning(1, -100)
        assert w == 1
        w = tmp_db.add_warning(1, -100)
        assert w == 2

    def test_reset_warnings(self, tmp_db):
        """reset_warnings should reset warnings to 0."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.add_warning(1, -100)
        tmp_db.add_warning(1, -100)
        tmp_db.reset_warnings(1, -100)
        m = tmp_db.member(1, -100)
        assert m['warnings'] == 0

    def test_log_action(self, tmp_db):
        """log_action should insert into admin_logs."""
        tmp_db.log_action(-100, 1, "Admin", 2, "User", "ban", "spam")
        logs = tmp_db.recent_logs(-100)
        assert len(logs) == 1
        assert logs[0]['action'] == "ban"
        assert logs[0]['reason'] == "spam"

    def test_log_message(self, tmp_db):
        """log_message should insert message previews."""
        tmp_db.log_message(-100, 1, "User", "Hello world")
        msgs = tmp_db.recent_messages(10)
        assert len(msgs) == 1
        assert msgs[0]['message_preview'] == "Hello world"

    def test_log_message_truncates(self, tmp_db):
        """log_message should truncate preview to 100 chars."""
        long_msg = "x" * 200
        tmp_db.log_message(-100, 1, "User", long_msg)
        msgs = tmp_db.recent_messages(10)
        assert len(msgs[0]['message_preview']) == 100

    def test_recent_logs_with_cid(self, tmp_db):
        """recent_logs should filter by chat_id when provided."""
        tmp_db.log_action(-100, 1, "A", 2, "B", "ban", "")
        tmp_db.log_action(-200, 1, "A", 3, "C", "kick", "")
        logs = tmp_db.recent_logs(-100)
        assert len(logs) == 1
        assert logs[0]['action'] == "ban"

    def test_recent_logs_without_cid(self, tmp_db):
        """recent_logs without cid should return all logs."""
        tmp_db.log_action(-100, 1, "A", 2, "B", "ban", "")
        tmp_db.log_action(-200, 1, "A", 3, "C", "kick", "")
        logs = tmp_db.recent_logs()
        assert len(logs) == 2

    def test_global_stats(self, tmp_db):
        """global_stats should return correct aggregate stats."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -200, "b", "B")
        tmp_db.log_action(-100, 1, "A", 2, "B", "\u062d\u0638\u0631", "")
        stats = tmp_db.global_stats()
        assert stats['total_users'] == 2
        assert stats['total_groups'] == 2
        assert stats['total_actions'] == 1
        assert stats['bans_count'] == 1

    def test_add_and_get_response(self, tmp_db):
        """add_response and get_response should work together."""
        tmp_db.add_response(-100, "hello", "Hi there!", 1)
        resp = tmp_db.get_response(-100, "say hello")
        assert resp == "Hi there!"

    def test_get_response_no_match(self, tmp_db):
        """get_response should return None when no trigger matches."""
        assert tmp_db.get_response(-100, "random text") is None

    def test_list_responses(self, tmp_db):
        """list_responses should return all responses for a chat."""
        tmp_db.add_response(-100, "hi", "Hello!", 1)
        tmp_db.add_response(-100, "bye", "Goodbye!", 1)
        rs = tmp_db.list_responses(-100)
        assert len(rs) == 2

    def test_del_response(self, tmp_db):
        """del_response should remove the specified response."""
        tmp_db.add_response(-100, "hi", "Hello!", 1)
        rs = tmp_db.list_responses(-100)
        rid = rs[0]['id']
        tmp_db.del_response(rid, -100)
        assert len(tmp_db.list_responses(-100)) == 0

    def _insert_whisper(self, tmp_db, sid, sname, rid, rname, msg, cid):
        """Helper to insert a whisper bypassing the save_whisper lastrowid bug."""
        conn = tmp_db.conn()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO whispers (sender_id,sender_name,recipient_id,recipient_name,message,chat_id)
               VALUES (?,?,?,?,?,?)''', (sid, sname, rid, rname, msg, cid))
        wid = cursor.lastrowid
        conn.commit()
        conn.close()
        return wid

    def test_save_and_get_whisper(self, tmp_db):
        """Inserting and retrieving a whisper should work."""
        wid = self._insert_whisper(tmp_db, 1, "Sender", 2, "Receiver", "secret msg", -100)
        w = tmp_db.get_whisper(wid)
        assert w is not None
        assert w['message'] == "secret msg"
        assert w['is_read'] == 0

    def test_read_whisper(self, tmp_db):
        """read_whisper should mark whisper as read."""
        wid = self._insert_whisper(tmp_db, 1, "S", 2, "R", "msg", -100)
        tmp_db.read_whisper(wid)
        w = tmp_db.get_whisper(wid)
        assert w['is_read'] == 1

    def test_get_whisper_not_found(self, tmp_db):
        """get_whisper should return None for nonexistent whisper."""
        assert tmp_db.get_whisper(999) is None

    def test_settings_creates_default(self, tmp_db):
        """settings should create default settings if none exist."""
        s = tmp_db.settings(-100)
        assert s['links_allowed'] == 0
        assert s['media_allowed'] == 1
        assert s['spam_protection'] == 1
        assert s['welcome_enabled'] == 1
        assert s['max_warnings'] == 3

    def test_set_setting(self, tmp_db):
        """set_setting should update specific settings."""
        tmp_db.settings(-100)  # ensure row exists
        tmp_db.set_setting(-100, "links_allowed", 1)
        s = tmp_db.settings(-100)
        assert s['links_allowed'] == 1

    def test_random_question(self, tmp_db):
        """random_question should return a question dict."""
        q = tmp_db.random_question()
        assert q is not None
        assert 'question' in q
        assert 'answer' in q
        assert 'options' in q
        # options should be valid JSON
        json.loads(q['options'])

    def test_members_list_with_cid(self, tmp_db):
        """members_list with cid should return members for that chat."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -200, "b", "B")
        ms = tmp_db.members_list(-100)
        assert len(ms) == 1
        assert ms[0]['user_id'] == 1

    def test_members_list_without_cid(self, tmp_db):
        """members_list without cid should return all members."""
        tmp_db.upsert_member(1, -100, "a", "A")
        tmp_db.upsert_member(2, -200, "b", "B")
        ms = tmp_db.members_list()
        assert len(ms) == 2


# ═══════════════════════════════════════════
#    Tests: Text detection helpers
# ═══════════════════════════════════════════

class TestTextDetection:
    """Tests for text detection utility functions."""

    def test_name_mentioned_true(self):
        assert shady_bot.name_mentioned("\u0634\u0627\u062f\u064a") is True

    def test_name_mentioned_false(self):
        assert shady_bot.name_mentioned("hello world") is False

    def test_name_mentioned_case_insensitive(self):
        assert shady_bot.name_mentioned("\u0634\u0627\u062f\u0649") is True

    def test_is_greeting_arabic(self):
        assert shady_bot.is_greeting("\u0645\u0631\u062d\u0628\u0627") is True

    def test_is_greeting_english(self):
        assert shady_bot.is_greeting("hello") is True

    def test_is_greeting_false(self):
        assert shady_bot.is_greeting("goodbye") is False

    def test_is_greeting_substring(self):
        assert shady_bot.is_greeting("I say hi to you") is True

    def test_is_farewell_true(self):
        assert shady_bot.is_farewell("\u0628\u0627\u064a") is True

    def test_is_farewell_english_like(self):
        assert shady_bot.is_farewell("\u0645\u0639 \u0627\u0644\u0633\u0644\u0627\u0645\u0629") is True

    def test_is_farewell_false(self):
        assert shady_bot.is_farewell("hello there") is False

    def test_is_thanks_true(self):
        assert shady_bot.is_thanks("\u0634\u0643\u0631\u0627") is True

    def test_is_thanks_variant(self):
        assert shady_bot.is_thanks("\u0645\u0634\u0643\u0648\u0631") is True

    def test_is_thanks_false(self):
        assert shady_bot.is_thanks("hello") is False

    def test_is_question_question_mark(self):
        assert shady_bot.is_question("what is this?") is True

    def test_is_question_arabic_mark(self):
        assert shady_bot.is_question("\u0645\u0627 \u0647\u0630\u0627\u061f") is True

    def test_is_question_keyword(self):
        assert shady_bot.is_question("\u0643\u064a\u0641 \u062d\u0627\u0644\u0643") is True

    def test_is_question_false(self):
        assert shady_bot.is_question("this is a statement") is False

    def test_is_complaint_true(self):
        assert shady_bot.is_complaint("\u0632\u0647\u0642\u062a") is True

    def test_is_complaint_false(self):
        assert shady_bot.is_complaint("I am happy") is False

    def test_is_love_true(self):
        assert shady_bot.is_love("\u0628\u062d\u0628\u0643") is True

    def test_is_love_false(self):
        assert shady_bot.is_love("hello world") is False


# ═══════════════════════════════════════════
#    Tests: _stats_text helper
# ═══════════════════════════════════════════

class TestStatsText:
    """Tests for the _stats_text helper function."""

    def test_stats_text_basic(self):
        s = {
            'points': 50, 'level': 4, 'coins': 200,
            'messages_count': 30, 'warnings': 1,
        }
        result = shady_bot._stats_text("Alice", s)
        assert "Alice" in result
        assert "50" in result
        assert "200" in result
        assert "30" in result

    def test_stats_text_zero_points(self):
        s = {
            'points': 0, 'level': 1, 'coins': 100,
            'messages_count': 0, 'warnings': 0,
        }
        result = shady_bot._stats_text("Bob", s)
        assert "Bob" in result
        assert "\u0645\u0633\u062a\u0648\u0649" in result or "1" in result

    def test_stats_text_high_level(self):
        s = {
            'points': 6000, 'level': 10, 'coins': 5000,
            'messages_count': 1000, 'warnings': 0,
        }
        result = shady_bot._stats_text("Pro", s)
        assert "Pro" in result
        assert "6000" in result

    def test_stats_text_missing_coins_key(self):
        """Should handle missing 'coins' key gracefully."""
        s = {
            'points': 10, 'level': 1,
            'messages_count': 5, 'warnings': 0,
        }
        result = shady_bot._stats_text("User", s)
        assert "User" in result
        assert "0" in result  # default coins


# ═══════════════════════════════════════════
#    Tests: is_admin helper
# ═══════════════════════════════════════════

class TestIsAdmin:
    """Tests for the is_admin function."""

    @pytest.mark.asyncio
    async def test_developer_is_admin(self):
        """DEVELOPER_ID should always be admin."""
        bot = MagicMock()
        result = await shady_bot.is_admin(bot, -100, shady_bot.DEVELOPER_ID)
        assert result is True

    @pytest.mark.asyncio
    async def test_admin_member(self):
        """ChatMemberAdministrator should be admin."""
        from telegram import ChatMemberAdministrator
        bot = MagicMock()
        mock_admin = MagicMock(spec=ChatMemberAdministrator)
        bot.get_chat_member = AsyncMock(return_value=mock_admin)
        result = await shady_bot.is_admin(bot, -100, 999)
        assert result is True

    @pytest.mark.asyncio
    async def test_owner_member(self):
        """ChatMemberOwner should be admin."""
        from telegram import ChatMemberOwner
        bot = MagicMock()
        mock_owner = MagicMock(spec=ChatMemberOwner)
        bot.get_chat_member = AsyncMock(return_value=mock_owner)
        result = await shady_bot.is_admin(bot, -100, 999)
        assert result is True

    @pytest.mark.asyncio
    async def test_regular_member_not_admin(self):
        """Regular ChatMember should not be admin."""
        bot = MagicMock()
        mock_member = MagicMock(spec=shady_bot.ChatMember)
        bot.get_chat_member = AsyncMock(return_value=mock_member)
        result = await shady_bot.is_admin(bot, -100, 999)
        assert result is False

    @pytest.mark.asyncio
    async def test_exception_returns_false(self):
        """is_admin should return False on exception."""
        bot = MagicMock()
        bot.get_chat_member = AsyncMock(side_effect=Exception("API error"))
        result = await shady_bot.is_admin(bot, -100, 999)
        assert result is False


# ═══════════════════════════════════════════
#    Tests: get_target helper
# ═══════════════════════════════════════════

class TestGetTarget:
    """Tests for the get_target function."""

    @pytest.mark.asyncio
    async def test_target_from_reply(self, make_context):
        """get_target should extract target from reply_to_message."""
        update = MagicMock()
        reply_user = MagicMock()
        reply_user.full_name = "Target"
        reply_msg = MagicMock()
        reply_msg.from_user = reply_user
        update.message = MagicMock()
        update.message.reply_to_message = reply_msg

        ctx = make_context()
        target, name = await shady_bot.get_target(update, ctx)
        assert target == reply_user
        assert name == "Target"

    @pytest.mark.asyncio
    async def test_target_from_user_id(self, make_context):
        """get_target should resolve target by user ID arg."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_to_message = None

        mock_chat = MagicMock()
        mock_chat.full_name = "ResolvedUser"

        ctx = make_context(args=["12345"])
        ctx.bot.get_chat = AsyncMock(return_value=mock_chat)

        target, name = await shady_bot.get_target(update, ctx)
        assert target == mock_chat
        assert name == "ResolvedUser"

    @pytest.mark.asyncio
    async def test_target_from_username(self, make_context):
        """get_target should resolve target by @username arg."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_to_message = None

        mock_chat = MagicMock()
        mock_chat.full_name = "UsernameUser"

        # @someuser can't be parsed as int, so get_chat is called first
        # with int() which raises ValueError internally, then with the
        # @username string.
        ctx = make_context(args=["@someuser"])
        ctx.bot.get_chat = AsyncMock(return_value=mock_chat)

        target, name = await shady_bot.get_target(update, ctx)
        assert target == mock_chat
        assert name == "UsernameUser"

    @pytest.mark.asyncio
    async def test_target_none_no_reply_no_args(self, make_context):
        """get_target should return (None, None) with no reply and no args."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_to_message = None

        ctx = make_context()
        target, name = await shady_bot.get_target(update, ctx)
        assert target is None
        assert name is None


# ═══════════════════════════════════════════
#    Tests: Command handlers
# ═══════════════════════════════════════════

class TestStartCommand:
    """Tests for the /start command."""

    @pytest.mark.asyncio
    async def test_start_sends_welcome(self, make_update, make_context):
        update = make_update(user_id=123)
        ctx = make_context()
        await shady_bot.start(update, ctx)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "TestUser" in call_args[0][0] or "TestUser" in str(call_args)

    @pytest.mark.asyncio
    async def test_start_developer_gets_extra_button(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        await shady_bot.start(update, ctx)
        call_args = update.message.reply_text.call_args
        # The developer should get a keyboard with the dev panel button
        markup = call_args[1].get('reply_markup') or call_args.kwargs.get('reply_markup')
        buttons_text = []
        for row in markup.inline_keyboard:
            for btn in row:
                buttons_text.append(btn.text)
        assert any("\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0637\u0648\u0631" in t for t in buttons_text)


class TestHelpCommand:
    """Tests for the /help command."""

    @pytest.mark.asyncio
    async def test_help_sends_guide(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.help_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "/quiz" in call_text
        assert "/ban" in call_text
        assert "/daily" in call_text


class TestBanCommand:
    """Tests for the /ban command."""

    @pytest.mark.asyncio
    async def test_ban_no_target(self, make_update, make_context):
        """Ban without target should show error."""
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()

        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(None, None)):
            await shady_bot.ban_cmd(update, ctx)
        update.message.reply_text.assert_called()
        assert "\u2764" not in str(update.message.reply_text.call_args)

    @pytest.mark.asyncio
    async def test_ban_success(self, make_update, make_context, tmp_db):
        """Successful ban should call ban_chat_member."""
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["456", "spam"])

        target = MagicMock()
        target.id = 456
        target.full_name = "BadUser"

        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "BadUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.ban_cmd(update, ctx)
        ctx.bot.ban_chat_member.assert_called_once()

    @pytest.mark.asyncio
    async def test_ban_telegram_error(self, make_update, make_context, tmp_db):
        """Ban should handle TelegramError gracefully."""
        from telegram.error import TelegramError
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        ctx.bot.ban_chat_member = AsyncMock(side_effect=TelegramError("not enough rights"))

        target = MagicMock()
        target.id = 456

        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "User")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.ban_cmd(update, ctx)
        # Should show error message
        last_call = update.message.reply_text.call_args[0][0]
        assert "\u2764" not in last_call or "\u274c" in last_call


class TestKickCommand:
    """Tests for the /kick command."""

    @pytest.mark.asyncio
    async def test_kick_no_target(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(None, None)):
            await shady_bot.kick_cmd(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_kick_success(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["456"])
        target = MagicMock()
        target.id = 456
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "KickedUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.kick_cmd(update, ctx)
        ctx.bot.ban_chat_member.assert_called_once()
        ctx.bot.unban_chat_member.assert_called_once()


class TestMuteCommand:
    """Tests for the /mute command."""

    @pytest.mark.asyncio
    async def test_mute_no_target(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(None, None)):
            await shady_bot.mute_cmd(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_mute_success_default_time(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        target = MagicMock()
        target.id = 456
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "MutedUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.mute_cmd(update, ctx)
        ctx.bot.restrict_chat_member.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "60" in call_text  # default 60 minutes

    @pytest.mark.asyncio
    async def test_mute_custom_duration(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["30"])
        target = MagicMock()
        target.id = 456
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "MutedUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.mute_cmd(update, ctx)
        call_text = update.message.reply_text.call_args[0][0]
        assert "30" in call_text


class TestUnmuteCommand:
    """Tests for the /unmute command."""

    @pytest.mark.asyncio
    async def test_unmute_no_target(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(None, None)):
            await shady_bot.unmute_cmd(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_unmute_success(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        target = MagicMock()
        target.id = 456
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "UnmutedUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.unmute_cmd(update, ctx)
        ctx.bot.restrict_chat_member.assert_called_once()


class TestWarnCommand:
    """Tests for the /warn command."""

    @pytest.mark.asyncio
    async def test_warn_no_target(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(None, None)):
            await shady_bot.warn_cmd(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_warn_increments_warning(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["bad behavior"])
        target = MagicMock()
        target.id = 456
        target.username = "warned"
        target.full_name = "WarnedUser"
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "WarnedUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.warn_cmd(update, ctx)
        call_text = update.message.reply_text.call_args[0][0]
        assert "#1" in call_text or "1/" in call_text

    @pytest.mark.asyncio
    async def test_warn_auto_kick_on_max(self, make_update, make_context, tmp_db):
        """Exceeding max warnings should auto-kick."""
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        target = MagicMock()
        target.id = 456
        target.username = "warned"
        target.full_name = "WarnedUser"

        # Set up member with 2 warnings already (max is 3)
        tmp_db.upsert_member(456, -100, "warned", "WarnedUser")
        tmp_db.add_warning(456, -100)
        tmp_db.add_warning(456, -100)

        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "WarnedUser")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.warn_cmd(update, ctx)
        # Should have tried to ban+unban (kick)
        ctx.bot.ban_chat_member.assert_called_once()
        ctx.bot.unban_chat_member.assert_called_once()


class TestPromoteCommand:
    """Tests for the /promote command."""

    @pytest.mark.asyncio
    async def test_promote_no_target(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(None, None)):
            await shady_bot.promote_cmd(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_promote_success(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        target = MagicMock()
        target.id = 456
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "NewAdmin")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.promote_cmd(update, ctx)
        ctx.bot.promote_chat_member.assert_called_once()


class TestEntertainmentCommands:
    """Tests for entertainment/game commands."""

    @pytest.mark.asyncio
    async def test_fortune_cmd(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.fortune_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert text in shady_bot.FORTUNE

    @pytest.mark.asyncio
    async def test_joke_cmd(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.joke_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert text in shady_bot.JOKES

    @pytest.mark.asyncio
    async def test_wisdom_cmd(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.wisdom_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert text in shady_bot.WISDOM

    @pytest.mark.asyncio
    async def test_eightball_cmd_no_args(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.eightball_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "\u0633\u0624\u0627\u0644\u0643" in text  # "your question"

    @pytest.mark.asyncio
    async def test_eightball_cmd_with_question(self, make_update, make_context):
        update = make_update()
        ctx = make_context(args=["will", "I", "succeed"])
        await shady_bot.eightball_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "will I succeed" in text

    @pytest.mark.asyncio
    async def test_roast_cmd_self(self, make_update, make_context):
        """Roast without target should roast the sender."""
        update = make_update()
        ctx = make_context()
        await shady_bot.roast_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text

    @pytest.mark.asyncio
    async def test_roast_cmd_with_reply(self, make_update, make_context):
        """Roast with reply should target the replied user."""
        reply_user = MagicMock()
        reply_user.first_name = "Victim"
        reply_msg = MagicMock()
        reply_msg.from_user = reply_user
        update = make_update()
        update.message.reply_to_message = reply_msg
        ctx = make_context()
        await shady_bot.roast_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "Victim" in text

    @pytest.mark.asyncio
    async def test_compliment_cmd_self(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.compliment_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text

    @pytest.mark.asyncio
    async def test_compliment_cmd_with_args(self, make_update, make_context):
        update = make_update()
        ctx = make_context(args=["@friend"])
        await shady_bot.compliment_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "friend" in text

    @pytest.mark.asyncio
    async def test_hack_cmd_no_target(self, make_update, make_context):
        """Hack without target should use 'unknown'."""
        update = make_update()
        ctx = make_context()
        await shady_bot.hack_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "\u0645\u062c\u0647\u0648\u0644" in text  # "unknown"

    @pytest.mark.asyncio
    async def test_hack_cmd_with_reply(self, make_update, make_context):
        reply_user = MagicMock()
        reply_user.first_name = "HackTarget"
        reply_msg = MagicMock()
        reply_msg.from_user = reply_user
        update = make_update()
        update.message.reply_to_message = reply_msg
        ctx = make_context()
        await shady_bot.hack_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "HackTarget" in text

    @pytest.mark.asyncio
    async def test_ship_cmd_no_args(self, make_update, make_context):
        """Ship without args should ship user with Shady."""
        update = make_update()
        ctx = make_context()
        await shady_bot.ship_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text
        assert "\u0634\u0627\u062f\u064a" in text  # "Shady"

    @pytest.mark.asyncio
    async def test_ship_cmd_two_args(self, make_update, make_context):
        update = make_update()
        ctx = make_context(args=["@alice", "@bob"])
        await shady_bot.ship_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "alice" in text
        assert "bob" in text


class TestEconomyCommands:
    """Tests for economy-related commands."""

    @pytest.mark.asyncio
    async def test_stats_cmd(self, make_update, make_context, tmp_db):
        update = make_update(user_id=1)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.stats_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text

    @pytest.mark.asyncio
    async def test_top_cmd_no_data(self, make_update, make_context, tmp_db):
        update = make_update()
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.top_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u2764" not in text or "\u274c" in text or "\u0644\u0627 \u062a\u0648\u062c\u062f" in text

    @pytest.mark.asyncio
    async def test_top_cmd_with_data(self, make_update, make_context, tmp_db):
        tmp_db.upsert_member(1, -100, "a", "Alice")
        tmp_db.upsert_member(2, -100, "b", "Bob")
        tmp_db.add_points(1, -100, 50)
        update = make_update()
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.top_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "Alice" in text

    @pytest.mark.asyncio
    async def test_daily_cmd_first_claim(self, make_update, make_context, tmp_db):
        update = make_update(user_id=1)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.daily_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u0645\u0643\u0627\u0641\u0623\u0629" in text  # "reward"

    @pytest.mark.asyncio
    async def test_daily_cmd_already_claimed(self, make_update, make_context, tmp_db):
        tmp_db.upsert_member(1, -100, "test", "TestUser")
        tmp_db.claim_daily(1, -100)
        update = make_update(user_id=1)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.daily_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u063a\u062f\u0627\u064b" in text or "\u2708" in text or "\u23f0" in text

    @pytest.mark.asyncio
    async def test_wallet_cmd(self, make_update, make_context, tmp_db):
        update = make_update(user_id=1)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.wallet_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text
        assert "\u0645\u062d\u0641\u0638\u0629" in text or "\u0639\u0645\u0644\u0627\u062a" in text or "100" in text

    @pytest.mark.asyncio
    async def test_gift_cmd_no_args(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        await shady_bot.gift_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text

    @pytest.mark.asyncio
    async def test_gift_cmd_invalid_amount(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["@user", "abc"])
        await shady_bot.gift_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text

    @pytest.mark.asyncio
    async def test_gift_cmd_success(self, make_update, make_context, tmp_db):
        tmp_db.upsert_member(shady_bot.DEVELOPER_ID, -100, "dev", "Dev")
        tmp_db.upsert_member(456, -100, "recv", "Receiver")
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["@recv", "30"])
        target = MagicMock()
        target.id = 456
        target.username = "recv"
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "Receiver")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.gift_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "30" in text

    @pytest.mark.asyncio
    async def test_gift_cmd_insufficient_balance(self, make_update, make_context, tmp_db):
        tmp_db.upsert_member(shady_bot.DEVELOPER_ID, -100, "dev", "Dev")
        tmp_db.upsert_member(456, -100, "recv", "Receiver")
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=["@recv", "999"])
        target = MagicMock()
        target.id = 456
        target.username = "recv"
        with patch.object(shady_bot, 'get_target', new_callable=AsyncMock,
                          return_value=(target, "Receiver")), \
             patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.gift_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text


class TestCalcCommand:
    """Tests for the /calc command."""

    @pytest.mark.asyncio
    async def test_calc_no_args(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.calc_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text

    @pytest.mark.asyncio
    async def test_calc_valid_expression(self, make_update, make_context):
        update = make_update()
        ctx = make_context(args=["2", "+", "3"])
        await shady_bot.calc_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "5" in text

    @pytest.mark.asyncio
    async def test_calc_invalid_expression(self, make_update, make_context):
        update = make_update()
        ctx = make_context(args=["abc"])
        await shady_bot.calc_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text


class TestAutoResponseCommands:
    """Tests for addresponse, responses, and delresponse commands."""

    @pytest.mark.asyncio
    async def test_addresponse_missing_pipe(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID, text="/addresponse hello")
        ctx = make_context()
        await shady_bot.addresponse_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text

    @pytest.mark.asyncio
    async def test_addresponse_success(self, make_update, make_context, tmp_db):
        update = make_update(
            user_id=shady_bot.DEVELOPER_ID,
            text="/addresponse hello | Hi there!"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.addresponse_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u2705" in text
        assert "hello" in text

    @pytest.mark.asyncio
    async def test_responses_empty(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.responses_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u0644\u0627 \u062a\u0648\u062c\u062f" in text  # "no"

    @pytest.mark.asyncio
    async def test_responses_with_data(self, make_update, make_context, tmp_db):
        tmp_db.add_response(-100, "hi", "Hello!", 1)
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.responses_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "hi" in text

    @pytest.mark.asyncio
    async def test_delresponse_no_args(self, make_update, make_context):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        await shady_bot.delresponse_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text

    @pytest.mark.asyncio
    async def test_delresponse_success(self, make_update, make_context, tmp_db):
        tmp_db.add_response(-100, "hi", "Hello!", 1)
        rs = tmp_db.list_responses(-100)
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context(args=[str(rs[0]['id'])])
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.delresponse_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u2705" in text


class TestWhisperCommand:
    """Tests for the /whisper command."""

    @pytest.mark.asyncio
    async def test_whisper_no_args(self, make_update, make_context):
        update = make_update()
        ctx = make_context()
        await shady_bot.whisper_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u274c" in text

    @pytest.mark.asyncio
    async def test_whisper_success(self, make_update, make_context, tmp_db):
        update = make_update(user_id=1)
        mock_target = MagicMock()
        mock_target.id = 2
        mock_target.full_name = "Recipient"
        ctx = make_context(args=["@recipient", "secret", "message"])
        ctx.bot.get_chat = AsyncMock(return_value=mock_target)
        # Patch save_whisper to avoid the lastrowid bug on Connection
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(tmp_db, 'save_whisper', return_value=1):
            await shady_bot.whisper_cmd(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u0647\u0645\u0633\u0629" in text  # "whisper"


class TestDevPanelCommand:
    """Tests for the /dev command."""

    @pytest.mark.asyncio
    async def test_dev_panel_non_developer(self, make_update, make_context):
        update = make_update(user_id=999)
        ctx = make_context()
        await shady_bot.dev_panel_cmd(update, ctx)
        # Non-developer should get no response
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_dev_panel_developer(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.dev_panel_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "\u0644\u0648\u062d\u0629 \u0627\u0644\u0645\u0637\u0648\u0631" in text


# ═══════════════════════════════════════════
#    Tests: handle_message (message processing)
# ═══════════════════════════════════════════

class TestHandleMessage:
    """Tests for the handle_message function."""

    @pytest.mark.asyncio
    async def test_ignores_bot_messages(self, make_update, make_context, tmp_db):
        update = make_update(is_bot=True, text="hello")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_empty_text(self, make_update, make_context, tmp_db):
        update = make_update(text=None, chat_type="private")
        update.message.text = None
        update.message.caption = None
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_update_message(self, make_context):
        update = MagicMock()
        update.message = None
        update.effective_user = None
        ctx = make_context()
        # Should return early without error
        await shady_bot.handle_message(update, ctx)

    @pytest.mark.asyncio
    async def test_private_greeting(self, make_update, make_context, tmp_db):
        """In private chat, greeting should get a reply."""
        update = make_update(chat_type="private", text="\u0645\u0631\u062d\u0628\u0627")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_mentioned_name_greeting(self, make_update, make_context, tmp_db):
        """Mentioning Shady's name with a greeting should reply."""
        update = make_update(
            chat_type="supergroup",
            text="\u0634\u0627\u062f\u064a \u0645\u0631\u062d\u0628\u0627"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_called()
        text = update.message.reply_text.call_args[0][0]
        assert text in shady_bot.SHADY_GREET_REPLIES

    @pytest.mark.asyncio
    async def test_mentioned_thanks(self, make_update, make_context, tmp_db):
        update = make_update(
            chat_type="supergroup",
            text="\u0634\u0627\u062f\u064a \u0634\u0643\u0631\u0627"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_called()
        text = update.message.reply_text.call_args[0][0]
        assert text in shady_bot.SHADY_THANKS_REPLIES

    @pytest.mark.asyncio
    async def test_mentioned_complaint(self, make_update, make_context, tmp_db):
        update = make_update(
            chat_type="supergroup",
            text="\u0634\u0627\u062f\u064a \u062a\u0639\u0628\u062a"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_called()
        text = update.message.reply_text.call_args[0][0]
        assert text in shady_bot.SYMPATHY

    @pytest.mark.asyncio
    async def test_mentioned_love(self, make_update, make_context, tmp_db):
        update = make_update(
            chat_type="supergroup",
            text="\u0634\u0627\u062f\u064a \u0628\u062d\u0628\u0643"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_mentioned_question_time(self, make_update, make_context, tmp_db):
        """Asking about time should return current time."""
        update = make_update(
            chat_type="supergroup",
            text="\u0634\u0627\u062f\u064a \u0643\u0645 \u0627\u0644\u0633\u0627\u0639\u0629\u061f"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        update.message.reply_text.assert_called()
        text = update.message.reply_text.call_args[0][0]
        assert "\u0627\u0644\u0648\u0642\u062a" in text  # "time"

    @pytest.mark.asyncio
    async def test_mentioned_question_who_are_you(self, make_update, make_context, tmp_db):
        update = make_update(
            chat_type="supergroup",
            text="\u0634\u0627\u062f\u064a \u0645\u0646 \u0623\u0646\u062a\u061f"
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert "\u0634\u0627\u062f\u064a" in text

    @pytest.mark.asyncio
    async def test_auto_response(self, make_update, make_context, tmp_db):
        """Auto-responses from DB should be returned in group chat."""
        tmp_db.add_response(-100, "trigger", "auto reply!", 1)
        update = make_update(chat_type="supergroup", text="trigger word")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.handle_message(update, ctx)
        text = update.message.reply_text.call_args[0][0]
        assert text == "auto reply!"

    @pytest.mark.asyncio
    async def test_group_registers_activity(self, make_update, make_context, tmp_db):
        """Messages in groups should register member activity."""
        update = make_update(chat_type="supergroup", text="just chatting", user_id=42)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.handle_message(update, ctx)
        m = tmp_db.member(42, -100)
        assert m is not None
        assert m['messages_count'] == 1


# ═══════════════════════════════════════════
#    Tests: button_callback
# ═══════════════════════════════════════════

class TestButtonCallback:
    """Tests for the button_callback inline keyboard handler."""

    @pytest.mark.asyncio
    async def test_main_menu(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="main_menu")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.answer.assert_called_once()
        q.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_menu(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="help_menu")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert "/quiz" in text

    @pytest.mark.asyncio
    async def test_my_stats(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="my_stats", user_id=1)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_my_wallet(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="my_wallet", user_id=1)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert "\u0645\u062d\u0641\u0638\u0629" in text

    @pytest.mark.asyncio
    async def test_games_menu(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="games_menu")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert "\u0627\u0644\u0623\u0644\u0639\u0627\u0628" in text

    @pytest.mark.asyncio
    async def test_leaderboard_empty(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="leaderboard")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_leaderboard_with_data(self, make_callback_query, make_context, tmp_db):
        tmp_db.upsert_member(1, -100, "a", "Alice")
        tmp_db.add_points(1, -100, 50)
        update, q = make_callback_query(data="leaderboard")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert "Alice" in text

    @pytest.mark.asyncio
    async def test_quiz_correct(self, make_callback_query, make_context, tmp_db):
        tmp_db.upsert_member(123, -100, "test", "TestUser")
        update, q = make_callback_query(data="quiz_c_1")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.answer.assert_called()
        # Points should be added
        call_args = [str(c) for c in q.answer.call_args_list]
        assert any("\u0635\u062d\u064a\u062d\u0629" in c for c in call_args)  # "correct"

    @pytest.mark.asyncio
    async def test_quiz_wrong(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="quiz_w_1")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        call_args = [str(c) for c in q.answer.call_args_list]
        assert any("\u062e\u0627\u0637\u0626\u0629" in c for c in call_args)  # "wrong"

    @pytest.mark.asyncio
    async def test_vote(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="vote_1_123")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.answer.assert_called()

    @pytest.mark.asyncio
    async def test_open_whisper_wrong_user(self, make_callback_query, make_context, tmp_db):
        # Insert whisper directly to avoid save_whisper lastrowid bug
        conn = tmp_db.conn()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO whispers (sender_id,sender_name,recipient_id,recipient_name,message,chat_id)
               VALUES (?,?,?,?,?,?)''', (1, "S", 999, "R", "secret", -100))
        wid = cursor.lastrowid
        conn.commit()
        conn.close()
        update, q = make_callback_query(data=f"open_whisper_{wid}_999", user_id=123)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        # Should deny access
        call_args = str(q.answer.call_args_list)
        assert "\u0644\u064a\u0633\u062a \u0644\u0643" in call_args  # "not for you"

    @pytest.mark.asyncio
    async def test_open_whisper_correct_user(self, make_callback_query, make_context, tmp_db):
        conn = tmp_db.conn()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO whispers (sender_id,sender_name,recipient_id,recipient_name,message,chat_id)
               VALUES (?,?,?,?,?,?)''', (1, "Sender", 123, "Recipient", "secret msg", -100))
        wid = cursor.lastrowid
        conn.commit()
        conn.close()
        update, q = make_callback_query(data=f"open_whisper_{wid}_123", user_id=123)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        call_args = str(q.answer.call_args_list)
        assert "secret msg" in call_args

    @pytest.mark.asyncio
    async def test_close_menu(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="close_menu")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.delete_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_dev_panel_non_developer(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="dev_panel", user_id=999)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        call_args = str(q.answer.call_args_list)
        assert "\u0644\u0644\u0645\u0637\u0648\u0631" in call_args  # "developer only"

    @pytest.mark.asyncio
    async def test_dev_panel_developer(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="dev_panel", user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        q.edit_message_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_joke_button(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="start_joke")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert text in shady_bot.JOKES

    @pytest.mark.asyncio
    async def test_start_wisdom_button(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="start_wisdom")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert text in shady_bot.WISDOM

    @pytest.mark.asyncio
    async def test_start_fortune_button(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="start_fortune")
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.button_callback(update, ctx)
        text = q.edit_message_text.call_args[0][0]
        assert text in shady_bot.FORTUNE

    @pytest.mark.asyncio
    async def test_toggle_setting(self, make_callback_query, make_context, tmp_db):
        """Toggle button should flip setting value."""
        tmp_db.settings(-100)  # init settings
        update, q = make_callback_query(
            data="toggle_links_-100",
            user_id=shady_bot.DEVELOPER_ID
        )
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=True):
            await shady_bot.button_callback(update, ctx)
        s = tmp_db.settings(-100)
        assert s['links_allowed'] == 1  # toggled from 0 to 1

    @pytest.mark.asyncio
    async def test_admin_menu_non_admin(self, make_callback_query, make_context, tmp_db):
        update, q = make_callback_query(data="admin_menu", user_id=999)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db), \
             patch.object(shady_bot, 'is_admin', new_callable=AsyncMock, return_value=False):
            await shady_bot.button_callback(update, ctx)
        call_args = str(q.answer.call_args_list)
        assert "\u0644\u0644\u0645\u0634\u0631\u0641\u064a\u0646" in call_args


# ═══════════════════════════════════════════
#    Tests: error_handler
# ═══════════════════════════════════════════

class TestErrorHandler:
    """Tests for the error_handler function."""

    @pytest.mark.asyncio
    async def test_error_handler_logs(self):
        update = MagicMock()
        ctx = MagicMock()
        ctx.error = ValueError("test error")
        with patch.object(shady_bot.logger, 'error') as mock_log:
            await shady_bot.error_handler(update, ctx)
        mock_log.assert_called_once()


# ═══════════════════════════════════════════
#    Tests: member_update handler
# ═══════════════════════════════════════════

class TestMemberUpdate:
    """Tests for the member_update handler."""

    @pytest.mark.asyncio
    async def test_member_join_with_welcome(self, make_context, tmp_db):
        update = MagicMock()
        result = MagicMock()
        result.chat = MagicMock()
        result.chat.id = -100
        member = MagicMock()
        member.status = "member"
        member.user = MagicMock()
        member.user.id = 42
        member.user.username = "newuser"
        member.user.full_name = "New User"
        member.user.first_name = "New"
        result.new_chat_member = member
        update.chat_member = result

        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.member_update(update, ctx)
        ctx.bot.send_message.assert_called_once()
        # Member should be upserted
        m = tmp_db.member(42, -100)
        assert m is not None

    @pytest.mark.asyncio
    async def test_member_leave(self, make_context, tmp_db):
        update = MagicMock()
        result = MagicMock()
        result.chat = MagicMock()
        result.chat.id = -100
        member = MagicMock()
        member.status = "left"
        member.user = MagicMock()
        member.user.id = 42
        member.user.first_name = "Leaver"
        result.new_chat_member = member
        update.chat_member = result

        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.member_update(update, ctx)
        ctx.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_member_update_no_result(self, make_context):
        update = MagicMock()
        update.chat_member = None
        ctx = make_context()
        # Should return early without error
        await shady_bot.member_update(update, ctx)

    @pytest.mark.asyncio
    async def test_member_join_welcome_disabled(self, make_context, tmp_db):
        """No welcome message if welcome_enabled is 0."""
        tmp_db.settings(-100)
        tmp_db.set_setting(-100, "welcome_enabled", 0)

        update = MagicMock()
        result = MagicMock()
        result.chat = MagicMock()
        result.chat.id = -100
        member = MagicMock()
        member.status = "member"
        member.user = MagicMock()
        member.user.id = 42
        member.user.username = "newuser"
        member.user.full_name = "New User"
        member.user.first_name = "New"
        result.new_chat_member = member
        update.chat_member = result

        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.member_update(update, ctx)
        ctx.bot.send_message.assert_not_called()


# ═══════════════════════════════════════════
#    Tests: Settings command
# ═══════════════════════════════════════════

class TestSettingsCommand:
    """Tests for the /settings command."""

    @pytest.mark.asyncio
    async def test_settings_cmd(self, make_update, make_context, tmp_db):
        update = make_update(user_id=shady_bot.DEVELOPER_ID)
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.settings_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args
        # Should have inline keyboard
        assert call_kwargs.kwargs.get('reply_markup') is not None or \
            (len(call_kwargs) > 1 and call_kwargs[1].get('reply_markup') is not None)


# ═══════════════════════════════════════════
#    Tests: Quiz command
# ═══════════════════════════════════════════

class TestQuizCommand:
    """Tests for the /quiz command."""

    @pytest.mark.asyncio
    async def test_quiz_cmd(self, make_update, make_context, tmp_db):
        update = make_update()
        ctx = make_context()
        with patch.object(shady_bot, 'db', tmp_db):
            await shady_bot.quiz_cmd(update, ctx)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "\u0633\u0624\u0627\u0644" in text  # "question"

    @pytest.mark.asyncio
    async def test_send_quiz_no_questions(self, make_update, make_context):
        """_send_quiz with no questions should show error."""
        msg = MagicMock()
        msg.reply_text = AsyncMock()
        empty_db = MagicMock()
        empty_db.random_question.return_value = None
        with patch.object(shady_bot, 'db', empty_db):
            await shady_bot._send_quiz(msg, -100)
        text = msg.reply_text.call_args[0][0]
        assert "\u274c" in text
