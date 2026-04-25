import { BotContext } from '../types';
import { config } from '../config';
import { logger } from '../utils/logger';

const userRequests = new Map<number, { count: number; resetTime: number }>();

export async function rateLimitMiddleware(ctx: BotContext, next: () => Promise<void>): Promise<void> {
  if (!ctx.from) return next();
  if (ctx.isAdmin) return next();

  const userId = ctx.from.id;
  const now = Date.now();

  let userData = userRequests.get(userId);

  if (!userData || now > userData.resetTime) {
    userData = { count: 0, resetTime: now + 60000 };
    userRequests.set(userId, userData);
  }

  userData.count++;

  if (userData.count > config.maxRequestsPerMinute) {
    logger.warn(`Rate limit exceeded for user ${userId}`);
    try {
      await ctx.reply('⚠️ لقد تجاوزت الحد المسموح من الطلبات. يرجى الانتظار دقيقة واحدة.');
    } catch (_err) {
      // ignore
    }
    return;
  }

  return next();
}

setInterval(() => {
  const now = Date.now();
  for (const [userId, data] of userRequests.entries()) {
    if (now > data.resetTime) {
      userRequests.delete(userId);
    }
  }
}, 300000);
