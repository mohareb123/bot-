import { BotContext } from '../types';
import { logger } from './logger';
import fs from 'fs';
import path from 'path';
import { config } from '../config';
import { PATHS } from '../config';

export async function sendProcessing(ctx: BotContext, text = '⏳ جاري التنفيذ...'): Promise<number | undefined> {
  try {
    const msg = await ctx.reply(text);
    return msg.message_id;
  } catch (err) {
    logger.error('Failed to send processing message:', err);
    return undefined;
  }
}

export async function editMessage(ctx: BotContext, messageId: number, text: string, extra?: Record<string, unknown>): Promise<void> {
  try {
    await ctx.telegram.editMessageText(
      ctx.chat?.id,
      messageId,
      undefined,
      text,
      { parse_mode: 'HTML', ...extra } as Parameters<typeof ctx.telegram.editMessageText>[4]
    );
  } catch (err) {
    logger.debug('Failed to edit message (may already be deleted):', err);
  }
}

export async function deleteMessage(ctx: BotContext, messageId: number): Promise<void> {
  try {
    await ctx.telegram.deleteMessage(ctx.chat!.id, messageId);
  } catch (err) {
    logger.debug('Failed to delete message:', err);
  }
}

export async function autoDeleteMessage(ctx: BotContext, messageId: number, delayMs = 5000): Promise<void> {
  setTimeout(async () => {
    await deleteMessage(ctx, messageId);
  }, delayMs);
}

export async function sendSuccessVideo(ctx: BotContext, caption = '✅ تمت العملية بنجاح!'): Promise<void> {
  try {
    const videoPath = path.join(PATHS.assets, 'success_video.mp4');
    if (config.successVideoUrl) {
      await ctx.replyWithVideo(config.successVideoUrl, { caption });
    } else if (fs.existsSync(videoPath)) {
      await ctx.replyWithVideo({ source: videoPath }, { caption });
    }
  } catch (err) {
    logger.debug('Failed to send success video:', err);
  }
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function truncateText(text: string, maxLength = 4000): string {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}
