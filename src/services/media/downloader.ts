import axios from 'axios';
import { execFile } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import path from 'path';
import { config } from '../../config';
import { logger } from '../../utils/logger';
import { generateTempPath, detectPlatform } from '../../utils/helpers';

const execFileAsync = promisify(execFile);

export interface DownloadResult {
  filePath: string;
  title: string;
  platform: string;
  format: string;
  fileSize: number;
}

export async function downloadMedia(url: string): Promise<DownloadResult> {
  const platform = detectPlatform(url);
  logger.info(`Downloading media from ${platform || 'direct'}: ${url}`);

  const providers = [
    () => downloadWithCobalt(url),
    () => downloadWithYtDlp(url),
    () => downloadDirect(url),
  ];

  for (const provider of providers) {
    try {
      return await provider();
    } catch (err) {
      logger.warn('Download provider failed:', err);
      continue;
    }
  }

  throw new Error('فشل تحميل الوسائط من جميع المصادر');
}

async function downloadWithCobalt(url: string): Promise<DownloadResult> {
  const response = await axios.post(
    `${config.cobaltApiUrl}/`,
    {
      url,
      downloadMode: 'auto',
      filenameStyle: 'basic',
    },
    {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    }
  );

  const data = response.data;

  if (data.status === 'tunnel' || data.status === 'redirect') {
    const downloadUrl = data.url;
    const filePath = generateTempPath('mp4');

    const fileResponse = await axios.get(downloadUrl, {
      responseType: 'arraybuffer',
      timeout: 300000,
      maxContentLength: 50 * 1024 * 1024,
    });

    fs.writeFileSync(filePath, fileResponse.data);

    return {
      filePath,
      title: data.filename || 'video',
      platform: detectPlatform(url) || 'unknown',
      format: 'mp4',
      fileSize: fileResponse.data.length,
    };
  }

  throw new Error(`Cobalt returned status: ${data.status}`);
}

async function downloadWithYtDlp(url: string): Promise<DownloadResult> {
  const filePath = generateTempPath('mp4');
  const args = ['-f', 'best[filesize<50M]/best', '--no-playlist', '--max-filesize', '50M', '-o', filePath, url];
  if (config.googleCookiesPath) {
    args.unshift('--cookies', config.googleCookiesPath);
  }

  try {
    const { stdout } = await execFileAsync('yt-dlp', args, { timeout: 120000 });
    logger.debug('yt-dlp output:', stdout);

    if (!fs.existsSync(filePath)) {
      const dir = path.dirname(filePath);
      const base = path.basename(filePath, '.mp4');
      const files = fs.readdirSync(dir).filter(f => f.startsWith(base));
      if (files.length > 0) {
        const actualPath = path.join(dir, files[0]);
        fs.renameSync(actualPath, filePath);
      } else {
        throw new Error('yt-dlp did not produce output file');
      }
    }

    const stat = fs.statSync(filePath);

    return {
      filePath,
      title: 'video',
      platform: detectPlatform(url) || 'unknown',
      format: 'mp4',
      fileSize: stat.size,
    };
  } catch (err) {
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    throw err;
  }
}

async function downloadDirect(url: string): Promise<DownloadResult> {
  const filePath = generateTempPath('mp4');

  const response = await axios.get(url, {
    responseType: 'arraybuffer',
    timeout: 120000,
    maxContentLength: 50 * 1024 * 1024,
  });

  fs.writeFileSync(filePath, response.data);

  return {
    filePath,
    title: 'media',
    platform: 'direct',
    format: 'mp4',
    fileSize: response.data.length,
  };
}
