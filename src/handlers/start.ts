import { Telegraf } from 'telegraf';
import { BotContext } from '../types';
import { mainMenuKeyboard } from '../utils/keyboard';
import { Group } from '../models/Group';
import { User } from '../models/User';
import { logger } from '../utils/logger';

export function registerStartHandlers(bot: Telegraf<BotContext>): void {
  bot.start(async (ctx) => {
    const firstName = ctx.from?.first_name || 'صديقي';

    await ctx.reply(
      `مرحباً <b>${firstName}</b>! 👋\n\n` +
      `أنا بوت ذكاء اصطناعي متكامل، أقدر أساعدك في:\n\n` +
      `🤖 <b>الذكاء الاصطناعي</b> - شات ذكي، تحليل وإنشاء صور\n` +
      `📥 <b>تحميل الوسائط</b> - فيسبوك، تيك توك، وغيرها\n` +
      `🔊 <b>تحويل النص لصوت</b> - عدة لغات وأصوات\n` +
      `🎤 <b>تحويل الصوت لنص</b> - عربي وإنجليزي\n\n` +
      `اختر من القائمة أو أرسل لي أي رسالة نصية للشات الذكي 💬`,
      { parse_mode: 'HTML', ...mainMenuKeyboard() }
    );
  });

  bot.help(async (ctx) => {
    await ctx.reply(
      `📖 <b>دليل الاستخدام:</b>\n\n` +
      `💬 <b>الشات الذكي:</b> أرسل أي رسالة نصية\n` +
      `📷 <b>تحليل صورة:</b> أرسل صورة مع وصف أو بدون\n` +
      `🖼️ <b>إنشاء صورة:</b> /imagine + الوصف\n` +
      `📥 <b>تحميل فيديو:</b> أرسل رابط الفيديو مباشرة\n` +
      `🔊 <b>نص لصوت:</b> /tts + النص\n` +
      `🎤 <b>صوت لنص:</b> أرسل رسالة صوتية\n` +
      `🎵 <b>تحويل لـMP3:</b> /mp3 + رابط الفيديو\n\n` +
      `⚙️ <b>أوامر أخرى:</b>\n` +
      `/settings - الإعدادات\n` +
      `/admin - لوحة التحكم (للأدمن)\n` +
      `/stats - إحصائياتك`,
      { parse_mode: 'HTML', ...mainMenuKeyboard() }
    );
  });

  bot.command('stats', async (ctx) => {
    const userId = ctx.from?.id;
    if (!userId) return;

    const user = await User.findOne({ telegramId: userId });

    if (!user) {
      await ctx.reply('لم يتم العثور على بياناتك.');
      return;
    }

    await ctx.reply(
      `📊 <b>إحصائياتك:</b>\n\n` +
      `👤 الاسم: ${user.firstName} ${user.lastName}\n` +
      `📝 إجمالي الطلبات: ${user.totalRequests}\n` +
      `📅 تاريخ الانضمام: ${user.joinedAt.toLocaleDateString('ar-EG')}\n` +
      `🕐 آخر نشاط: ${user.lastActive.toLocaleDateString('ar-EG')}`,
      { parse_mode: 'HTML' }
    );
  });

  bot.on('new_chat_members', async (ctx) => {
    try {
      const botInfo = await ctx.telegram.getMe();
      const isBotAdded = ctx.message.new_chat_members.some(m => m.id === botInfo.id);

      if (isBotAdded && ctx.chat.type !== 'private') {
        await Group.findOneAndUpdate(
          { chatId: ctx.chat.id },
          {
            chatId: ctx.chat.id,
            title: ctx.chat.title || '',
            isActive: true,
            joinedAt: new Date(),
          },
          { upsert: true, new: true }
        );
        logger.info(`Bot added to group: ${ctx.chat.title} (${ctx.chat.id})`);
      }
    } catch (err) {
      logger.error('Error handling new chat members:', err);
    }
  });

  bot.on('left_chat_member', async (ctx) => {
    try {
      const botInfo = await ctx.telegram.getMe();
      if (ctx.message.left_chat_member.id === botInfo.id) {
        await Group.findOneAndUpdate(
          { chatId: ctx.chat.id },
          { isActive: false }
        );
        logger.info(`Bot removed from group: ${ctx.chat.id}`);
      }
    } catch (err) {
      logger.error('Error handling left chat member:', err);
    }
  });
}
