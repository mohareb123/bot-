import { Telegraf, Markup } from 'telegraf';
import { BotContext } from '../types';
import { mainMenuKeyboard } from '../utils/keyboard';
import { AVAILABLE_VOICES } from '../services/voice/tts';
import { User } from '../models/User';
import { Channel } from '../models/Channel';
import { config } from '../config';
import { logger } from '../utils/logger';

export function registerCallbackHandlers(bot: Telegraf<BotContext>): void {
  bot.action('back_main', async (ctx) => {
    await ctx.editMessageText(
      `🤖 <b>القائمة الرئيسية</b>\n\nاختر من القائمة أدناه:`,
      { parse_mode: 'HTML', ...mainMenuKeyboard() }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_ai', async (ctx) => {
    await ctx.editMessageText(
      `🤖 <b>الذكاء الاصطناعي</b>\n\n` +
      `💬 أرسل أي رسالة نصية للشات الذكي\n` +
      `📷 أرسل صورة لتحليلها\n` +
      `🖼️ استخدم /imagine لإنشاء صورة\n` +
      `✏️ استخدم /edit_image لتعديل صورة\n` +
      `🗑️ استخدم /clear لمسح سجل المحادثة`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_media', async (ctx) => {
    await ctx.editMessageText(
      `📥 <b>تحميل الوسائط</b>\n\n` +
      `أرسل رابط الفيديو مباشرة أو استخدم:\n` +
      `<code>/download [رابط]</code>\n\n` +
      `🎵 تحويل لـ MP3:\n` +
      `<code>/mp3 [رابط]</code>\n\n` +
      `📌 <b>المنصات المدعومة:</b>\n` +
      `• فيسبوك\n• تيك توك\n• إنستغرام\n• يوتيوب\n• تويتر/X\n• روابط مباشرة`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_tts', async (ctx) => {
    await ctx.editMessageText(
      `🔊 <b>تحويل النص إلى صوت</b>\n\n` +
      `استخدم: <code>/tts [النص]</code>\n\n` +
      `لتغيير الصوت: /voice\n\n` +
      `🌐 اللغات المدعومة: العربية، الإنجليزية، الفرنسية، الألمانية، الإسبانية، التركية`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_stt', async (ctx) => {
    await ctx.editMessageText(
      `🎤 <b>تحويل الصوت إلى نص</b>\n\n` +
      `أرسل رسالة صوتية وسأحولها لنص.\n\n` +
      `🌐 اللغات المدعومة: العربية والإنجليزية`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_image_gen', async (ctx) => {
    await ctx.editMessageText(
      `🖼️ <b>إنشاء صورة بالذكاء الاصطناعي</b>\n\n` +
      `استخدم: <code>/imagine [وصف الصورة]</code>\n\n` +
      `مثال: <code>/imagine قطة تجلس على القمر في ليلة مضيئة</code>`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_image_analyze', async (ctx) => {
    await ctx.editMessageText(
      `📷 <b>تحليل الصور</b>\n\n` +
      `أرسل أي صورة وسأحللها باستخدام الذكاء الاصطناعي.\n\n` +
      `يمكنك إضافة وصف مع الصورة لتخصيص التحليل.`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('menu_settings', async (ctx) => {
    const user = await User.findOne({ telegramId: ctx.from?.id });
    const currentVoice = AVAILABLE_VOICES.find(v => v.id === user?.settings?.ttsVoice);

    await ctx.editMessageText(
      `⚙️ <b>الإعدادات</b>\n\n` +
      `🌐 اللغة: ${user?.settings?.language || 'ar'}\n` +
      `🎙️ الصوت: ${currentVoice?.name || 'افتراضي'}\n` +
      `🔔 الإشعارات: ${user?.settings?.notifications ? '✅' : '❌'}`,
      {
        parse_mode: 'HTML',
        ...Markup.inlineKeyboard([
          [Markup.button.callback('🎙️ تغيير الصوت', 'settings_voice')],
          [Markup.button.callback(`🔔 الإشعارات: ${user?.settings?.notifications ? '✅' : '❌'}`, 'settings_notifications')],
          [Markup.button.callback('🔙 رجوع', 'back_main')],
        ]),
      }
    );
    await ctx.answerCbQuery();
  });

  bot.action('settings_voice', async (ctx) => {
    const voiceButtons = AVAILABLE_VOICES.map(v =>
      [Markup.button.callback(v.name, `set_voice_${v.id}`)]
    );
    voiceButtons.push([Markup.button.callback('🔙 رجوع', 'menu_settings')]);

    await ctx.editMessageText(
      '🎙️ <b>اختر الصوت:</b>',
      { parse_mode: 'HTML', ...Markup.inlineKeyboard(voiceButtons) }
    );
    await ctx.answerCbQuery();
  });

  bot.action(/set_voice_(.+)/, async (ctx) => {
    const voiceId = ctx.match[1];
    const voice = AVAILABLE_VOICES.find(v => v.id === voiceId);
    if (!voice) {
      await ctx.answerCbQuery('❌ صوت غير صالح');
      return;
    }

    await User.findOneAndUpdate(
      { telegramId: ctx.from?.id },
      { 'settings.ttsVoice': voiceId }
    );

    await ctx.answerCbQuery(`✅ تم تغيير الصوت إلى: ${voice?.name || voiceId}`);
    await ctx.editMessageText(
      `✅ تم تغيير الصوت إلى: <b>${voice?.name || voiceId}</b>`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'menu_settings')]]) }
    );
  });

  bot.action('settings_notifications', async (ctx) => {
    const user = await User.findOne({ telegramId: ctx.from?.id });
    if (user) {
      user.settings.notifications = !user.settings.notifications;
      await user.save();
      await ctx.answerCbQuery(`الإشعارات: ${user.settings.notifications ? '✅ مفعلة' : '❌ معطلة'}`);
    }
  });

  bot.action('menu_help', async (ctx) => {
    await ctx.editMessageText(
      `📖 <b>دليل الاستخدام:</b>\n\n` +
      `💬 <b>الشات الذكي:</b> أرسل أي رسالة نصية\n` +
      `📷 <b>تحليل صورة:</b> أرسل صورة\n` +
      `🖼️ <b>إنشاء صورة:</b> /imagine + الوصف\n` +
      `✏️ <b>تعديل صورة:</b> /edit_image كرد على صورة\n` +
      `📥 <b>تحميل فيديو:</b> أرسل رابط مباشر\n` +
      `🔊 <b>نص لصوت:</b> /tts + النص\n` +
      `🎤 <b>صوت لنص:</b> أرسل رسالة صوتية\n` +
      `🎵 <b>تحويل لـMP3:</b> /mp3 + رابط\n` +
      `🗑️ <b>مسح المحادثة:</b> /clear\n` +
      `📊 <b>إحصائياتك:</b> /stats`,
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'back_main')]]) }
    );
    await ctx.answerCbQuery();
  });

  bot.action('check_subscription', async (ctx) => {
    const userId = ctx.from?.id;
    if (!userId) return;

    try {
      const channels = await Channel.find({ isRequired: true });
      const allChannels = [...channels.map(c => c.username)];
      for (const ch of config.requiredChannels) {
        if (!allChannels.includes(ch)) allChannels.push(ch);
      }

      let allSubscribed = true;
      for (const channelUsername of allChannels) {
        try {
          const member = await ctx.telegram.getChatMember(`@${channelUsername}`, userId);
          if (['left', 'kicked'].includes(member.status)) {
            allSubscribed = false;
            break;
          }
        } catch {
          // skip
        }
      }

      if (allSubscribed) {
        await ctx.answerCbQuery('✅ تم التحقق! يمكنك استخدام البوت الآن.');
        await ctx.editMessageText(
          '✅ تم التحقق من اشتراكك بنجاح! أرسل /start للبدء.',
          { parse_mode: 'HTML' }
        );
      } else {
        await ctx.answerCbQuery('❌ لم تشترك في جميع القنوات المطلوبة.');
      }
    } catch (err) {
      logger.error('Subscription check error:', err);
      await ctx.answerCbQuery('❌ حدث خطأ. حاول مرة أخرى.');
    }
  });

  bot.action('cancel', async (ctx) => {
    await ctx.editMessageText('❌ تم الإلغاء.');
    await ctx.answerCbQuery();
  });

  bot.action('noop', async (ctx) => {
    await ctx.answerCbQuery();
  });
}
