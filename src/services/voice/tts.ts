import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import axios from 'axios';
import { logger } from '../../utils/logger';
import { generateTempPath } from '../../utils/helpers';

const execAsync = promisify(exec);

export interface TTSVoice {
  id: string;
  name: string;
  language: string;
}

export const AVAILABLE_VOICES: TTSVoice[] = [
  { id: 'ar-EG-ShakirNeural', name: 'شاكر (مصري)', language: 'ar' },
  { id: 'ar-EG-SalmaNeural', name: 'سلمى (مصري)', language: 'ar' },
  { id: 'ar-SA-HamedNeural', name: 'حامد (سعودي)', language: 'ar' },
  { id: 'ar-SA-ZariyahNeural', name: 'زارية (سعودي)', language: 'ar' },
  { id: 'en-US-GuyNeural', name: 'Guy (English)', language: 'en' },
  { id: 'en-US-JennyNeural', name: 'Jenny (English)', language: 'en' },
  { id: 'en-GB-RyanNeural', name: 'Ryan (British)', language: 'en' },
  { id: 'fr-FR-HenriNeural', name: 'Henri (French)', language: 'fr' },
  { id: 'de-DE-ConradNeural', name: 'Conrad (German)', language: 'de' },
  { id: 'es-ES-AlvaroNeural', name: 'Alvaro (Spanish)', language: 'es' },
  { id: 'tr-TR-AhmetNeural', name: 'Ahmet (Turkish)', language: 'tr' },
];

export async function textToSpeech(text: string, voiceId = 'ar-EG-ShakirNeural'): Promise<string> {
  const providers = [
    () => ttsWithEdgeTTS(text, voiceId),
    () => ttsWithFreeAPI(text, voiceId),
  ];

  for (const provider of providers) {
    try {
      return await provider();
    } catch (err) {
      logger.warn('TTS provider failed:', err);
      continue;
    }
  }

  throw new Error('فشل تحويل النص إلى صوت');
}

async function ttsWithEdgeTTS(text: string, voiceId: string): Promise<string> {
  const outputPath = generateTempPath('mp3');
  const escapedText = text.replace(/"/g, '\\"').replace(/'/g, "\\'");

  try {
    await execAsync(
      `edge-tts --voice "${voiceId}" --text "${escapedText}" --write-media "${outputPath}"`,
      { timeout: 60000 }
    );

    if (!fs.existsSync(outputPath)) {
      throw new Error('edge-tts did not produce output');
    }

    return outputPath;
  } catch (err) {
    if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
    throw err;
  }
}

async function ttsWithFreeAPI(text: string, _voiceId: string): Promise<string> {
  const outputPath = generateTempPath('mp3');
  const lang = detectLanguage(text);

  const url = `https://translate.google.com/translate_tts?ie=UTF-8&q=${encodeURIComponent(text)}&tl=${lang}&client=tw-ob`;

  const response = await axios.get(url, {
    responseType: 'arraybuffer',
    timeout: 30000,
    headers: { 'User-Agent': 'Mozilla/5.0' },
  });

  fs.writeFileSync(outputPath, response.data);
  return outputPath;
}

function detectLanguage(text: string): string {
  const arabicRegex = /[\u0600-\u06FF]/;
  if (arabicRegex.test(text)) return 'ar';
  return 'en';
}
