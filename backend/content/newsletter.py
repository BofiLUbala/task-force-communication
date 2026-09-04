from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from .models import NewsletterDelivery, NewsletterSubscriber


def _message(post, recipient_email, unsubscribe_token=None):
    subject = post.newsletter_subject or post.title
    sender_name = post.newsletter_sender_name or 'Task Force Présidentielle'
    from_email = f'{sender_name} <{settings.DEFAULT_FROM_EMAIL}>' if settings.DEFAULT_FROM_EMAIL else sender_name
    preview = escape(post.newsletter_preview_text or post.excerpt or '')
    web_url = f'{settings.FRONTEND_URL}/publications/{post.slug}'
    unsubscribe_url = (
        f'{settings.FRONTEND_URL}/newsletter/desabonnement/{unsubscribe_token}'
        if unsubscribe_token else None
    )
    footer = (
        f'<p style="margin-top:32px;font-size:12px;color:#64748b">'
        f'<a href="{web_url}">Lire cette newsletter sur le site</a>'
        + (f' · <a href="{unsubscribe_url}">Se désabonner</a>' if unsubscribe_url else '')
        + '</p>'
    )
    html = (
        '<div style="display:none;max-height:0;overflow:hidden">' + preview + '</div>'
        '<article style="max-width:680px;margin:auto;font-family:Arial,sans-serif;color:#0d1c2e;line-height:1.65">'
        f'<h1 style="color:#002f6a">{escape(post.title)}</h1>{post.body}{footer}</article>'
    )
    plain = f'{post.title}\n\n{strip_tags(post.body)}\n\nLire sur le site : {web_url}'
    if unsubscribe_url:
        plain += f'\nSe désabonner : {unsubscribe_url}'
    return EmailMultiAlternatives(subject, plain, from_email, [recipient_email]), html


def send_test(post, email):
    message, html = _message(post, email)
    message.attach_alternative(html, 'text/html')
    return message.send(fail_silently=False)


def send_to_subscribers(post):
    sent = failed = 0
    subscribers = NewsletterSubscriber.objects.filter(is_active=True)
    for subscriber in subscribers:
        try:
            message, html = _message(post, subscriber.email, subscriber.unsubscribe_token)
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
