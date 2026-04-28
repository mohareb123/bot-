import { Telegraf } from 'telegraf';
import { BotContext, ChatMessage } from '../types';
import { aiManager } from '../services/ai/provider';
import { generateImage, editImage } from '../services/ai/imageGeneration';
import { sendProcessing, editMessage, deleteMessage, sendSuccessVideo, truncateText, escapeHtml } from '../utils/messages';
import { logger } from '../utils/logger';
import { Group } from '../models/Group';
import { isUrl, detectPlatform, generateTempPath } from '../utils/helpers';
import axios from 'axios';
import fs from 'fs';

const chatHistory = new Map<number, ChatMessage[]>();
const MAX_HISTORY = 10;

function getUserHistory(userId: number): ChatMessage[] {
  return chatHistory.get(userId) || [];
}

function addToHistory(userId: number, role: 'user' | 'assistant', content: string): void {
  const history = getUserHistory(userId);
  history.push({ role, content });
  if (history.length > MAX_HISTORY * 2) {
    history.splice(0, 2);
  }
  chatHistory.set(userId, history);
}

export function registerAIHandlers(bot: Telegraf<BotContext>): void {
  bot.command('imagine', async (ctx) => {
    const prompt = ctx.message.text.replace(/^\/imagine(@\w+)?\s*/, '').trim();
    if (!prompt) {
      await ctx.reply('🖼️ أرسل وصف الصورة المطلوبة بعد الأمر:\n<code>/imagine قطة تجلس على القمر</code>', { parse_mode: 'HTML' });
      return;
    }

    const processingMsgId = await sendProcessing(ctx, '🎨 جاري إنشاء الصورة...');
    const startTime = Date.now();

    try {
      const result = await generateImage(prompt);
      const duration = ((Date.now() - startTime) / 1000).toFixed(1);

      if (processingMsgId) await deleteMessage(ctx, processingMsgId);

      await ctx.replyWithPhoto(
        { source: result.imagePath },
        { caption: `🖼️ <b>تم إنشاء الصورة</b>\n\n📝 ${escapeHtml(prompt)}\n⏱ ${duration}s | 🔧 ${result.provider}`, parse_mode: 'HTML' }
      );

      await sendSuccessVideo(ctx);

      if (fs.existsSync(result.imagePath)) fs.unlinkSync(result.imagePath);

      if (ctx.chat && ctx.chat.type !== 'private') {
        await Group.findOneAndUpdate({ chatId: ctx.chat.id }, { $inc: { 'stats.aiRequests': 1 } });
      }
    } catch (err) {
      logger.error('Image generation error:', err);
      if (processingMsgId) {
        await editMessage(ctx, processingMsgId, '❌ فشل إنشاء الصورة. حاول مرة أخرى.');
      }
    }
  });

  bot.command('edit_image', async (ctx) => {
    const replyMsg = ctx.message.reply_to_message;
    if (!replyMsg || !('photo' in replyMsg) || !replyMsg.photo) {
      await ctx.reply('📷 أرسل هذا الأمر كرد على صورة مع وصف التعديل المطلوب.');
      return;
    }

    const prompt = ctx.message.text.replace(/^\/edit_image(@\w+)?\s*/, '').trim();
    if (!prompt) {
      await ctx.reply('✏️ أضف وصف التعديل بعد الأمر.');
      return;
    }

    const processingMsgId = await sendProcessing(ctx, '✏️ جاري تعديل الصورة...');

    try {
      const photo = replyMsg.photo[replyMsg.photo.length - 1];
      const fileLink = await ctx.telegram.getFileLink(photo.file_id);

      const tempPath = generateTempPath('jpg');
      const response = await axios.get(fileLink.href, { responseType: 'arraybuffer' });
      fs.writeFileSync(tempPath, response.data);

      const result = await editImage(tempPath, prompt);

      if (processingMsgId) await deleteMessage(ctx, processingMsgId);

      await ctx.replyWithPhoto(
        { source: result.imagePath },
        { caption: `✏️ <b>تم تعديل الصورة</b>\n\n📝 ${escapeHtml(prompt)}`, parse_mode: 'HTML' }
      );

      await sendSuccessVideo(ctx);

      if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
      if (fs.existsSync(result.imagePath)) fs.unlinkSync(result.imagePath);
    } catch (err) {
      logger.error('Image edit error:', err);
      if (processingMsgId) {
        await editMessage(ctx, processingMsgId, '❌ فشل تعديل الصورة. حاول مرة أخرى.');
      }
    }
  });

  bot.command('clear', async (ctx) => {
    const userId = ctx.from?.id;
    if (userId) {
      chatHistory.delete(userId);
      await ctx.reply('🗑️ تم مسح سجل المحادثة.');
    }
  });

  bot.on('photo', async (ctx) => {
    const caption = ctx.message.caption || 'صف هذه الصورة بالتفصيل';
    const processingMsgId = await sendProcessing(ctx, '📷 جاري تحليل الصورة...');

    try {
      const photo = ctx.message.photo[ctx.message.photo.length - 1];
      const fileLink = await ctx.telegram.getFileLink(photo.file_id);

      const result = await aiManager.analyzeImage(fileLink.href, caption);
      const truncated = truncateText(result);

      if (processingMsgId) {
        await editMessage(ctx, processingMsgId, `📷 <b>تحليل الصورة:</b>\n\n${escapeHtml(truncated)}`);
      }

      await sendSuccessVideo(ctx);

      if (ctx.chat && ctx.chat.type !== 'private') {
        await Group.findOneAndUpdate({ chatId: ctx.chat.id }, { $inc: { 'stats.aiRequests': 1 } });
      }
    } catch (err) {
      logger.error('Image analysis error:', err);
      if (processingMsgId) {
        await editMessage(ctx, processingMsgId, '❌ فشل تحليل الصورة. حاول مرة أخرى.');
      }
    }
  });

  bot.on('text', async (ctx, next) => {
    const text = ctx.message.text;
    if (!text || text.startsWith('/')) return next();

    if (isUrl(text) && detectPlatform(text)) return next();

    const userId = ctx.from.id;
    const processingMsgId = await sendProcessing(ctx, '🤖 جاري التفكير...');

    try {
      const history = [...getUserHistory(userId)];

      const response = await aiManager.chat(text, history);
      const truncated = truncateText(response);

      addToHistory(userId, 'user', text);
      addToHistory(userId, 'assistant', response);

      if (processingMsgId) {
        await editMessage(ctx, processingMsgId, escapeHtml(truncated));
      }

      if (ctx.chat && ctx.chat.type !== 'private') {
        await Group.findOneAndUpdate({ chatId: ctx.chat.id }, { $inc: { 'stats.aiRequests': 1 } });
      }
    } catch (err) {
      logger.error('AI chat error:', err);
      if (processingMsgId) {
        await editMessage(ctx, processingMsgId, '❌ عذراً، حدث خطأ. حاول مرة أخرى.');
      }
    }
  });
}
