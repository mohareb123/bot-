import { Telegraf } from 'telegraf';
import { BotContext } from '../types';
import { textToSpeech, AVAILABLE_VOICES } from '../services/voice/tts';
import { speechToText } from '../services/voice/stt';
import { sendProcessing, editMessage, deleteMessage, sendSuccessVideo, escapeHtml } from '../utils/messages';
import { User } from '../models/User';
import { logger } from '../utils/logger';
import { Group } from '../models/Group';
import { Markup } from 'telegraf';
import axios from 'axios';
import fs from 'fs';
import { generateTempPath } from '../utils/helpers';

export function registerVoiceHandlers(bot: Telegraf<BotContext>): void {
  bot.command('tts', async (ctx) => {
    const text = ctx.message.text.replace(/^\/tts(@\w+)?\s*/, '').trim();
    if (!text) {
      await ctx.reply(
        '🔊 <b>تحويل النص إلى صوت</b>\n\n' +
        'استخدم: <code>/tts [النص]</code>\n\n' +
        'لتغيير الصوت: <code>/voice</code>',
        { parse_mode: 'HTML' }
      );
      return;
    }

    await handleTTS(ctx, text);
  });

  bot.command('voice', async (ctx) => {
    const voiceButtons = AVAILABLE_VOICES.map(v =>
      [Markup.button.callback(`${v.name}`, `set_voice_${v.id}`)]
    );
    voiceButtons.push([Markup.button.callback('🔙 رجوع', 'back_main')]);

    await ctx.reply(
      '🎙️ <b>اختر الصوت المطلوب:</b>',
      { parse_mode: 'HTML', ...Markup.inlineKeyboard(voiceButtons) }
    );
  });

  bot.on('voice', async (ctx) => {
    await handleSTT(ctx);
  });

  bot.on('audio', async (ctx) => {
    await handleSTT(ctx);
  });
}

async function handleTTS(ctx: BotContext, text: string, voiceId?: string): Promise<void> {
  const processingMsgId = await sendProcessing(ctx, '🔊 جاري تحويل النص لصوت...');

  try {
    const user = await User.findOne({ telegramId: ctx.from?.id });
    const voice = voiceId || user?.settings?.ttsVoice || 'ar-EG-ShakirNeural';

    const audioPath = await textToSpeech(text, voice);

    if (processingMsgId) await deleteMessage(ctx, processingMsgId);

    await ctx.replyWithVoice(
      { source: audioPath },
      { caption: `🔊 ${escapeHtml(text.substring(0, 100))}${text.length > 100 ? '...' : ''}`, parse_mode: 'HTML' }
    );

    await sendSuccessVideo(ctx);

    if (fs.existsSync(audioPath)) fs.unlinkSync(audioPath);

    if (ctx.chat && ctx.chat.type !== 'private') {
      await Group.findOneAndUpdate({ chatId: ctx.chat.id }, { $inc: { 'stats.voiceRequests': 1 } });
    }
  } catch (err) {
    logger.error('TTS error:', err);
    if (processingMsgId) {
      await editMessage(ctx, processingMsgId, '❌ فشل تحويل النص إلى صوت. حاول مرة أخرى.');
    }
  }
}

async function handleSTT(ctx: BotContext): Promise<void> {
  const processingMsgId = await sendProcessing(ctx, '🎤 جاري تحويل الصوت لنص...');

  try {
    const msg = ctx.message;
    if (!msg) {
      if (processingMsgId) await editMessage(ctx, processingMsgId, '❌ لم يتم العثور على ملف صوتي.');
      return;
    }
    let fileId: string;
    if ('voice' in msg && msg.voice) {
      fileId = msg.voice.file_id;
    } else if ('audio' in msg && msg.audio) {
      fileId = msg.audio.file_id;
    } else {
      if (processingMsgId) await editMessage(ctx, processingMsgId, '❌ لم يتم العثور على ملف صوتي.');
      return;
    }

    const fileLink = await ctx.telegram.getFileLink(fileId);
    const tempPath = generateTempPath('ogg');

    const response = await axios.get(fileLink.href, { responseType: 'arraybuffer', timeout: 30000 });
    fs.writeFileSync(tempPath, response.data);

    const result = await speechToText(tempPath);

    if (processingMsgId) {
      await editMessage(ctx, processingMsgId,
        `🎤 <b>النص المستخرج:</b>\n\n${escapeHtml(result.text)}`
      );
    }

    await sendSuccessVideo(ctx);

    if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);

    if (ctx.chat && ctx.chat.type !== 'private') {
      await Group.findOneAndUpdate({ chatId: ctx.chat.id }, { $inc: { 'stats.voiceRequests': 1 } });
    }
  } catch (err) {
    logger.error('STT error:', err);
    if (processingMsgId) {
      await editMessage(ctx, processingMsgId, '❌ فشل تحويل الصوت إلى نص. حاول مرة أخرى.');
    }
  }
}
