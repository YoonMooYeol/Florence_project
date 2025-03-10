# Generated by Django 5.1.7 on 2025-03-10 11:21

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('calendars', '0001_initial'),
        ('llm', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyConversationSummary',
            fields=[
                ('summary_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('summary_text', models.TextField(verbose_name='일별 대화 요약 내용')),
                ('summary_date', models.DateField(verbose_name='요약 날짜')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('conversations', models.ManyToManyField(related_name='daily_summaries', to='llm.llmconversation', verbose_name='관련 대화')),
                ('pregnancy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='daily_conversation_summaries', to='accounts.pregnancy', verbose_name='임신 정보')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_conversation_summaries', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '일별 대화 요약',
                'verbose_name_plural': '일별 대화 요약 목록',
                'ordering': ['-summary_date'],
                'unique_together': {('user', 'summary_date')},
            },
        ),
        migrations.DeleteModel(
            name='EventConversationSummary',
        ),
    ]
