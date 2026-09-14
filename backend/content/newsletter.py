from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from .models import NewsletterDelivery, NewsletterSubscriber


def _absolute(url):
    """Media URLs are stored site-relative; e-mail clients need absolute ones."""
    if not url:
        return ''
    if url.startswith(('http://', 'https://')):
        return url
    base = (getattr(settings, 'SOCIAL_AUTH_REDIRECT_BASE', '') or '').rstrip('/')
    return f'{base}{url}' if base else url


def _attachment_section(post):
    """Documents and links as clickable items.

    Videos and other heavy media are deliberately linked, never attached: a
    newsletter that carries a 200 Mo video is a newsletter that never arrives.
    """
    from .models import PublicMedia

    rows = []
    for media in post.gallery.all():
        if media.media_type == PublicMedia.MediaType.DOCUMENT:
            label = media.title or media.original_filename or 'Document'
            rows.append((escape(label), _absolute(media.file.url), 'Télécharger'))
        elif media.media_type == PublicMedia.MediaType.VIDEO:
            label = media.title or 'Vidéo'
            rows.append((escape(label), f'{settings.FRONTEND_URL}/publications/{post.slug}', 'Voir la vidéo'))

    if post.attachment:
        rows.append(('Document joint', _absolute(post.attachment.url), 'Télécharger'))

    for link in post.links.all():
        rows.append((escape(link.label or link.url), link.url, 'Ouvrir'))

    if not rows:
        return '', ''

    items = ''.join(
        f'<li style="margin-bottom:8px"><a href="{escape(url)}" '
        f'style="color:#0759a8">{label}</a> — <span style="color:#64748b">{action}</span></li>'
        for label, url, action in rows
    )
    html = (
        '<div style="margin-top:28px;padding-top:18px;border-top:1px solid #e2e8f0">'
        '<h3 style="font-size:15px;color:#002f6a;margin:0 0 10px">Ressources</h3>'
        f'<ul style="padding-left:18px;margin:0">{items}</ul></div>'
    )
    plain = '\n'.join(f'- {label} : {url}' for label, url, _ in rows)
    return html, f'\n\nRessources :\n{plain}'


def _cover_section(post):
    if not post.cover_image:
        return ''
    return (
        f'<img src="{escape(_absolute(post.cover_image.url))}" alt="" '
        'style="width:100%;max-width:680px;height:auto;border-radius:10px;margin-bottom:18px">'
    )


def _gallery_section(post):
    """Inline the publication's photos.

    Images are the one heavy medium e-mail renders well, so they travel with
    the message; videos and documents stay links (see `_attachment_section`).
    """
    from .models import PublicMedia

    photos = [m for m in post.gallery.all() if m.media_type == PublicMedia.MediaType.PHOTO]
    if not photos:
        return ''
    cells = ''.join(
        f'<img src="{escape(_absolute(photo.file.url))}" alt="{escape(photo.alt_text or "")}" '
        'style="width:100%;max-width:680px;height:auto;border-radius:10px;margin:10px 0">'
        + (
            f'<p style="margin:0 0 14px;font-size:13px;color:#64748b">{escape(photo.caption)}</p>'
            if photo.caption else ''
        )
        for photo in photos[:20]
    )
    return f'<div style="margin-top:20px">{cells}</div>'


def build_message(post, recipient_email, unsubscribe_token=None):
    """Render the e-mail version of any publication, whatever its type.

    A newsletter is not a different kind of content here — it is a publication
    whose category happens to be NEWSLETTER. The subject and sender fields fall
    back to the publication's own title when they were never filled in.
    """
    subject = post.newsletter_subject or post.title
    sender_name = post.newsletter_sender_name or 'Task Force Présidentielle'
    from_email = f'{sender_name} <{settings.DEFAULT_FROM_EMAIL}>' if settings.DEFAULT_FROM_EMAIL else sender_name
    preview = escape(post.newsletter_preview_text or post.excerpt or '')
    web_url = f'{settings.FRONTEND_URL}/publications/{post.slug}'
    unsubscribe_url = (
        f'{settings.FRONTEND_URL}/newsletter/desabonnement/{unsubscribe_token}'
        if unsubscribe_token else None
    )
    resources_html, resources_plain = _attachment_section(post)
    footer = (
        f'<p style="margin-top:32px;font-size:12px;color:#64748b">'
        f'<a href="{web_url}">Lire cette newsletter sur le site</a>'
        + (f' · <a href="{unsubscribe_url}">Se désabonner</a>' if unsubscribe_url else '')
        + '</p>'
    )
    html = (
        '<div style="display:none;max-height:0;overflow:hidden">' + preview + '</div>'
        '<article style="max-width:680px;margin:auto;font-family:Arial,sans-serif;color:#0d1c2e;line-height:1.65">'
        f'<h1 style="color:#002f6a">{escape(post.title)}</h1>'
        f'{_cover_section(post)}{post.body}{_gallery_section(post)}{resources_html}{footer}</article>'
    )
    plain = f'{post.title}\n\n{strip_tags(post.body)}{resources_plain}\n\nLire sur le site : {web_url}'
    if unsubscribe_url:
        plain += f'\nSe désabonner : {unsubscribe_url}'
    return EmailMultiAlternatives(subject, plain, from_email, [recipient_email]), html


def send_test(post, email):
    message, html = build_message(post, email)
    message.attach_alternative(html, 'text/html')
    return message.send(fail_silently=False)


def send_to_subscribers(post):
    sent = failed = 0
    subscribers = NewsletterSubscriber.objects.filter(is_active=True)
    for subscriber in subscribers:
        try:
            message, html = build_message(post, subscriber.email, subscriber.unsubscribe_token)
            message.attach_alternative(html, 'text/html')
            message.send(fail_silently=False)
            NewsletterDelivery.objects.update_or_create(
                post=post, subscriber=subscriber,
                defaults={'status': NewsletterDelivery.Status.SENT, 'error': ''},
            )
            sent += 1
        except Exception as exc:  # SMTP errors vary by backend/provider
            NewsletterDelivery.objects.update_or_create(
                post=post, subscriber=subscriber,
                defaults={'status': NewsletterDelivery.Status.FAILED, 'error': str(exc)[:500]},
            )
            failed += 1
    return sent, failed


#: Historical name, kept so existing imports keep working.
_message = build_message
