import { Context } from 'telegraf';
import { Update } from 'telegraf/types';

export interface BotConfig {
  botToken: string;
  botUsername: string;
  mongodbUri: string;
  adminIds: number[];
  adminPassword: string;
  geminiApiKey: string;
  openaiApiKey: string;
  openaiBaseUrl: string;
  huggingfaceApiKey: string;
  witAiToken: string;
  cobaltApiUrl: string;
  googleCookiesPath: string;
  requiredChannels: string[];
  successVideoUrl: string;
  port: number;
  nodeEnv: string;
  maxRequestsPerMinute: number;
}

export interface BotContext extends Context<Update> {
  dbUser?: UserDocument;
  isAdmin?: boolean;
}

export interface UserDocument {
  telegramId: number;
  username: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin' | 'superadmin' | 'banned';
  requestCount: number;
  lastRequestTime: Date;
  totalRequests: number;
  joinedAt: Date;
  lastActive: Date;
  settings: UserSettings;
}

export interface UserSettings {
  language: string;
  ttsVoice: string;
  imageQuality: string;
  notifications: boolean;
}

export interface GroupDocument {
  chatId: number;
  title: string;
  isActive: boolean;
  joinedAt: Date;
  memberCount: number;
  settings: GroupSettings;
  stats: GroupStats;
}

export interface GroupSettings {
  aiEnabled: boolean;
  mediaEnabled: boolean;
  voiceEnabled: boolean;
  welcomeMessage: string;
  language: string;
}

export interface GroupStats {
  totalMessages: number;
  aiRequests: number;
  mediaDownloads: number;
  voiceRequests: number;
}

export interface ChannelDocument {
  channelId: string;
  username: string;
  title: string;
  isRequired: boolean;
  addedAt: Date;
  subscriberCount: number;
}

export interface PluginDocument {
  name: string;
  description: string;
  version: string;
  isActive: boolean;
  settings: Record<string, unknown>;
  handler: string;
  addedAt: Date;
}

export interface LogDocument {
  userId: number;
  action: string;
  details: string;
  chatId: number;
  timestamp: Date;
  success: boolean;
  duration: number;
}

export interface AIProvider {
  name: string;
  chat(prompt: string, history?: ChatMessage[]): Promise<string>;
  analyzeImage(imageUrl: string, prompt?: string): Promise<string>;
  isAvailable(): Promise<boolean>;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface MediaDownloadResult {
  url: string;
  title: string;
  thumbnail?: string;
  duration?: number;
  format: string;
  fileSize?: number;
  qualities?: MediaQuality[];
}

export interface MediaQuality {
  label: string;
  url: string;
  format: string;
  fileSize?: number;
}

export interface TTSResult {
  audioBuffer: Buffer;
  duration: number;
}

export interface STTResult {
  text: string;
  language: string;
  confidence: number;
}

export interface AdminAction {
  type: string;
  targetId: number | string;
  performedBy: number;
  details: string;
  timestamp: Date;
}

export type CallbackAction =
  | 'admin_main'
  | 'admin_groups'
  | 'admin_channels'
  | 'admin_users'
  | 'admin_plugins'
  | 'admin_stats'
  | 'admin_settings'
  | 'group_toggle'
  | 'group_settings'
  | 'channel_add'
  | 'channel_remove'
  | 'channel_toggle'
  | 'user_promote'
  | 'user_demote'
  | 'user_ban'
  | 'user_unban'
  | 'plugin_toggle'
  | 'plugin_settings'
  | 'ai_chat'
  | 'ai_image_gen'
  | 'ai_image_analyze'
  | 'media_download'
  | 'media_quality'
  | 'media_mp3'
  | 'voice_tts'
  | 'voice_stt'
  | 'check_subscription'
  | 'cancel'
  | 'back'
  | 'page_next'
  | 'page_prev';
