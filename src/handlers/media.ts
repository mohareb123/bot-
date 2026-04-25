import { Telegraf } from 'telegraf';
import { BotContext } from '../types';
import { downloadMedia } from '../services/media/downloader';
import { convertToMp3 } from '../services/media/converter';
import { sendProcessing, editMessage, deleteMessage, sendSuccessVideo } from '../utils/messages';
import { formatFileSize, isUrl, detectPlatform } from '../utils/helpers';
import { logger } from '../utils/logger';
import { Group } from '../models/Group';
import fs from 'fs';

export function registerMediaHandlers(bot: Telegraf<BotContext>): void {
  bot.command('download', async (ctx) => {
    const url = ctx.message.text.replace(/^\/download(@\w+)?\s*/, '').trim();
    if (!url || !isUrl(url)) {
      await ctx.reply(
        '📥 <b>تحميل الوسائط</b>\n\n' +
        'أرسل رابط الفيديو مباشرة أو استخدم:\n' +
        '<code>/download [رابط]</code>\n\n' +
        '📌 المنصات المدعومة:\n' +
        '• فيسبوك\n• تيك توك\n• إنستغرام\n• يوتيوب\n• تويتر/X\n• روابط مباشرة',
        { parse_mode: 'HTML' }
      );
      return;
    }

    await handleDownload(ctx, url);
  });

  bot.command('mp3', async (ctx) => {
    const url = ctx.message.text.replace(/^\/mp3(@\w+)?\s*/, '').trim();
    if (!url || !isUrl(url)) {
      await ctx.reply('🎵 أرسل رابط الفيديو بعد الأمر:\n<code>/mp3 [رابط]</code>', { parse_mode: 'HTML' });
      return;
    }

    await handleMp3Download(ctx, url);
  });

  bot.on('text', async (ctx, next) => {
    const text = ctx.message.text;
    if (!text || text.startsWith('/')) return next();
    if (!isUrl(text)) return next();

    const platform = detectPlatform(text);
    if (!platform) return next();

    await handleDownload(ctx, text);
  });
}

async function handleDownload(ctx: BotContext, url: string): Promise<void> {
  const platform = detectPlatform(url) || 'direct';
  const platformNames: Record<string, string> = {
    tiktok: 'تيك توك',
    facebook: 'فيسبوك',
    instagram: 'إنستغرام',
    youtube: 'يوتيوب',
    twitter: 'تويتر',
    direct: 'رابط مباشر',
  };

  const processingMsgId = await sendProcessing(
    ctx,
    `📥 جاري التحميل من ${platformNames[platform] || platform}...`
  );

  try {
    const result = await downloadMedia(url);
    const fileSize = formatFileSize(result.fileSize);

    if (processingMsgId) await deleteMessage(ctx, processingMsgId);

    if (result.fileSize > 50 * 1024 * 1024) {
      await ctx.reply('⚠️ حجم الملف كبير جداً (أكبر من 50MB). جاري محاولة ضغطه...');
    }

    await ctx.replyWithVideo(
      { source: result.filePath },
      {
        caption:
          `✅ <b>تم التحميل بنجاح!</b>\n\n` +
          `📌 المنصة: ${platformNames[platform] || platform}\n` +
          `📁 الحجم: ${fileSize}\n` +
          `📹 الصيغة: ${result.format}`,
        parse_mode: 'HTML',
      }
    );

    await sendSuccessVideo(ctx);

    if (fs.existsSync(result.filePath)) fs.unlinkSync(result.filePath);

    if (ctx.chat && ctx.chat.type !== 'private') {
      await Group.findOneAndUpdate({ chatId: ctx.chat.id }, { $inc: { 'stats.mediaDownloads': 1 } });
    }

    logger.info(`Media downloaded: ${platform} - ${fileSize}`);
  } catch (err) {
    logger.error('Media download error:', err);
    if (processingMsgId) {
      await editMessage(ctx, processingMsgId,
        `❌ فشل التحميل من ${platformNames[platform] || platform}.\n\n` +
        `تأكد من:\n• الرابط صحيح\n• الفيديو متاح للعامة\n• حجم الفيديو أقل من 50MB`
      );
    }
  }
}

async function handleMp3Download(ctx: BotContext, url: string): Promise<void> {
  const processingMsgId = await sendProcessing(ctx, '🎵 جاري التحميل والتحويل لـ MP3...');

  try {
    const videoResult = await downloadMedia(url);

    if (processingMsgId) {
      await editMessage(ctx, processingMsgId, '🎵 جاري تحويل الفيديو إلى MP3...');
    }

    const mp3Result = await convertToMp3(videoResult.filePath);
    const fileSize = formatFileSize(mp3Result.fileSize);

    if (processingMsgId) await deleteMessage(ctx, processingMsgId);

    await ctx.replyWithAudio(
      { source: mp3Result.filePath },
      {
        caption: `🎵 <b>تم التحويل لـ MP3!</b>\n📁 الحجم: ${fileSize}`,
        parse_mode: 'HTML',
      }
    );

    await sendSuccessVideo(ctx);

    if (fs.existsSync(videoResult.filePath)) fs.unlinkSync(videoResult.filePath);
    if (fs.existsSync(mp3Result.filePath)) fs.unlinkSync(mp3Result.filePath);
  } catch (err) {
    logger.error('MP3 conversion error:', err);
    if (processingMsgId) {
      await editMessage(ctx, processingMsgId, '❌ فشل تحويل الفيديو إلى MP3.');
    }
  }
}
