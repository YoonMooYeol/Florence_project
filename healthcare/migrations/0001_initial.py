# Generated by Django 4.2 on 2025-03-05 13:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_completed', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('question', models.TextField()),
                ('answer', models.TextField()),
                ('emotion', models.CharField(choices=[('happiness', '행복'), ('sadness', '슬픔'), ('anger', '분노'), ('fear', '두려움'), ('surprise', '놀람'), ('disgust', '혐오'), ('neutral', '중립'), ('worry', '걱정'), ('anxiety', '불안'), ('excitement', '설렘'), ('tiredness', '피곤')], default='neutral', max_length=20)),
                ('confidence', models.FloatField(default=0.0)),
                ('step', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='healthcare.conversationsession')),
            ],
            options={
                'ordering': ['step'],
            },
        ),
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('summary', models.TextField()),
                ('emotional_analysis', models.TextField()),
                ('health_tips', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('medical_info', models.JSONField(default=dict)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='healthcare.conversationsession')),
            ],
        ),
    ]
