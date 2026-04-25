import { AIProvider, ChatMessage } from '../../types';
import { logger } from '../../utils/logger';

export class AIProviderManager {
  private providers: AIProvider[] = [];

  register(provider: AIProvider): void {
    this.providers.push(provider);
    logger.info(`AI provider registered: ${provider.name}`);
  }

  async chat(prompt: string, history?: ChatMessage[]): Promise<string> {
    for (const provider of this.providers) {
      try {
        const available = await provider.isAvailable();
        if (!available) continue;

        const result = await provider.chat(prompt, history);
        if (result) {
          logger.debug(`AI chat handled by: ${provider.name}`);
          return result;
        }
      } catch (err) {
        logger.warn(`AI provider ${provider.name} failed:`, err);
        continue;
      }
    }
    throw new Error('All AI providers failed');
  }

  async analyzeImage(imageUrl: string, prompt?: string): Promise<string> {
    for (const provider of this.providers) {
      try {
        const available = await provider.isAvailable();
        if (!available) continue;

        const result = await provider.analyzeImage(imageUrl, prompt);
        if (result) {
          logger.debug(`Image analysis handled by: ${provider.name}`);
          return result;
        }
      } catch (err) {
        logger.warn(`Image analysis provider ${provider.name} failed:`, err);
        continue;
      }
    }
    throw new Error('All image analysis providers failed');
  }
}

export const aiManager = new AIProviderManager();
