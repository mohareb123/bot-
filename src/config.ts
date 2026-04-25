import dotenv from 'dotenv';
import path from 'path';
import { BotConfig } from './types';

dotenv.config();

function getEnv(key: string, defaultValue = ''): string {
  return process.env[key] || defaultValue;
}

function getEnvNumber(key: string, defaultValue: number): number {
  const val = process.env[key];
  return val ? parseInt(val, 10) : defaultValue;
}

function getEnvArray(key: string, defaultValue: string[] = []): string[] {
  const val = process.env[key];
  if (!val) return defaultValue;
  return val.split(',').map(s => s.trim()).filter(Boolean);
}

function getEnvNumberArray(key: string, defaultValue: number[] = []): number[] {
  const val = process.env[key];
  if (!val) return defaultValue;
  return val.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));
}

export const config: BotConfig = {
  botToken: getEnv('BOT_TOKEN'),
  botUsername: getEnv('BOT_USERNAME'),
  mongodbUri: getEnv('MONGODB_URI', 'mongodb://localhost:27017/ai-telegram-bot'),
  adminIds: getEnvNumberArray('ADMIN_IDS'),
  adminPassword: getEnv('ADMIN_PASSWORD', 'admin123'),
  geminiApiKey: getEnv('GEMINI_API_KEY'),
  openaiApiKey: getEnv('OPENAI_API_KEY'),
  openaiBaseUrl: getEnv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
  huggingfaceApiKey: getEnv('HUGGINGFACE_API_KEY'),
  witAiToken: getEnv('WIT_AI_TOKEN'),
  cobaltApiUrl: getEnv('COBALT_API_URL', 'https://api.cobalt.tools'),
  googleCookiesPath: getEnv('GOOGLE_COOKIES_PATH'),
  requiredChannels: getEnvArray('REQUIRED_CHANNELS'),
  successVideoUrl: getEnv('SUCCESS_VIDEO_URL'),
  port: getEnvNumber('PORT', 3000),
  nodeEnv: getEnv('NODE_ENV', 'production'),
  maxRequestsPerMinute: getEnvNumber('MAX_REQUESTS_PER_MINUTE', 20),
};

export const PATHS = {
  assets: path.join(__dirname, '..', 'assets'),
  downloads: path.join(__dirname, '..', 'downloads'),
  temp: path.join(__dirname, '..', 'temp'),
};

export function validateConfig(): void {
  if (!config.botToken) {
    throw new Error('BOT_TOKEN is required');
  }
}
