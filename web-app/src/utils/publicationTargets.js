/**
 * Client-side mirror of the backend capability matrix
 * (`backend/content/social/capabilities.py`).
 *
 * The server stays the authority — it re-runs the same rules before sending
 * anything, and it is the server that decides who may receive a publication.
 * This copy exists so the composer can grey out an impossible destination the
 * moment a file is attached, instead of letting someone tick YouTube on a text
 * post and discover the problem only after publishing.
 */

export const LINKEDIN_MAX_IMAGES = 9;

/**
 * Channels nobody ticks: the author publishes once, and every connected
 * social provider that can carry the content receives it. Mirrors
 * `automatic_social_channels()` in `backend/content/channels.py`, which stays
 * the authority — the server adds these whatever the client sends.
 *
 * E-mail and WhatsApp are deliberately absent: a mass mailing is an explicit
 * act, so it keeps an explicit checkbox.
 */
export const AUTOMATIC_CHANNELS = ['LINKEDIN', 'YOUTUBE'];

export const isAutomaticChannel = (channel) => AUTOMATIC_CHANNELS.includes(channel);

export const CHANNELS = [
  { channel: 'WEB', label: 'Application Web', icon: 'public', selfHosted: true },
  { channel: 'MOBILE', label: 'Application mobile', icon: 'smartphone', selfHosted: true },
  { channel: 'EMAIL', label: 'E-mail', icon: 'mail' },
  { channel: 'WHATSAPP', label: 'WhatsApp', icon: 'chat' },
  { channel: 'LINKEDIN', label: 'LinkedIn', icon: 'work' },
  { channel: 'YOUTUBE', label: 'YouTube', icon: 'smart_display' },
];

/** Historical name for the WEB channel, still accepted by the API. */
export const TARGETS = CHANNELS;

const CAPABILITIES = {
  WEB: {
    text: true, link: true, image: true, maxImages: 100,
    video: true, multipleVideos: true, document: true, thumbnail: true,
  },
  MOBILE: {
    text: true, link: true, image: true, maxImages: 100,
    video: true, multipleVideos: true, document: true, thumbnail: true,
  },
  EMAIL: {
    text: true, link: true, image: true, maxImages: 20,
    video: false, multipleVideos: false, document: true, thumbnail: true,
  },
  WHATSAPP: {
    text: true, link: true, image: false, maxImages: 0,
    video: false, multipleVideos: false, document: false, thumbnail: false,
  },
  LINKEDIN: {
    text: true, link: true, image: true, maxImages: LINKEDIN_MAX_IMAGES,
    video: true, multipleVideos: false, document: false, thumbnail: false,
  },
  YOUTUBE: {
    text: true, link: true, image: false, maxImages: 0,
    video: true, multipleVideos: false, document: false, thumbnail: true,
    requiresVideo: true,
  },
};

/** What a channel drops rather than carries, phrased for the author. */
const LINKED_INSTEAD = 'le lien vers la publication complète reste inclus';

/**
 * @param {object} content  { hasText, images, videos, documents, links, hasCover }
 * @param {string[]} availableChannels  channels this deployment can use now
 * @returns {object[]} one plan per channel
 */
