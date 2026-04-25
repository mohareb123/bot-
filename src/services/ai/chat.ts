import axios from 'axios';
import { AIProvider, ChatMessage } from '../../types';
import { config } from '../../config';
import { logger } from '../../utils/logger';

export class GeminiProvider implements AIProvider {
  name = 'gemini';

  async isAvailable(): Promise<boolean> {
    return !!config.geminiApiKey;
  }

  async chat(prompt: string, history: ChatMessage[] = []): Promise<string> {
    const contents = history.map(msg => ({
      role: msg.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: msg.content }],
    }));
    contents.push({ role: 'user', parts: [{ text: prompt }] });

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${config.geminiApiKey}`,
      {
        contents,
        generationConfig: {
          temperature: 0.7,
          maxOutputTokens: 2048,
          topP: 0.9,
        },
        safetySettings: [
          { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_NONE' },
          { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_NONE' },
          { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_NONE' },
          { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_NONE' },
        ],
      },
      { timeout: 30000 }
    );

    const text = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error('Empty Gemini response');
    return text;
  }

  async analyzeImage(imageUrl: string, prompt = 'صف هذه الصورة بالتفصيل'): Promise<string> {
    const imageResponse = await axios.get(imageUrl, { responseType: 'arraybuffer', timeout: 30000 });
    const base64Image = Buffer.from(imageResponse.data).toString('base64');
    const mimeType = imageResponse.headers['content-type'] || 'image/jpeg';

    const response = await axios.post(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${config.geminiApiKey}`,
      {
        contents: [{
          parts: [
            { text: prompt },
            { inlineData: { mimeType, data: base64Image } },
          ],
        }],
        generationConfig: {
          temperature: 0.4,
          maxOutputTokens: 2048,
        },
      },
      { timeout: 60000 }
    );

    const text = response.data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error('Empty Gemini vision response');
    return text;
  }
}

export class OpenAICompatibleProvider implements AIProvider {
  name = 'openai-compatible';

  async isAvailable(): Promise<boolean> {
    return !!config.openaiApiKey && !!config.openaiBaseUrl;
  }

  async chat(prompt: string, history: ChatMessage[] = []): Promise<string> {
    const messages = [
      { role: 'system', content: 'أنت مساعد ذكي ومفيد. أجب بوضوح ودقة.' },
      ...history,
      { role: 'user', content: prompt },
    ];

    const response = await axios.post(
      `${config.openaiBaseUrl}/chat/completions`,
      {
        model: 'gpt-3.5-turbo',
        messages,
        temperature: 0.7,
        max_tokens: 2048,
      },
      {
        headers: { Authorization: `Bearer ${config.openaiApiKey}` },
        timeout: 30000,
      }
    );

    return response.data?.choices?.[0]?.message?.content || '';
  }

  async analyzeImage(_imageUrl: string, _prompt?: string): Promise<string> {
    throw new Error('Image analysis not supported by this provider');
  }
}

export class FreeAIProvider implements AIProvider {
  name = 'free-fallback';

  async isAvailable(): Promise<boolean> {
    return true;
  }

  async chat(prompt: string, _history: ChatMessage[] = []): Promise<string> {
    try {
      const response = await axios.post(
        'https://text.pollinations.ai/',
        prompt,
        {
          headers: { 'Content-Type': 'text/plain' },
          timeout: 30000,
        }
      );
      return typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
    } catch (err) {
      logger.warn('Free AI fallback failed:', err);
      throw err;
    }
  }

  async analyzeImage(_imageUrl: string, _prompt?: string): Promise<string> {
    throw new Error('Image analysis not available in free fallback');
  }
}
