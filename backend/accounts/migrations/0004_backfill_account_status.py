from django.db import migrations


def backfill_status(apps, schema_editor):
    """Existing rows predate the status field: active accounts are ACTIVE,
    the rest are self-registrations that never confirmed their e-mail."""
    User = apps.get_model('accounts', 'User')
    User.objects.filter(is_active=True).update(status='ACTIVE')
    User.objects.filter(is_active=False).update(status='PENDING_EMAIL')


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_user_invited_by_user_status_and_more')]

    operations = [
        migrations.RunPython(backfill_status, migrations.RunPython.noop),
    ]
