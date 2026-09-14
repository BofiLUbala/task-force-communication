"""What each destination can actually carry, and what a given post maps to.

The matrix below is deliberately conservative: it describes what *this*
application can publish with the OAuth scopes it actually requests (see
`oauth.py`), not everything the provider's API offers to approved partners.
Claiming a capability the token cannot exercise would just move the failure
from a clear pre-flight message to an opaque 403 at publish time.
"""
import re
from dataclasses import dataclass, field
from html import unescape

from django.conf import settings

WEBSITE = 'WEBSITE'
#: Canonical channel name used by `PublicationDelivery`. `WEBSITE` is the
#: historical spelling and stays accepted everywhere WEB is.
WEB = 'WEB'
MOBILE = 'MOBILE'
EMAIL = 'EMAIL'
WHATSAPP = 'WHATSAPP'

#: Channels this application delivers itself, so they never need an OAuth
#: connection to be considered available.
SELF_HOSTED = (WEBSITE, WEB, MOBILE)

#: Every distribution channel, in the order the composer displays them.
ALL_CHANNELS = (WEB, MOBILE, EMAIL, WHATSAPP, 'LINKEDIN', 'YOUTUBE')

#: A WhatsApp message is a short text; anything longer travels as a link.
WHATSAPP_TEXT_LIMIT = 900

#: LinkedIn multi-image shares cap out well below this; 9 is the safe ceiling.
LINKEDIN_MAX_IMAGES = 9


@dataclass
class Capability:
    text: bool = False
    rich_text: bool = False
    link: bool = False
    image: bool = False
    multiple_images: int = 0          # 0 = unsupported, N = max images
    video: bool = False
    multiple_videos: bool = False
    document: bool = False
    thumbnail: bool = False
    requires_video: bool = False


CAPABILITIES = {
    WEBSITE: Capability(
        text=True, rich_text=True, link=True, image=True, multiple_images=100,
        video=True, multiple_videos=True, document=True, thumbnail=True,
    ),
    # The mobile app renders the same publication object as the website, minus
    # the rich-text niceties the native renderer cannot lay out.
    MOBILE: Capability(
        text=True, rich_text=True, link=True, image=True, multiple_images=100,
        video=True, multiple_videos=True, document=True, thumbnail=True,
    ),
    # E-mail carries formatted text and inline images. Videos and other heavy
    # media are linked, never attached: a 200 Mo newsletter never arrives.
    EMAIL: Capability(
        text=True, rich_text=True, link=True, image=True, multiple_images=20,
        video=False, multiple_videos=False, document=True, thumbnail=True,
    ),
    # The open-wa bridge sends text; every attachment travels as the canonical
    # link back to the full publication.
    WHATSAPP: Capability(
        text=True, rich_text=False, link=True, image=False, multiple_images=0,
        video=False, multiple_videos=False, document=False, thumbnail=False,
    ),
    # Scopes requested: openid profile w_member_social (+ w_organization_social
    # when an organisation URN is configured). ugcPosts covers text, articles,
    # images and video. Native document shares need the versioned /rest/documents
    # API and a product this app is not approved for, so documents are excluded.
    'LINKEDIN': Capability(
        text=True, rich_text=False, link=True, image=True,
        multiple_images=LINKEDIN_MAX_IMAGES, video=True, multiple_videos=False,
        document=False, thumbnail=False,
    ),
    # Scopes requested: youtube.upload + youtube.readonly. A YouTube publication
    # *is* a video; everything else can only travel inside the description.
    'YOUTUBE': Capability(
        text=True, rich_text=False, link=True, image=False, multiple_images=0,
        video=True, multiple_videos=False, document=False, thumbnail=True,
        requires_video=True,
    ),
    'FACEBOOK': Capability(
        text=True, rich_text=False, link=True, image=False, multiple_images=0,
        video=False, document=False,
    ),
    'TIKTOK': Capability(
        text=True, rich_text=False, link=False, image=False, multiple_images=0,
        video=True, document=False, requires_video=True,
    ),
}

CAPABILITIES[WEB] = CAPABILITIES[WEBSITE]

