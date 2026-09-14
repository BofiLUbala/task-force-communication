from django.db import migrations


def backfill_platform(apps, schema_editor):
    """Existing attempts read their platform through the account FK; copy it
    onto the row so the history survives the account being disconnected."""
    SocialPostAttempt = apps.get_model('content', 'SocialPostAttempt')
    for attempt in SocialPostAttempt.objects.filter(platform='').select_related('account'):
        if attempt.account_id:
            attempt.platform = attempt.account.platform
            attempt.save(update_fields=('platform',))


class Migration(migrations.Migration):
    dependencies = [('content', '0010_alter_publicmedia_options_publicmedia_alt_text_and_more')]

    operations = [migrations.RunPython(backfill_platform, migrations.RunPython.noop)]
