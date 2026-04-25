import { BotContext } from '../types';
import { Log } from '../models/Log';
import { logger } from '../utils/logger';

export async function loggerMiddleware(ctx: BotContext, next: () => Promise<void>): Promise<void> {
  const startTime = Date.now();

  await next();

  const duration = Date.now() - startTime;

  try {
    const action = getActionFromContext(ctx);
    if (action) {
      await Log.create({
        userId: ctx.from?.id || 0,
        action,
        details: getDetailsFromContext(ctx),
        chatId: ctx.chat?.id || 0,
        timestamp: new Date(),
        success: true,
        duration,
      });
    }
  } catch (err) {
    logger.debug('Failed to log action:', err);
  }
}

function getActionFromContext(ctx: BotContext): string | null {
  if ('text' in (ctx.message || {})) {
    const text = (ctx.message as { text?: string })?.text || '';
    if (text.startsWith('/')) {
      return `command:${text.split(' ')[0].split('@')[0]}`;
    }
    return 'message:text';
  }
  if ('photo' in (ctx.message || {})) return 'message:photo';
  if ('voice' in (ctx.message || {})) return 'message:voice';
  if ('video' in (ctx.message || {})) return 'message:video';
  if (ctx.callbackQuery) return 'callback';
  return null;
}

function getDetailsFromContext(ctx: BotContext): string {
  if ('text' in (ctx.message || {})) {
    const text = (ctx.message as { text?: string })?.text || '';
    return text.substring(0, 200);
  }
  if (ctx.callbackQuery && 'data' in ctx.callbackQuery) {
    return ctx.callbackQuery.data || '';
  }
  return '';
}
