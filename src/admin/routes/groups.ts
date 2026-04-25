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
    const group = await Group.findOneAndUpdate(
      { chatId: parseInt(req.params.chatId) },
      req.body,
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
