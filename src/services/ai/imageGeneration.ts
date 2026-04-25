import axios from 'axios';
import { config } from '../../config';
import { logger } from '../../utils/logger';
import { generateTempPath } from '../../utils/helpers';
import fs from 'fs';

export interface ImageGenResult {
  imagePath: string;
  prompt: string;
  provider: string;
}

export async function generateImage(prompt: string): Promise<ImageGenResult> {
  const providers = [
    () => generateWithPollinations(prompt),
    () => generateWithHuggingFace(prompt),
  ];

  for (const provider of providers) {
    try {
      return await provider();
    } catch (err) {
      logger.warn('Image generation provider failed:', err);
      continue;
    }
  }

  throw new Error('All image generation providers failed');
}

async function generateWithPollinations(prompt: string): Promise<ImageGenResult> {
  const encodedPrompt = encodeURIComponent(prompt);
  const url = `https://image.pollinations.ai/prompt/${encodedPrompt}?width=1024&height=1024&nologo=true`;

  const response = await axios.get(url, {
    responseType: 'arraybuffer',
    timeout: 120000,
  });

  const imagePath = generateTempPath('png');
  fs.writeFileSync(imagePath, response.data);

  return { imagePath, prompt, provider: 'pollinations' };
}

async function generateWithHuggingFace(prompt: string): Promise<ImageGenResult> {
  if (!config.huggingfaceApiKey) throw new Error('HuggingFace API key not configured');

  const response = await axios.post(
    'https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0',
    { inputs: prompt },
    {
      headers: { Authorization: `Bearer ${config.huggingfaceApiKey}` },
      responseType: 'arraybuffer',
      timeout: 120000,
    }
  );

  const imagePath = generateTempPath('png');
  fs.writeFileSync(imagePath, response.data);

  return { imagePath, prompt, provider: 'huggingface' };
}

export async function editImage(imagePath: string, prompt: string): Promise<ImageGenResult> {
  const imageData = fs.readFileSync(imagePath);
  const base64 = imageData.toString('base64');

  try {
    if (config.geminiApiKey) {
      const response = await axios.post(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${config.geminiApiKey}`,
        {
          contents: [{
            parts: [
              { text: `Edit this image: ${prompt}. Describe the result in detail.` },
              { inlineData: { mimeType: 'image/png', data: base64 } },
            ],
          }],
        },
        { timeout: 60000 }
      );

      const description = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
      if (description) {
        return generateImage(`${prompt}, ${description}`);
      }
    }
  } catch (err) {
    logger.warn('Image edit with Gemini failed:', err);
  }

  return generateImage(prompt);
}
