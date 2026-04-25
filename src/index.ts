import { config, validateConfig } from './config';
import { connectDatabase } from './database';
import { createBot } from './bot';
import { ensureDirectories, cleanTempFiles } from './utils/helpers';
import { logger } from './utils/logger';
import cron from 'node-cron';

async function main(): Promise<void> {
  logger.info('Starting AI Telegram Bot...');

  validateConfig();
  ensureDirectories();

  await connectDatabase();

  const bot = createBot();

  // Clean temp files every hour
  cron.schedule('0 * * * *', () => {
    cleanTempFiles();
    logger.debug('Temp files cleaned');
  });

  // Graceful shutdown
  const shutdown = async (signal: string) => {
    logger.info(`Received ${signal}. Shutting down gracefully...`);
    bot.stop(signal);
    process.exit(0);
  };

  process.once('SIGINT', () => shutdown('SIGINT'));
  process.once('SIGTERM', () => shutdown('SIGTERM'));

  // Start bot
  await bot.launch();
  logger.info(`Bot started successfully! (@${config.botUsername || 'bot'})`);
  logger.info(`Environment: ${config.nodeEnv}`);
  logger.info(`Admin IDs: ${config.adminIds.join(', ') || 'none configured'}`);
}

main().catch((err) => {
  logger.error('Fatal error:', err);
  process.exit(1);
});
