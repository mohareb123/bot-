import { Telegraf } from 'telegraf';
import { BotContext } from './types';
import { config } from './config';
import { authMiddleware } from './middleware/auth';
import { subscriptionMiddleware } from './middleware/subscription';
import { rateLimitMiddleware } from './middleware/rateLimit';
import { loggerMiddleware } from './middleware/loggerMiddleware';
import { registerStartHandlers } from './handlers/start';
import { registerAIHandlers } from './handlers/ai';
import { registerMediaHandlers } from './handlers/media';
import { registerVoiceHandlers } from './handlers/voice';
import { registerAdminHandlers } from './handlers/admin';
import { registerCallbackHandlers } from './handlers/callbacks';
import { aiManager } from './services/ai/provider';
import { GeminiProvider, OpenAICompatibleProvider, FreeAIProvider } from './services/ai/chat';
import { logger } from './utils/logger';

export function createBot(): Telegraf<BotContext> {
  const bot = new Telegraf<BotContext>(config.botToken);

  // Register AI providers (order = priority for fallback)
  aiManager.register(new GeminiProvider());
  aiManager.register(new OpenAICompatibleProvider());
  aiManager.register(new FreeAIProvider());

  // Middleware (order matters)
  bot.use(authMiddleware);
  bot.use(rateLimitMiddleware);
  bot.use(subscriptionMiddleware);
  bot.use(loggerMiddleware);

  // Handlers (order matters: commands first, then text/media)
  registerStartHandlers(bot);
  registerAdminHandlers(bot);
  registerCallbackHandlers(bot);
  registerVoiceHandlers(bot);
  registerMediaHandlers(bot);
  registerAIHandlers(bot);

  // Error handling
  bot.catch((err: unknown, ctx: BotContext) => {
    logger.error(`Bot error for ${ctx.from?.id}:`, err);
    try {
      ctx.reply('❌ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.');
    } catch {
      // ignore
    }
  });

  return bot;
}
