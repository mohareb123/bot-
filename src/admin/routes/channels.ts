import { Router } from 'express';
import { Channel } from '../../models/Channel';

export const channelRoutes = Router();

channelRoutes.get('/', async (_req, res) => {
  try {
    const channels = await Channel.find().sort({ addedAt: -1 });
    res.json(channels);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch channels' });
  }
});

channelRoutes.post('/', async (req, res) => {
  try {
    const { username, title, isRequired } = req.body;
    const channel = await Channel.findOneAndUpdate(
      { username },
      { username, title, isRequired: isRequired !== false, addedAt: new Date() },
      { upsert: true, new: true }
    );
    res.json(channel);
  } catch (err) {
    res.status(500).json({ error: 'Failed to add channel' });
  }
});

channelRoutes.delete('/:username', async (req, res) => {
  try {
    await Channel.deleteOne({ username: req.params.username });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete channel' });
  }
});

channelRoutes.patch('/:username/toggle', async (req, res) => {
  try {
    const channel = await Channel.findOne({ username: req.params.username });
    if (!channel) {
      res.status(404).json({ error: 'Channel not found' });
      return;
    }
    channel.isRequired = !channel.isRequired;
    await channel.save();
    res.json(channel);
  } catch (err) {
    res.status(500).json({ error: 'Failed to toggle channel' });
  }
});
