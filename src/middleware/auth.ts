import { BotContext } from '../types';
import { User } from '../models/User';
import { config } from '../config';
import { logger } from '../utils/logger';

export async function authMiddleware(ctx: BotContext, next: () => Promise<void>): Promise<void> {
  if (!ctx.from) return next();

  const telegramId = ctx.from.id;

  try {
    let user = await User.findOne({ telegramId });

    if (!user) {
      user = await User.create({
        telegramId,
        username: ctx.from.username || '',
        firstName: ctx.from.first_name || '',
        lastName: ctx.from.last_name || '',
        role: config.adminIds.includes(telegramId) ? 'superadmin' : 'user',
      });
      logger.info(`New user registered: ${telegramId} (@${ctx.from.username})`);
    } else {
      if (user.role === 'banned') {
        return;
      }

      user.lastActive = new Date();
      user.username = ctx.from.username || user.username;
      user.firstName = ctx.from.first_name || user.firstName;
      user.totalRequests += 1;
      await user.save();
    }

    ctx.isAdmin = user.role === 'admin' || user.role === 'superadmin';
  } catch (err) {
    logger.error('Auth middleware error:', err);
  }

  return next();
}
