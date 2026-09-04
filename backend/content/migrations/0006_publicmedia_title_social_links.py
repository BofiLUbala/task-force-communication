from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('content', '0005_alter_socialaccount_platform')]

    operations = [
        migrations.AddField(
            model_name='publicmedia',
            name='title',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='publicmedia',
            name='social_links',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
