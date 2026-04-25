import { Markup } from 'telegraf';

export function mainMenuKeyboard() {
  return Markup.inlineKeyboard([
    [
      Markup.button.callback('🤖 الذكاء الاصطناعي', 'menu_ai'),
      Markup.button.callback('📥 تحميل الوسائط', 'menu_media'),
    ],
    [
      Markup.button.callback('🔊 تحويل النص لصوت', 'menu_tts'),
      Markup.button.callback('🎤 تحويل الصوت لنص', 'menu_stt'),
    ],
    [
      Markup.button.callback('🖼️ إنشاء صورة', 'menu_image_gen'),
      Markup.button.callback('📷 تحليل صورة', 'menu_image_analyze'),
    ],
    [
      Markup.button.callback('⚙️ الإعدادات', 'menu_settings'),
      Markup.button.callback('ℹ️ المساعدة', 'menu_help'),
    ],
  ]);
}

export function adminMenuKeyboard() {
  return Markup.inlineKeyboard([
    [
      Markup.button.callback('👥 إدارة المجموعات', 'admin_groups'),
      Markup.button.callback('📢 إدارة القنوات', 'admin_channels'),
    ],
    [
      Markup.button.callback('👤 إدارة المستخدمين', 'admin_users'),
      Markup.button.callback('🧩 الإضافات', 'admin_plugins'),
    ],
    [
      Markup.button.callback('📊 الإحصائيات', 'admin_stats'),
      Markup.button.callback('⚙️ الإعدادات العامة', 'admin_settings'),
    ],
    [Markup.button.callback('🔙 القائمة الرئيسية', 'back_main')],
  ]);
}

export function backButton(callbackData = 'back_main') {
  return Markup.inlineKeyboard([
    [Markup.button.callback('🔙 رجوع', callbackData)],
  ]);
}

export function subscriptionKeyboard(channels: { username: string; title: string }[]) {
  const urlButtons = channels.map(ch =>
    Markup.button.url(`📢 ${ch.title || ch.username}`, `https://t.me/${ch.username}`)
  );
  const checkButton = Markup.button.callback('✅ تحقق من الاشتراك', 'check_subscription');
  const rows = [...urlButtons.map(b => [b]), [checkButton]];
  return Markup.inlineKeyboard(rows);
}

export function mediaQualityKeyboard(qualities: { label: string; id: string }[]) {
  const buttons = qualities.map(q =>
    [Markup.button.callback(`📹 ${q.label}`, `quality_${q.id}`)]
  );
  buttons.push([Markup.button.callback('🎵 تحويل لـ MP3', 'convert_mp3')]);
  buttons.push([Markup.button.callback('🔙 رجوع', 'back_main')]);
  return Markup.inlineKeyboard(buttons);
}

export function confirmKeyboard(action: string) {
  return Markup.inlineKeyboard([
    [
      Markup.button.callback('✅ تأكيد', `confirm_${action}`),
      Markup.button.callback('❌ إلغاء', 'cancel'),
    ],
  ]);
}

export function paginationKeyboard(currentPage: number, totalPages: number, prefix: string) {
  const buttons = [];
  if (currentPage > 1) {
    buttons.push(Markup.button.callback('◀️ السابق', `${prefix}_page_${currentPage - 1}`));
  }
  buttons.push(Markup.button.callback(`${currentPage}/${totalPages}`, 'noop'));
  if (currentPage < totalPages) {
    buttons.push(Markup.button.callback('التالي ▶️', `${prefix}_page_${currentPage + 1}`));
  }
  return buttons;
}

export function groupSettingsKeyboard(chatId: number, settings: { aiEnabled: boolean; mediaEnabled: boolean; voiceEnabled: boolean }) {
  return Markup.inlineKeyboard([
    [Markup.button.callback(
      `${settings.aiEnabled ? '✅' : '❌'} الذكاء الاصطناعي`,
      `group_toggle_ai_${chatId}`
    )],
    [Markup.button.callback(
      `${settings.mediaEnabled ? '✅' : '❌'} تحميل الوسائط`,
      `group_toggle_media_${chatId}`
    )],
    [Markup.button.callback(
      `${settings.voiceEnabled ? '✅' : '❌'} الصوت`,
      `group_toggle_voice_${chatId}`
    )],
    [Markup.button.callback('🔙 رجوع', 'admin_groups')],
  ]);
}
