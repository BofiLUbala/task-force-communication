import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('content', '0007_alter_publicpost_category')]

    operations = [
        migrations.AddField(model_name='publicpost', name='newsletter_preview_text', field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name='publicpost', name='newsletter_recipient_count', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='publicpost', name='newsletter_sender_name', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='publicpost', name='newsletter_sent_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='publicpost', name='newsletter_subject', field=models.CharField(blank=True, max_length=255)),
        migrations.CreateModel(
            name='NewsletterSubscriber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('name', models.CharField(blank=True, max_length=150)),
                ('unsubscribe_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('subscribed_at', models.DateTimeField(auto_now_add=True)),
                ('unsubscribed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ('-subscribed_at',)},
        ),
        migrations.CreateModel(
            name='NewsletterDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('SENT', 'Envoyé'), ('FAILED', 'Échec')], max_length=10)),
                ('error', models.CharField(blank=True, max_length=500)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='newsletter_deliveries', to='content.publicpost')),
                ('subscriber', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='content.newslettersubscriber')),
            ],
            options={'ordering': ('-sent_at',)},
        ),
        migrations.AddConstraint(
            model_name='newsletterdelivery',
            constraint=models.UniqueConstraint(fields=('post', 'subscriber'), name='unique_newsletter_delivery'),
        ),
    ]
