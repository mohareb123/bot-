import { Telegraf, Markup } from 'telegraf';
import { BotContext } from '../types';
import { adminMenuKeyboard, groupSettingsKeyboard, paginationKeyboard } from '../utils/keyboard';
import { editMessage } from '../utils/messages';
import { User } from '../models/User';
import { Group } from '../models/Group';
import { Channel } from '../models/Channel';
import { Plugin } from '../models/Plugin';
import { Log } from '../models/Log';
import { logger } from '../utils/logger';

const ITEMS_PER_PAGE = 5;

export function registerAdminHandlers(bot: Telegraf<BotContext>): void {
  bot.command('admin', async (ctx) => {
    if (!ctx.isAdmin) {
      await ctx.reply('⛔ ليس لديك صلاحية الوصول لهذه اللوحة.');
      return;
    }

    const totalUsers = await User.countDocuments();
    const totalGroups = await Group.countDocuments({ isActive: true });
    const totalChannels = await Channel.countDocuments();
    const todayLogs = await Log.countDocuments({
      timestamp: { $gte: new Date(new Date().setHours(0, 0, 0, 0)) },
    });

    await ctx.reply(
      `🎛️ <b>لوحة التحكم</b>\n\n` +
      `👤 المستخدمين: <b>${totalUsers}</b>\n` +
      `👥 المجموعات النشطة: <b>${totalGroups}</b>\n` +
      `📢 القنوات: <b>${totalChannels}</b>\n` +
      `📊 عمليات اليوم: <b>${todayLogs}</b>`,
      { parse_mode: 'HTML', ...adminMenuKeyboard() }
    );
  });

  // Groups management
  bot.action('admin_groups', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    await showGroupsList(ctx, 1);
  });

  bot.action(/admin_groups_page_(\d+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const page = parseInt(ctx.match[1]);
    await showGroupsList(ctx, page);
  });

  bot.action(/group_toggle_ai_(-?\d+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const chatId = parseInt(ctx.match[1]);
    const group = await Group.findOne({ chatId });
    if (group) {
      group.settings.aiEnabled = !group.settings.aiEnabled;
      await group.save();
      await ctx.answerCbQuery(`الذكاء الاصطناعي: ${group.settings.aiEnabled ? '✅ مفعل' : '❌ معطل'}`);
      await showGroupSettings(ctx, chatId);
    }
  });

  bot.action(/group_toggle_media_(-?\d+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const chatId = parseInt(ctx.match[1]);
    const group = await Group.findOne({ chatId });
    if (group) {
      group.settings.mediaEnabled = !group.settings.mediaEnabled;
      await group.save();
      await ctx.answerCbQuery(`تحميل الوسائط: ${group.settings.mediaEnabled ? '✅ مفعل' : '❌ معطل'}`);
      await showGroupSettings(ctx, chatId);
    }
  });

  bot.action(/group_toggle_voice_(-?\d+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const chatId = parseInt(ctx.match[1]);
    const group = await Group.findOne({ chatId });
    if (group) {
      group.settings.voiceEnabled = !group.settings.voiceEnabled;
      await group.save();
      await ctx.answerCbQuery(`الصوت: ${group.settings.voiceEnabled ? '✅ مفعل' : '❌ معطل'}`);
      await showGroupSettings(ctx, chatId);
    }
  });

  bot.action(/group_settings_(-?\d+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const chatId = parseInt(ctx.match[1]);
    await showGroupSettings(ctx, chatId);
  });

  // Channels management
  bot.action('admin_channels', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    await showChannelsList(ctx);
  });

  bot.command('addchannel', async (ctx) => {
    if (!ctx.isAdmin) return;
    const username = ctx.message.text.replace(/^\/addchannel(@\w+)?\s*@?/, '').trim();
    if (!username) {
      await ctx.reply('📢 استخدم: <code>/addchannel [username]</code>', { parse_mode: 'HTML' });
      return;
    }

    try {
      await Channel.findOneAndUpdate(
        { username },
        { username, isRequired: true, addedAt: new Date() },
        { upsert: true, new: true }
      );
      await ctx.reply(`✅ تم إضافة القناة @${username} للاشتراك الإجباري.`);
    } catch (err) {
      logger.error('Add channel error:', err);
      await ctx.reply('❌ فشل إضافة القناة.');
    }
  });

  bot.command('removechannel', async (ctx) => {
    if (!ctx.isAdmin) return;
    const username = ctx.message.text.replace(/^\/removechannel(@\w+)?\s*@?/, '').trim();
    if (!username) {
      await ctx.reply('📢 استخدم: <code>/removechannel [username]</code>', { parse_mode: 'HTML' });
      return;
    }

    await Channel.deleteOne({ username });
    await ctx.reply(`✅ تم حذف القناة @${username}.`);
  });

  bot.action(/channel_toggle_(.+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const username = ctx.match[1];
    const channel = await Channel.findOne({ username });
    if (channel) {
      channel.isRequired = !channel.isRequired;
      await channel.save();
      await ctx.answerCbQuery(`${channel.isRequired ? '✅ مفعل' : '❌ معطل'}`);
      await showChannelsList(ctx);
    }
  });

  // Users management
  bot.action('admin_users', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    await showUsersList(ctx, 1);
  });

  bot.action(/admin_users_page_(\d+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const page = parseInt(ctx.match[1]);
    await showUsersList(ctx, page);
  });

  bot.command('promote', async (ctx) => {
    if (!ctx.isAdmin) return;
    const targetId = parseInt(ctx.message.text.replace(/^\/promote(@\w+)?\s*/, '').trim());
    if (!targetId) {
      await ctx.reply('استخدم: <code>/promote [user_id]</code>', { parse_mode: 'HTML' });
      return;
    }

    const user = await User.findOne({ telegramId: targetId });
    if (!user) {
      await ctx.reply('❌ المستخدم غير موجود.');
      return;
    }
    user.role = 'admin';
    await user.save();
    await ctx.reply(`✅ تم ترقية المستخدم ${user.firstName} إلى أدمن.`);
  });

  bot.command('demote', async (ctx) => {
    if (!ctx.isAdmin) return;
    const targetId = parseInt(ctx.message.text.replace(/^\/demote(@\w+)?\s*/, '').trim());
    if (!targetId) {
      await ctx.reply('استخدم: <code>/demote [user_id]</code>', { parse_mode: 'HTML' });
      return;
    }

    const user = await User.findOne({ telegramId: targetId });
    if (!user) {
      await ctx.reply('❌ المستخدم غير موجود.');
      return;
    }
    user.role = 'user';
    await user.save();
    await ctx.reply(`✅ تم تخفيض رتبة المستخدم ${user.firstName}.`);
  });

  bot.command('ban', async (ctx) => {
    if (!ctx.isAdmin) return;
    const targetId = parseInt(ctx.message.text.replace(/^\/ban(@\w+)?\s*/, '').trim());
    if (!targetId) {
      await ctx.reply('استخدم: <code>/ban [user_id]</code>', { parse_mode: 'HTML' });
      return;
    }

    const user = await User.findOne({ telegramId: targetId });
    if (!user) {
      await ctx.reply('❌ المستخدم غير موجود.');
      return;
    }
    user.role = 'banned';
    await user.save();
    await ctx.reply(`✅ تم حظر المستخدم ${user.firstName}.`);
  });

  bot.command('unban', async (ctx) => {
    if (!ctx.isAdmin) return;
    const targetId = parseInt(ctx.message.text.replace(/^\/unban(@\w+)?\s*/, '').trim());
    if (!targetId) {
      await ctx.reply('استخدم: <code>/unban [user_id]</code>', { parse_mode: 'HTML' });
      return;
    }

    const user = await User.findOne({ telegramId: targetId });
    if (!user) {
      await ctx.reply('❌ المستخدم غير موجود.');
      return;
    }
    user.role = 'user';
    await user.save();
    await ctx.reply(`✅ تم إلغاء حظر المستخدم ${user.firstName}.`);
  });

  // Plugins management
  bot.action('admin_plugins', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    await showPluginsList(ctx);
  });

  bot.action(/plugin_toggle_(.+)/, async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const pluginName = ctx.match[1];
    const plugin = await Plugin.findOne({ name: pluginName });
    if (plugin) {
      plugin.isActive = !plugin.isActive;
      await plugin.save();
      await ctx.answerCbQuery(`${plugin.isActive ? '✅ مفعل' : '❌ معطل'}`);
      await showPluginsList(ctx);
    }
  });

  // Stats
  bot.action('admin_stats', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    await showStats(ctx);
  });

  // Settings
  bot.action('admin_settings', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    await ctx.editMessageText(
      '⚙️ <b>الإعدادات العامة:</b>\n\n' +
      'استخدم الأوامر التالية:\n\n' +
      '/addchannel [username] - إضافة قناة\n' +
      '/removechannel [username] - حذف قناة\n' +
      '/promote [user_id] - ترقية لأدمن\n' +
      '/demote [user_id] - تخفيض رتبة\n' +
      '/ban [user_id] - حظر مستخدم\n' +
      '/unban [user_id] - إلغاء حظر\n' +
      '/broadcast [رسالة] - بث رسالة للجميع',
      { parse_mode: 'HTML', ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'admin_main')]]) }
    );
  });

  bot.action('admin_main', async (ctx) => {
    if (!ctx.isAdmin) return ctx.answerCbQuery('⛔ غير مصرح');
    const totalUsers = await User.countDocuments();
    const totalGroups = await Group.countDocuments({ isActive: true });
    const totalChannels = await Channel.countDocuments();
    const todayLogs = await Log.countDocuments({
      timestamp: { $gte: new Date(new Date().setHours(0, 0, 0, 0)) },
    });

    await ctx.editMessageText(
      `🎛️ <b>لوحة التحكم</b>\n\n` +
      `👤 المستخدمين: <b>${totalUsers}</b>\n` +
      `👥 المجموعات النشطة: <b>${totalGroups}</b>\n` +
      `📢 القنوات: <b>${totalChannels}</b>\n` +
      `📊 عمليات اليوم: <b>${todayLogs}</b>`,
      { parse_mode: 'HTML', ...adminMenuKeyboard() }
    );
  });

  // Broadcast
  bot.command('broadcast', async (ctx) => {
    if (!ctx.isAdmin) return;
    const message = ctx.message.text.replace(/^\/broadcast(@\w+)?\s*/, '').trim();
    if (!message) {
      await ctx.reply('📣 استخدم: <code>/broadcast [الرسالة]</code>', { parse_mode: 'HTML' });
      return;
    }

    const users = await User.find({ role: { $ne: 'banned' } });
    let success = 0;
    let failed = 0;

    const statusMsg = await ctx.reply(`📣 جاري البث... (0/${users.length})`);

    for (const user of users) {
      try {
        await ctx.telegram.sendMessage(user.telegramId, message, { parse_mode: 'HTML' });
        success++;
      } catch {
        failed++;
      }

      if ((success + failed) % 20 === 0) {
        try {
          await ctx.telegram.editMessageText(
            ctx.chat!.id,
            statusMsg.message_id,
            undefined,
            `📣 جاري البث... (${success + failed}/${users.length})`
          );
        } catch {
          // ignore
        }
      }
    }

    await editMessage(
      ctx,
      statusMsg.message_id,
      `✅ <b>تم البث!</b>\n\n✅ نجح: ${success}\n❌ فشل: ${failed}`
    );
  });
}

