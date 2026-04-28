import { Router } from 'express';
import { Plugin } from '../../models/Plugin';

export const pluginRoutes = Router();

pluginRoutes.get('/', async (_req, res) => {
  try {
    const plugins = await Plugin.find().sort({ addedAt: -1 });
    res.json(plugins);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch plugins' });
  }
});

pluginRoutes.post('/', async (req, res) => {
  try {
    const { name, description, version, handler, settings } = req.body;
    const plugin = await Plugin.create({
      name,
      description,
      version: version || '1.0.0',
      handler,
      settings: settings || {},
      isActive: false,
    });
    res.json(plugin);
  } catch (err) {
    res.status(500).json({ error: 'Failed to create plugin' });
  }
});

pluginRoutes.patch('/:name/toggle', async (req, res) => {
  try {
    const plugin = await Plugin.findOne({ name: req.params.name });
    if (!plugin) {
      res.status(404).json({ error: 'Plugin not found' });
      return;
    }
    plugin.isActive = !plugin.isActive;
    await plugin.save();
    res.json(plugin);
  } catch (err) {
    res.status(500).json({ error: 'Failed to toggle plugin' });
  }
});

pluginRoutes.patch('/:name/settings', async (req, res) => {
  try {
    const plugin = await Plugin.findOneAndUpdate(
      { name: req.params.name },
      { settings: req.body },
      { new: true }
    );
    if (!plugin) {
      res.status(404).json({ error: 'Plugin not found' });
      return;
    }
    res.json(plugin);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update plugin settings' });
  }
});

pluginRoutes.delete('/:name', async (req, res) => {
  try {
    await Plugin.deleteOne({ name: req.params.name });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete plugin' });
  }
});
