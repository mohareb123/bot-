import axios from 'axios';
import fs from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';
import { config } from '../../config';
import { logger } from '../../utils/logger';
import { generateTempPath } from '../../utils/helpers';

const execAsync = promisify(exec);

export interface STTResult {
  text: string;
  language: string;
  confidence: number;
}

export async function speechToText(audioPath: string): Promise<STTResult> {
  const providers = [
    () => sttWithWitAi(audioPath),
    () => sttWithWhisper(audioPath),
  ];

  for (const provider of providers) {
    try {
      return await provider();
    } catch (err) {
      logger.warn('STT provider failed:', err);
      continue;
    }
  }

  throw new Error('فشل تحويل الصوت إلى نص');
}

async function sttWithWitAi(audioPath: string): Promise<STTResult> {
  if (!config.witAiToken) throw new Error('Wit.ai token not configured');

  const wavPath = await convertToWav(audioPath);

  try {
    const audioData = fs.readFileSync(wavPath);

    const response = await axios.post(
      'https://api.wit.ai/speech?v=20240101',
      audioData,
      {
        headers: {
          Authorization: `Bearer ${config.witAiToken}`,
          'Content-Type': 'audio/wav',
        },
        timeout: 60000,
        maxContentLength: 10 * 1024 * 1024,
      }
    );

    const text = response.data?.text || response.data?._text || '';
    if (!text) throw new Error('Empty Wit.ai response');

    return {
      text,
      language: 'auto',
      confidence: response.data?.confidence || response.data?.speech?.confidence || 0.9,
    };
  } finally {
    if (fs.existsSync(wavPath)) fs.unlinkSync(wavPath);
  }
}

async function sttWithWhisper(audioPath: string): Promise<STTResult> {
  try {
    const { stdout } = await execAsync(
      `whisper "${audioPath}" --model tiny --language auto --output_format txt`,
      { timeout: 120000 }
    );

    return {
      text: stdout.trim(),
      language: 'auto',
      confidence: 0.7,
    };
  } catch {
    throw new Error('Whisper STT not available');
  }
}

async function convertToWav(inputPath: string): Promise<string> {
  const wavPath = generateTempPath('wav');

  await execAsync(
    `ffmpeg -i "${inputPath}" -acodec pcm_s16le -ar 16000 -ac 1 -y "${wavPath}"`,
    { timeout: 30000 }
  );

  if (!fs.existsSync(wavPath)) {
    throw new Error('Failed to convert audio to WAV');
  }

  return wavPath;
}
