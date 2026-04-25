import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import { logger } from '../../utils/logger';
import { generateTempPath } from '../../utils/helpers';

const execAsync = promisify(exec);

export interface ConvertResult {
  filePath: string;
  format: string;
  duration: number;
  fileSize: number;
}

export async function convertToMp3(videoPath: string): Promise<ConvertResult> {
  const outputPath = generateTempPath('mp3');

  try {
    const cmd = `ffmpeg -i "${videoPath}" -vn -acodec libmp3lame -ab 192k -ar 44100 -y "${outputPath}" 2>&1`;
    await execAsync(cmd, { timeout: 120000 });

    if (!fs.existsSync(outputPath)) {
      throw new Error('FFmpeg did not produce output file');
    }

    const stat = fs.statSync(outputPath);
    const duration = await getMediaDuration(outputPath);

    return {
      filePath: outputPath,
      format: 'mp3',
      duration,
      fileSize: stat.size,
    };
  } catch (err) {
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    logger.error('Video to MP3 conversion failed:', err);
    throw new Error('فشل تحويل الفيديو إلى MP3');
  }
}

export async function getMediaDuration(filePath: string): Promise<number> {
  try {
    const { stdout } = await execAsync(
      `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${filePath}"`,
      { timeout: 10000 }
    );
    return parseFloat(stdout.trim()) || 0;
  } catch {
    return 0;
  }
}

export async function convertAudioFormat(inputPath: string, format: string): Promise<string> {
  const outputPath = generateTempPath(format);

  try {
    const cmd = `ffmpeg -i "${inputPath}" -y "${outputPath}" 2>&1`;
    await execAsync(cmd, { timeout: 60000 });

    if (!fs.existsSync(outputPath)) {
      throw new Error('FFmpeg format conversion failed');
    }

    return outputPath;
  } catch (err) {
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    throw err;
  }
}
