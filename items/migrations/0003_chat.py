# Hand-written migration 0003: replace Claim with Conversation + Message.
# Dev data only — no data migration needed.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0002_categories_and_claims'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Remove Claim ──────────────────────────────────────────────────
        migrations.DeleteModel(name='Claim'),

        # ── Add Conversation ──────────────────────────────────────────────
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('item', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conversations',
                    to='items.itemreport',
                )),
                ('participant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conversations',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-updated_at']},
        ),
        migrations.AddConstraint(
            model_name='conversation',
            constraint=models.UniqueConstraint(
                fields=('item', 'participant'),
                name='one_conversation_per_user_per_item',
            ),
        ),

        # ── Add Message ───────────────────────────────────────────────────
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('conversation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='items.conversation',
                )),
                ('sender', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sent_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['conversation', 'created_at'], name='items_messa_convers_3ba555_idx'),
        ),
    ]
