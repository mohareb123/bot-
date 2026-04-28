import { Router } from 'express';
import { User } from '../../models/User';

export const userRoutes = Router();

userRoutes.get('/', async (req, res) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 20;
    const search = req.query.search as string;

    const query: Record<string, unknown> = {};
    if (search) {
      query.$or = [
        { username: { $regex: search, $options: 'i' } },
        { firstName: { $regex: search, $options: 'i' } },
        { telegramId: parseInt(search) || 0 },
      ];
    }

    const [users, total] = await Promise.all([
      User.find(query)
        .sort({ lastActive: -1 })
        .skip((page - 1) * limit)
        .limit(limit),
      User.countDocuments(query),
    ]);

    res.json({ users, total, page, pages: Math.ceil(total / limit) });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch users' });
  }
});

userRoutes.get('/:telegramId', async (req, res) => {
  try {
    const user = await User.findOne({ telegramId: parseInt(req.params.telegramId) });
    if (!user) {
      res.status(404).json({ error: 'User not found' });
      return;
    }
    res.json(user);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch user' });
  }
});

userRoutes.patch('/:telegramId/role', async (req, res) => {
  try {
    const { role } = req.body;
    if (!['user', 'admin', 'superadmin', 'banned'].includes(role)) {
      res.status(400).json({ error: 'Invalid role' });
      return;
    }

    const user = await User.findOneAndUpdate(
      { telegramId: parseInt(req.params.telegramId) },
      { role },
      { new: true }
    );

    if (!user) {
      res.status(404).json({ error: 'User not found' });
      return;
    }
    res.json(user);
  } catch (err) {
    res.status(500).json({ error: 'Failed to update user role' });
  }
});
