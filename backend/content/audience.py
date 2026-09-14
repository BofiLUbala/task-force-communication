"""Who a publication is for, and who is therefore allowed to see it.

Every rule here is applied on the server. The web and mobile apps never decide
visibility for themselves: they ask for a feed and receive only the rows the
authenticated user is entitled to. Hiding a hierarchy-only communiqué with a
React condition would leave it one `curl` away from any agent.
"""
from django.db.models import Q

from .models import PublicPost

#: Roles that are considered "the hierarchy" for targeting purposes. The super
#: admin provisions the platform and is not an operational recipient, but it
#: must still be able to read what it administers.
HIERARCHY_ROLES = ('HIERARCHY', 'SUPER_ADMIN')

AUDIENCE_LABELS = {
    PublicPost.Audience.EVERYONE: 'Tout le monde',
    PublicPost.Audience.ALL_AGENTS: 'Tous les agents',
    PublicPost.Audience.HIERARCHY_ONLY: 'Hiérarchie uniquement',
    PublicPost.Audience.SPECIFIC_GROUP: 'Une unité précise',
    PublicPost.Audience.SPECIFIC_USERS: 'Des personnes précises',
}


def _active_users():
    from accounts.models import User
    return User.objects.filter(is_active=True, status=User.AccountStatus.ACTIVE)


def resolve_users(post):
    """Every account that should receive `post`, as a queryset.

    This single function is the source of truth for all four person-facing
    channels: the web feed, the mobile feed, e-mail and WhatsApp. They can
    therefore never disagree about who was concerned.
    """
    users = _active_users()
    audience = post.audience or PublicPost.Audience.EVERYONE

    if audience == PublicPost.Audience.ALL_AGENTS:
        return users.filter(role='AGENT')
    if audience == PublicPost.Audience.HIERARCHY_ONLY:
        return users.filter(role__in=HIERARCHY_ROLES)
    if audience == PublicPost.Audience.SPECIFIC_GROUP:
        if not post.audience_unit:
            return users.none()
        return users.filter(unit__iexact=post.audience_unit)
    if audience == PublicPost.Audience.SPECIFIC_USERS:
        return users.filter(targeted_publications=post)
    return users


def audience_size(post):
    return resolve_users(post).count()


def audience_description(post):
    """A human sentence for the confirmation screen and the detail page."""
    audience = post.audience or PublicPost.Audience.EVERYONE
    if audience == PublicPost.Audience.SPECIFIC_GROUP:
        return f'Unité « {post.audience_unit} »' if post.audience_unit else 'Unité non précisée'
    if audience == PublicPost.Audience.SPECIFIC_USERS:
        return f'{post.audience_users.count()} personne(s) désignée(s)'
    return AUDIENCE_LABELS.get(audience, audience)


def can_view(post, user):
    """Whether `user` may read this publication inside the apps."""
    if not (user and user.is_authenticated):
        # Anonymous visitors only ever see the public showcase, and only the
        # publications explicitly addressed to everyone.
        return post.is_published and post.audience == PublicPost.Audience.EVERYONE

    # Authors and the hierarchy see their own and all content respectively,
    # including drafts, because they are the people who manage it.
    if user.role in HIERARCHY_ROLES or post.published_by_id == user.id:
        return True
    if not post.is_published:
        return False
    return resolve_users(post).filter(pk=user.pk).exists()


def visibility_filter(user):
    """A `Q` object selecting the published publications `user` may read.

    Used for feeds and list endpoints, where evaluating `can_view` row by row
    would mean one query per publication.
    """
    everyone = Q(audience=PublicPost.Audience.EVERYONE)
    if not (user and user.is_authenticated):
        return everyone

    if user.role in HIERARCHY_ROLES:
        return Q()

    allowed = everyone | Q(audience_users=user)
    if user.role == 'AGENT':
        allowed |= Q(audience=PublicPost.Audience.ALL_AGENTS)
    if user.unit:
        allowed |= Q(
            audience=PublicPost.Audience.SPECIFIC_GROUP, audience_unit__iexact=user.unit,
        )
    return allowed


def feed_queryset(user):
    """The internal feed: published, audience-matched, newest first."""
    return (
        PublicPost.objects.filter(is_published=True)
        .filter(visibility_filter(user))
        .distinct()
        .select_related('published_by')
        .prefetch_related('gallery', 'links', 'deliveries')
        .order_by('-published_at', '-created_at')
    )


def email_recipients(post):
    """`(address, user, subscriber)` triples for the e-mail channel.

    Internal recipients come from the audience. Public newsletter subscribers
    are added only when the publication is addressed to everyone — a
    hierarchy-only note must never leak to a public mailing list.
    """
    from .models import NewsletterSubscriber

    seen = set()
    rows = []
    for user in resolve_users(post).exclude(email=''):
        address = user.email.strip().lower()
        if address and address not in seen:
            seen.add(address)
            rows.append((address, user, None))

    if post.audience == PublicPost.Audience.EVERYONE:
        for subscriber in NewsletterSubscriber.objects.filter(is_active=True):
            address = subscriber.email.strip().lower()
            if address and address not in seen:
                seen.add(address)
                rows.append((address, None, subscriber))
    return rows


def whatsapp_recipients(post):
    """`(phone, user)` pairs, plus the accounts that had to be skipped.

    Returns `(recipients, skipped)` so the delivery record can say *why*
    someone received nothing instead of silently under-delivering.
    """
    recipients, skipped, seen = [], [], set()
    for user in resolve_users(post):
        phone = (user.phone_number or '').strip()
        if not phone:
            skipped.append((user, 'NO_PHONE_NUMBER'))
            continue
        if phone in seen:
            continue
        seen.add(phone)
        recipients.append((phone, user))
    return recipients, skipped
