import { Router } from 'express';
import { Group } from '../../models/Group';

export const groupRoutes = Router();

groupRoutes.get('/', async (_req, res) => {
  try {
    const groups = await Group.find().sort({ isActive: -1, joinedAt: -1 });
    res.json(groups);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch groups' });
  }
});

groupRoutes.get('/:chatId', async (req, res) => {
  try {
    const group = await Group.findOne({ chatId: parseInt(req.params.chatId) });
    if (!group) {
      res.status(404).json({ error: 'Group not found' });
      return;
    }
    res.json(group);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch group' });
  }
});

groupRoutes.patch('/:chatId', async (req, res) => {
  try {
    const allowedFields: Record<string, unknown> = {};
    const { title, isActive, settings } = req.body;
    if (title !== undefined) allowedFields.title = title;
    if (isActive !== undefined) allowedFields.isActive = isActive;
    if (settings) {
      const safe = ['aiEnabled', 'mediaEnabled', 'voiceEnabled', 'welcomeMessage', 'language'] as const;
      for (const key of safe) {
        if (settings[key] !== undefined) {
          allowedFields[`settings.${key}`] = settings[key];
        }
      }
    }

    const group = await Group.findOneAndUpdate(
      { chatId: parseInt(req.params.chatId) },
      { $set: allowedFields },
      { new: true }
    );
    if (!group) {
      res.status(404).json({ error: 'Group not found' });
      return;
    }
    res.json(group);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update group' });
  }
});

groupRoutes.patch('/:chatId/toggle', async (req, res) => {
  try {
    const group = await Group.findOne({ chatId: parseInt(req.params.chatId) });
    if (!group) {
      res.status(404).json({ error: 'Group not found' });
      return;
    }
    group.isActive = !group.isActive;
    await group.save();
    res.json(group);
  } catch (err) {
    res.status(500).json({ error: 'Failed to toggle group' });
  }
});