export function evaluateTargets(content, availableChannels = []) {
  const {
    hasText = false, images = 0, videos = 0, documents = 0, links = 0, hasCover = false,
  } = content;

  return CHANNELS.map(({ channel, label, icon, selfHosted }) => {
    const capability = CAPABILITIES[channel];
    const connected = Boolean(selfHosted) || availableChannels.includes(channel);
    const included = [];
    const excluded = [];

    if (!connected) {
      return {
        platform: channel, channel, label, icon, automatic: isAutomaticChannel(channel), connected: false, available: false,
        reason: `Indisponible — connectez ${label} d’abord.`, included, excluded,
      };
    }

    if (capability.requiresVideo && videos === 0) {
      if (images) excluded.push({ item: `${images} image(s)`, reason: `${label} ne publie que des vidéos.` });
      if (documents) excluded.push({ item: `${documents} document(s)`, reason: `${label} ne publie que des vidéos.` });
      return {
        platform: channel, channel, label, icon, automatic: isAutomaticChannel(channel), connected: true, available: false,
        reason: `Indisponible — ajoutez une vidéo.`, included, excluded,
      };
    }

    if (hasText && capability.text) included.push('texte');

    if (links) {
      if (capability.link) included.push(`${links} lien(s)`);
      else excluded.push({ item: 'liens', reason: `${label} ne prend pas en charge les liens.` });
    }

    if (images) {
      if (!capability.image) {
        excluded.push({
          item: `${images} image(s)`,
          reason: `${label} ne publie pas d’images ; ${LINKED_INSTEAD}.`,
        });
      } else {
        const maximum = Math.max(capability.maxImages, 1);
        const kept = Math.min(images, maximum);
        included.push(`${kept} image(s)`);
        if (images > maximum) {
          excluded.push({
            item: `${images - maximum} image(s) supplémentaire(s)`,
            reason: `${label} accepte au maximum ${maximum} images par publication.`,
          });
        }
      }
    }

    if (videos) {
      if (!capability.video) {
        excluded.push({
          item: `${videos} vidéo(s)`,
          reason: `${label} ne publie pas de vidéos ; ${LINKED_INSTEAD}.`,
        });
      } else {
        included.push('1 vidéo');
        if (videos > 1 && !capability.multipleVideos) {
          excluded.push({
            item: `${videos - 1} vidéo(s) supplémentaire(s)`,
            reason: `${label} ne publie qu’une vidéo ; la première est utilisée.`,
          });
        }
      }
    }

    if (documents) {
      if (capability.document) included.push(`${documents} document(s)`);
      else {
        excluded.push({
          item: `${documents} document(s)`,
          reason: `${label} ne permet pas de publier des documents ; ${LINKED_INSTEAD}.`,
        });
      }
    }

    if (hasCover && capability.thumbnail) included.push('miniature');

    return {
      platform: channel,
      channel,
      label,
      icon,
      automatic: isAutomaticChannel(channel),
      connected: true,
      available: included.length > 0,
      reason: included.length ? '' : `Aucun contenu compatible avec ${label}.`,
      included,
      excluded,
    };
  });
}

/**
 * What an automatic channel will do, phrased as a statement rather than a
 * choice — the author is being told, not asked.
 */
export function automaticStatus(plan) {
  if (!plan.connected) {
    return { tone: 'off', text: `Non connecté — ${plan.label} sera ignoré.` };
  }
  if (!plan.available) {
    const missing = CAPABILITIES[plan.channel]?.requiresVideo
      ? 'vidéo requise'
      : `aucun contenu compatible avec ${plan.label}`;
    return { tone: 'skip', text: `Connecté — ${missing}, sera ignoré.` };
  }
  return {
    tone: 'auto',
    text: `Connecté — publication automatique : ${plan.included.join(', ')}.`,
  };
}

export function classifyFile(file) {
  const type = file?.type || '';
  if (type.startsWith('image/')) return 'PHOTO';
  if (type.startsWith('video/')) return 'VIDEO';
  if (type.startsWith('audio/')) return 'AUDIO';
  return 'DOCUMENT';
}

export const MEDIA_LABELS = {
  PHOTO: 'Image',
  VIDEO: 'Vidéo',
  DOCUMENT: 'Document',
  AUDIO: 'Audio',
};

export const STATUS_LABELS = {
  SUCCESS: 'Réussi',
  SENT: 'Publié',
  FAILED: 'Échec',
  SKIPPED: 'Ignoré',
  PENDING: 'En attente',
  PROCESSING: 'En cours',
};

export const PUBLICATION_TYPES = [
  { value: 'ACTUALITE', label: 'Actualité' },
  { value: 'COMMUNIQUE', label: 'Communiqué' },
  { value: 'ACTIVITE', label: 'Activité' },
  { value: 'NEWSLETTER', label: 'Newsletter' },
];

export const AUDIENCES = [
  { value: 'EVERYONE', label: 'Tout le monde', hint: 'Visible aussi sur le site public.' },
  { value: 'ALL_AGENTS', label: 'Tous les agents', hint: 'Tous les agents de terrain actifs.' },
  { value: 'HIERARCHY_ONLY', label: 'Hiérarchie uniquement', hint: 'Contenu confidentiel.' },
  { value: 'SPECIFIC_GROUP', label: 'Une unité précise', hint: 'Choisissez l’unité concernée.' },
  { value: 'SPECIFIC_USERS', label: 'Des personnes précises', hint: 'Choisissez les destinataires.' },
];

/**
 * What each channel will actually send, phrased as a preview for the author.
 * Deliberately mirrors the backend adapters rather than the raw content: the
 * point of the preview is to show the transformation, not to hide it.
 */
export function channelPreview(plan, content) {
  if (!plan.available) return [];
  const rows = [...plan.included];
  if (plan.channel === 'WHATSAPP') {
    return ['titre', 'texte court', 'lien vers la publication complète'];
  }
  if (plan.channel === 'EMAIL' && (content.videos || content.documents)) {
    rows.push('liens vers les vidéos et documents');
  }
  if (plan.channel === 'YOUTUBE') {
    return ['la vidéo', 'le titre', 'la description', 'les liens de la publication'];
  }
  return rows;
}
