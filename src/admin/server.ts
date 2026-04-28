import express from 'express';
import { config } from '../config';
import { logger } from '../utils/logger';
import { groupRoutes } from './routes/groups';
import { channelRoutes } from './routes/channels';
import { userRoutes } from './routes/users';
import { pluginRoutes } from './routes/plugins';
import { statsRoutes } from './routes/stats';

export function createAdminServer(): express.Express {
  const app = express();

  app.use(express.json());

  // Auth middleware
  app.use('/api', (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || authHeader !== `Bearer ${config.adminPassword}`) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }
    next();
  });

  // Routes
  app.use('/api/groups', groupRoutes);
  app.use('/api/channels', channelRoutes);
  app.use('/api/users', userRoutes);
  app.use('/api/plugins', pluginRoutes);
  app.use('/api/stats', statsRoutes);

  // Health check
  app.get('/health', (_req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  return app;
}

export function startAdminServer(): void {
  const app = createAdminServer();
  app.listen(config.port, () => {
    logger.info(`Admin API server running on port ${config.port}`);
  });
}
