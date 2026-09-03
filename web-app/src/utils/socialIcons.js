const SOCIAL_ICONS = [
  { match: /facebook/i, icon: 'thumb_up', color: '#1877F2' },
  { match: /instagram/i, icon: 'photo_camera', color: '#E1306C' },
  { match: /twitter|^x$|\bx\b/i, icon: 'tag', color: '#000000' },
  { match: /youtube/i, icon: 'smart_display', color: '#FF0000' },
  { match: /linkedin/i, icon: 'work', color: '#0A66C2' },
  { match: /tiktok/i, icon: 'music_note', color: '#000000' },
  { match: /whatsapp/i, icon: 'chat', color: '#25D366' },
  { match: /telegram/i, icon: 'send', color: '#26A5E4' },
];

export function socialIconFor(name) {
  const found = SOCIAL_ICONS.find((entry) => entry.match.test(name || ''));
  return found || { icon: 'public', color: 'var(--primary)' };
}