async function showGroupsList(ctx: BotContext, page: number): Promise<void> {
  const total = await Group.countDocuments();
  const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE));
  const groups = await Group.find()
    .sort({ isActive: -1, joinedAt: -1 })
    .skip((page - 1) * ITEMS_PER_PAGE)
    .limit(ITEMS_PER_PAGE);

  let text = `👥 <b>المجموعات</b> (${total}):\n\n`;
  for (const group of groups) {
    text += `${group.isActive ? '🟢' : '🔴'} <b>${group.title || group.chatId}</b>\n`;
    text += `   ID: <code>${group.chatId}</code>\n`;
    text += `   📊 رسائل: ${group.stats.totalMessages} | AI: ${group.stats.aiRequests}\n\n`;
  }

  const buttons = groups.map(g =>
    [Markup.button.callback(`⚙️ ${g.title || g.chatId}`, `group_settings_${g.chatId}`)]
  );

  if (totalPages > 1) {
    buttons.push(paginationKeyboard(page, totalPages, 'admin_groups'));
  }
  buttons.push([Markup.button.callback('🔙 رجوع', 'admin_main')]);

  try {
    await ctx.editMessageText(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  } catch {
    await ctx.reply(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  }
  await ctx.answerCbQuery();
}

async function showGroupSettings(ctx: BotContext, chatId: number): Promise<void> {
  const group = await Group.findOne({ chatId });
  if (!group) return;

  await ctx.editMessageText(
    `⚙️ <b>إعدادات المجموعة:</b>\n\n` +
    `📝 الاسم: ${group.title}\n` +
    `🆔 ID: <code>${group.chatId}</code>\n` +
    `📊 الرسائل: ${group.stats.totalMessages}\n` +
    `🤖 طلبات AI: ${group.stats.aiRequests}\n` +
    `📥 تحميلات: ${group.stats.mediaDownloads}`,
    { parse_mode: 'HTML', ...groupSettingsKeyboard(chatId, group.settings) }
  );
  await ctx.answerCbQuery();
}

async function showChannelsList(ctx: BotContext): Promise<void> {
  const channels = await Channel.find().sort({ addedAt: -1 });

  let text = `📢 <b>القنوات</b> (${channels.length}):\n\n`;
  for (const ch of channels) {
    text += `${ch.isRequired ? '✅' : '❌'} @${ch.username}`;
    if (ch.title) text += ` - ${ch.title}`;
    text += '\n';
  }

  if (channels.length === 0) {
    text += 'لا توجد قنوات مضافة.\n';
  }

  text += '\n/addchannel [username] - إضافة قناة\n/removechannel [username] - حذف قناة';

  const buttons = channels.map(ch =>
    [Markup.button.callback(`${ch.isRequired ? '✅' : '❌'} @${ch.username}`, `channel_toggle_${ch.username}`)]
  );
  buttons.push([Markup.button.callback('🔙 رجوع', 'admin_main')]);

  try {
    await ctx.editMessageText(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  } catch {
    await ctx.reply(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  }
  await ctx.answerCbQuery();
}

async function showUsersList(ctx: BotContext, page: number): Promise<void> {
  const total = await User.countDocuments();
  const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE));
  const users = await User.find()
    .sort({ lastActive: -1 })
    .skip((page - 1) * ITEMS_PER_PAGE)
    .limit(ITEMS_PER_PAGE);

  let text = `👤 <b>المستخدمين</b> (${total}):\n\n`;
  for (const user of users) {
    const roleEmoji = { user: '👤', admin: '👑', superadmin: '🌟', banned: '🚫' };
    text += `${roleEmoji[user.role] || '👤'} <b>${user.firstName || 'N/A'}</b>`;
    if (user.username) text += ` (@${user.username})`;
    text += `\n   ID: <code>${user.telegramId}</code> | طلبات: ${user.totalRequests}\n\n`;
  }

  const buttons = [];
  if (totalPages > 1) {
    buttons.push(paginationKeyboard(page, totalPages, 'admin_users'));
  }
  buttons.push([Markup.button.callback('🔙 رجوع', 'admin_main')]);

  try {
    await ctx.editMessageText(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  } catch {
    await ctx.reply(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  }
  await ctx.answerCbQuery();
}

async function showPluginsList(ctx: BotContext): Promise<void> {
  const plugins = await Plugin.find().sort({ addedAt: -1 });

  let text = `🧩 <b>الإضافات</b> (${plugins.length}):\n\n`;
  for (const plugin of plugins) {
    text += `${plugin.isActive ? '✅' : '❌'} <b>${plugin.name}</b> v${plugin.version}\n`;
    text += `   ${plugin.description}\n\n`;
  }

  if (plugins.length === 0) {
    text += 'لا توجد إضافات مثبتة حالياً.\n';
  }

  const buttons = plugins.map(p =>
    [Markup.button.callback(`${p.isActive ? '✅' : '❌'} ${p.name}`, `plugin_toggle_${p.name}`)]
  );
  buttons.push([Markup.button.callback('🔙 رجوع', 'admin_main')]);

  try {
    await ctx.editMessageText(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  } catch {
    await ctx.reply(text, { parse_mode: 'HTML', ...Markup.inlineKeyboard(buttons) });
  }
  await ctx.answerCbQuery();
}

async function showStats(ctx: BotContext): Promise<void> {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const week = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  const [totalUsers, newToday, activeWeek, totalGroups, totalLogs, todayLogs] = await Promise.all([
    User.countDocuments(),
    User.countDocuments({ joinedAt: { $gte: today } }),
    User.countDocuments({ lastActive: { $gte: week } }),
    Group.countDocuments({ isActive: true }),
    Log.countDocuments(),
    Log.countDocuments({ timestamp: { $gte: today } }),
  ]);

  const actionStats = await Log.aggregate([
    { $match: { timestamp: { $gte: today } } },
    { $group: { _id: '$action', count: { $sum: 1 } } },
    { $sort: { count: -1 } },
    { $limit: 10 },
  ]);

  let text = `📊 <b>الإحصائيات:</b>\n\n`;
  text += `👤 إجمالي المستخدمين: <b>${totalUsers}</b>\n`;
  text += `🆕 مستخدمين اليوم: <b>${newToday}</b>\n`;
  text += `📱 نشطين هذا الأسبوع: <b>${activeWeek}</b>\n`;
  text += `👥 المجموعات النشطة: <b>${totalGroups}</b>\n`;
  text += `📊 إجمالي العمليات: <b>${totalLogs}</b>\n`;
  text += `📊 عمليات اليوم: <b>${todayLogs}</b>\n`;

  if (actionStats.length > 0) {
    text += `\n📈 <b>أكثر العمليات اليوم:</b>\n`;
    for (const stat of actionStats) {
      text += `  • ${stat._id}: ${stat.count}\n`;
    }
  }

  await ctx.editMessageText(text, {
    parse_mode: 'HTML',
    ...Markup.inlineKeyboard([[Markup.button.callback('🔙 رجوع', 'admin_main')]]),
  });
  await ctx.answerCbQuery();
}
