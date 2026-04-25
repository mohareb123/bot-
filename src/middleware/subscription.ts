import { BotContext } from '../types';
import { Channel } from '../models/Channel';
import { subscriptionKeyboard } from '../utils/keyboard';
import { logger } from '../utils/logger';
import { config } from '../config';

export async function subscriptionMiddleware(ctx: BotContext, next: () => Promise<void>): Promise<void> {
  if (!ctx.from || !ctx.chat) return next();

  if (ctx.isAdmin) return next();

  const userId = ctx.from.id;

  try {
    const channels = await Channel.find({ isRequired: true });

    const allChannels = [...channels.map(c => c.username)];
    for (const ch of config.requiredChannels) {
      if (!allChannels.includes(ch)) {
        allChannels.push(ch);
      }
    }

    if (allChannels.length === 0) return next();

    const notSubscribed: { username: string; title: string }[] = [];

    for (const channelUsername of allChannels) {
      try {
        const member = await ctx.telegram.getChatMember(`@${channelUsername}`, userId);
        if (['left', 'kicked'].includes(member.status)) {
          const channelDoc = channels.find(c => c.username === channelUsername);
          notSubscribed.push({
            username: channelUsername,
            title: channelDoc?.title || channelUsername,
          });
        }
      } catch (err) {
        logger.debug(`Cannot check subscription for @${channelUsername}:`, err);
      }
    }

    if (notSubscribed.length > 0) {
      await ctx.reply(
        '⚠️ يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:',
        subscriptionKeyboard(notSubscribed)
      );
      return;
    }
  } catch (err) {
    logger.error('Subscription check error:', err);
  }

  return next();
}
