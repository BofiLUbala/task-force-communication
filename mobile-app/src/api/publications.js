import client from './client';

/**
 * The mobile app reads the very same feed endpoint as the web app.
 *
 * There is no mobile-specific publication store and no mobile-specific
 * filtering: the server resolves the audience once and returns only what the
 * signed-in account is entitled to see. Anything this file did differently
 * would be a second, divergent definition of "who is concerned".
 */
export async function fetchFeed({ unreadOnly = false } = {}) {
  const { data } = await client.get('/publications/feed/', {
    params: unreadOnly ? { unread: 1 } : undefined,
  });
  return {
    posts: data.results || [],
    unreadCount: data.unread_count || 0,
  };
}

export async function fetchPublication(slug) {
  const { data } = await client.get(`/publications/${slug}/`);
  return data;
}

export async function markRead(slug) {
  // Best effort: failing to record a read must never block reading.
  try {
    await client.post(`/publications/${slug}/mark-read/`);
  } catch {
    // ignored on purpose
  }
}

export const TYPE_LABELS = {
  ACTUALITE: 'Actualité',
  COMMUNIQUE: 'Communiqué',
  ACTIVITE: 'Activité',
  NEWSLETTER: 'Newsletter',
};

export function relativeTime(value) {
  if (!value) return '';
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  return `il y a ${Math.round(hours / 24)} j`;
}

export function previewText(post) {
  if (post.excerpt) return post.excerpt;
  return (post.body || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

export function coverOf(post) {
  if (post.cover_image) return post.cover_image;
  const photo = (post.gallery || []).find((item) => item.media_type === 'PHOTO');
  return photo ? photo.file : '';
}

export function splitAttachments(post) {
  const gallery = post.gallery || [];
  return {
    photos: gallery.filter((item) => item.media_type === 'PHOTO'),
    videos: gallery.filter((item) => item.media_type === 'VIDEO'),
    documents: gallery.filter((item) => item.media_type === 'DOCUMENT'),
  };
}
