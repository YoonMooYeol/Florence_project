# Generated by Django 4.2 on 2025-03-06 17:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatManager',
            fields=[
                ('chat_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='채팅 ID')),
                ('topic', models.CharField(blank=True, max_length=255, null=True, verbose_name='채팅 주제 요약')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정 일시')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성 상태')),
                ('message_count', models.IntegerField(default=0, verbose_name='메시지 수')),
                ('pregnancy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_rooms', to='accounts.pregnancy', verbose_name='임신 정보')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_rooms', to=settings.AUTH_USER_MODEL, verbose_name='사용자')),
            ],
            options={
                'verbose_name': '채팅방',
                'verbose_name_plural': '채팅방 목록',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LLMConversation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('query', models.TextField(verbose_name='사용자 질문')),
                ('response', models.TextField(verbose_name='LLM 응답')),
                ('user_info', models.JSONField(blank=True, default=dict, verbose_name='사용자 정보')),
                ('source_documents', models.JSONField(blank=True, default=list, verbose_name='참조 문서')),
                ('using_rag', models.BooleanField(default=False, verbose_name='RAG 사용 여부')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정 시간')),
                ('chat_room', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='llm.chatmanager', verbose_name='채팅방')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='llm_conversations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'LLM 대화',
                'verbose_name_plural': 'LLM 대화 목록',
                'ordering': ['-created_at'],
            },
        ),
    ]
