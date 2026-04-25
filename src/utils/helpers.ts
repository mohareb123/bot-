import fs from 'fs';
import path from 'path';
import { PATHS } from '../config';
import { logger } from './logger';

export function ensureDirectories(): void {
  const dirs = [PATHS.downloads, PATHS.temp, path.join(__dirname, '..', '..', 'logs')];
  for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }
}

export function cleanTempFiles(maxAgeMs = 3600000): void {
  try {
    if (!fs.existsSync(PATHS.temp)) return;
    const files = fs.readdirSync(PATHS.temp);
    const now = Date.now();
    for (const file of files) {
      const filePath = path.join(PATHS.temp, file);
      const stat = fs.statSync(filePath);
      if (now - stat.mtimeMs > maxAgeMs) {
        fs.unlinkSync(filePath);
      }
    }
  } catch (err) {
    logger.error('Error cleaning temp files:', err);
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function isUrl(text: string): boolean {
  try {
    new URL(text);
    return true;
  } catch {
    return false;
  }
}

export function detectPlatform(url: string): string | null {
  const platforms: Record<string, RegExp> = {
    tiktok: /tiktok\.com/i,
    facebook: /facebook\.com|fb\.watch|fb\.com/i,
    instagram: /instagram\.com/i,
    youtube: /youtube\.com|youtu\.be/i,
    twitter: /twitter\.com|x\.com/i,
  };

  for (const [platform, regex] of Object.entries(platforms)) {
    if (regex.test(url)) return platform;
  }
  return null;
}

export function generateTempPath(extension: string): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(7);
  return path.join(PATHS.temp, `${timestamp}_${random}.${extension}`);
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}