PLATFORM_LABELS = {
    WEBSITE: 'Site Task Force',
    WEB: 'Application Web',
    MOBILE: 'Application mobile',
    EMAIL: 'E-mail',
    WHATSAPP: 'WhatsApp',
    'LINKEDIN': 'LinkedIn',
    'YOUTUBE': 'YouTube',
    'FACEBOOK': 'Facebook',
    'TIKTOK': 'TikTok',
}


def html_to_text(html):
    """Flatten rich text into plain text fit for a provider description field.

    Providers such as YouTube expect plain text; sending raw HTML would show
    the markup to viewers.
    """
    if not html:
        return ''
    text = re.sub(r'(?i)<br\s*/?>', '\n', html)
    text = re.sub(r'(?i)</\s*(p|div|li|h[1-6])\s*>', '\n', text)
    text = re.sub(r'(?i)<\s*li[^>]*>', '• ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


@dataclass
class Inventory:
    """Everything a publication actually carries, old and new storage alike."""

    title: str = ''
    text: str = ''
    images: list = field(default_factory=list)
    videos: list = field(default_factory=list)
    documents: list = field(default_factory=list)
    audios: list = field(default_factory=list)
    links: list = field(default_factory=list)
    cover = None
    legacy_attachment = None

    @property
    def has_text(self):
        return bool(self.text or self.title)

    @property
    def primary_video(self):
        return self.videos[0] if self.videos else None


def _looks_like_document(file_field):
    name = (getattr(file_field, 'name', '') or '').lower()
    return bool(name) and not name.endswith(
        ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.avi', '.webm')
    )


def build_inventory(post):
    """Collect a post's content, including the legacy single-file fields so
    publications created before the attachment model still publish correctly."""
    from ..models import PublicMedia

    inventory = Inventory(
        title=post.title or '',
        text=html_to_text(post.body) or (post.excerpt or ''),
    )

    for media in post.gallery.all():
        if media.media_type == PublicMedia.MediaType.PHOTO:
            inventory.images.append(media)
        elif media.media_type == PublicMedia.MediaType.VIDEO:
            inventory.videos.append(media)
        elif media.media_type == PublicMedia.MediaType.DOCUMENT:
            inventory.documents.append(media)
        elif media.media_type == PublicMedia.MediaType.AUDIO:
            inventory.audios.append(media)

    if getattr(post, 'cover_image', None):
        inventory.cover = post.cover_image

    # `attachment` predates PublicMedia.DOCUMENT and still holds the PDF of
    # every communiqué published so far.
    attachment = getattr(post, 'attachment', None)
    if attachment and _looks_like_document(attachment):
        inventory.legacy_attachment = attachment

    inventory.links = list(post.links.all())
    return inventory


def all_documents(inventory):
    """Documents from both the attachment model and the legacy field."""
    items = list(inventory.documents)
    if inventory.legacy_attachment:
        items.append(inventory.legacy_attachment)
    return items


@dataclass
class DestinationPlan:
    """What one destination will receive, and what it cannot take."""

    platform: str
    label: str
    available: bool = True
    connected: bool = True
    reason: str = ''
    included: list = field(default_factory=list)
    excluded: list = field(default_factory=list)

    def exclude(self, item, reason):
        self.excluded.append({'item': item, 'reason': reason})

    def as_dict(self):
        return {
            'platform': self.platform,
            'label': self.label,
            'available': self.available,
            'connected': self.connected,
            'reason': self.reason,
            'included': self.included,
            'excluded': self.excluded,
        }


def plan_destination(post, platform, connected=True, inventory=None):
    """Decide what `platform` receives from `post`, and say what it drops."""
    inventory = inventory or build_inventory(post)
    capability = CAPABILITIES.get(platform)
    label = PLATFORM_LABELS.get(platform, platform)

    if capability is None:
        return DestinationPlan(
            platform=platform, label=label, available=False, connected=connected,
            reason=f'Plateforme « {platform} » non prise en charge.',
        )

    plan = DestinationPlan(platform=platform, label=label, connected=connected)

    if platform not in SELF_HOSTED and not connected:
        plan.available = False
        plan.reason = f'Aucun compte {label} connecté.'
        return plan

    documents = all_documents(inventory)

    # A video-only destination cannot do anything with a post that has none.
    if capability.requires_video and not inventory.videos:
        plan.available = False
        plan.reason = f'La publication sur {label} nécessite une vidéo.'
        for item, kind in (
            (inventory.images, 'image(s)'), (documents, 'document(s)'),
        ):
            if item:
                plan.exclude(kind, f'{label} ne publie que des vidéos.')
        return plan

    if inventory.has_text and capability.text:
        plan.included.append('texte')

    if inventory.links:
        if capability.link:
            plan.included.append(f'{len(inventory.links)} lien(s)')
        else:
            plan.exclude('liens', f'{label} ne prend pas en charge les liens.')

    if inventory.images:
        if not capability.image:
            plan.exclude(
                f'{len(inventory.images)} image(s)',
                f'{label} ne publie pas d’images.',
            )
        else:
            maximum = max(capability.multiple_images, 1)
            kept = min(len(inventory.images), maximum)
            plan.included.append(f'{kept} image(s)')
            if len(inventory.images) > maximum:
                plan.exclude(
                    f'{len(inventory.images) - maximum} image(s) supplémentaire(s)',
                    f'{label} accepte au maximum {maximum} images par publication.',
                )

    if inventory.videos:
        if not capability.video:
            plan.exclude(
                f'{len(inventory.videos)} vidéo(s)', f'{label} ne publie pas de vidéos.',
            )
        else:
            plan.included.append('1 vidéo')
            if len(inventory.videos) > 1 and not capability.multiple_videos:
                plan.exclude(
                    f'{len(inventory.videos) - 1} vidéo(s) supplémentaire(s)',
                    f'{label} ne publie qu’une vidéo par publication ; la première est utilisée.',
                )

    if documents:
        if capability.document:
            plan.included.append(f'{len(documents)} document(s)')
        else:
            plan.exclude(
                f'{len(documents)} document(s)',
                f'La connexion {label} actuelle ne permet pas de publier des documents ; '
                'le lien vers la publication reste disponible.',
            )

    if inventory.cover and capability.thumbnail:
        plan.included.append('miniature')

    # LinkedIn and the website can carry an image-less or text-less post, but
    # something must remain to publish.
    if not plan.included:
        plan.available = False
        plan.reason = f'Aucun contenu compatible avec {label}.'

    return plan


def plan_publication(post, connected_platforms=None, targets=None):
    """Plan every destination at once, for the composer preview and for publish."""
    inventory = build_inventory(post)
    connected_platforms = set(connected_platforms or [])
    platforms = targets or list(ALL_CHANNELS)
    return {
        platform: plan_destination(
            post, platform,
            connected=(platform in SELF_HOSTED or platform in connected_platforms),
            inventory=inventory,
        )
        for platform in platforms
    }


def available_channels():
    """Channels the deployment can actually use right now.

    A channel whose provider is not configured is reported as unavailable
    up-front rather than accepted and then failed at send time.
    """
    from ..models import SocialAccount

    connected = set(
        SocialAccount.objects.filter(is_active=True).values_list('platform', flat=True)
    )
    if settings.EMAIL_HOST_USER or 'console' in settings.EMAIL_BACKEND or 'locmem' in settings.EMAIL_BACKEND:
        connected.add(EMAIL)
    if settings.OPENWA_ENABLED:
        connected.add(WHATSAPP)
    return connected


def whatsapp_message(post, post_url, inventory=None):
    """The WhatsApp representation: a headline, a trimmed body, and the link.

    Nothing important is dropped silently — whatever cannot travel in a
    WhatsApp message is still reachable through the publication link, which is
    always appended.
    """
    inventory = inventory or build_inventory(post)
    label = post.get_category_display().upper()
    body = inventory.text or ''
    room = WHATSAPP_TEXT_LIMIT - len(post_url) - len(label) - len(inventory.title) - 40
    if room > 0 and len(body) > room:
        body = body[:room].rsplit(' ', 1)[0].rstrip() + '…'
    elif room <= 0:
        body = ''

    parts = [f'*{label}*', inventory.title]
    if body:
        parts.append(body)
    parts.append('Lire la publication complète :\n' + post_url)
    return '\n\n'.join(part for part in parts if part)


def linkedin_author_urn(account):
    """Organisation page when configured, otherwise the connected member."""
    if settings.LINKEDIN_ORGANIZATION_URN:
        return f'urn:li:organization:{settings.LINKEDIN_ORGANIZATION_URN}'
    if account and account.external_account_id:
        return f'urn:li:person:{account.external_account_id}'
    return ''
