from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('content', '0006_publicmedia_title_social_links')]

    operations = [
        migrations.AlterField(
            model_name='publicpost',
            name='category',
            field=models.CharField(
                choices=[
                    ('COMMUNIQUE', 'Communiqué'),
                    ('ACTUALITE', 'Actualité'),
                    ('ACTIVITE', 'Activité'),
                    ('NEWSLETTER', 'Newsletter'),
                ],
                max_length=20,
            ),
        ),
    ]
