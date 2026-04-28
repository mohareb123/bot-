import { Router } from 'express';
import { User } from '../../models/User';
import { Group } from '../../models/Group';
import { Channel } from '../../models/Channel';
import { Log } from '../../models/Log';

export const statsRoutes = Router();

statsRoutes.get('/', async (_req, res) => {
  try {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const week = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const month = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const [
      totalUsers,
      newToday,
      activeWeek,
      totalGroups,
      activeGroups,
      totalChannels,
      totalLogs,
      todayLogs,
      weekLogs,
    ] = await Promise.all([
      User.countDocuments(),
      User.countDocuments({ joinedAt: { $gte: today } }),
      User.countDocuments({ lastActive: { $gte: week } }),
      Group.countDocuments(),
      Group.countDocuments({ isActive: true }),
      Channel.countDocuments(),
      Log.countDocuments(),
      Log.countDocuments({ timestamp: { $gte: today } }),
      Log.countDocuments({ timestamp: { $gte: week } }),
    ]);

    const topActions = await Log.aggregate([
      { $match: { timestamp: { $gte: today } } },
      { $group: { _id: '$action', count: { $sum: 1 } } },
      { $sort: { count: -1 } },
      { $limit: 10 },
    ]);

    const dailyStats = await Log.aggregate([
      { $match: { timestamp: { $gte: month } } },
      {
        $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$timestamp' } },
          count: { $sum: 1 },
        },
      },
      { $sort: { _id: 1 } },
    ]);

    res.json({
      users: { total: totalUsers, newToday, activeWeek },
      groups: { total: totalGroups, active: activeGroups },
      channels: { total: totalChannels },
      logs: { total: totalLogs, today: todayLogs, week: weekLogs },
      topActions,
      dailyStats,
    });
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});
