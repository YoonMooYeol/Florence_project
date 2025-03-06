# Generated by Django 4.2 on 2025-03-06 08:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("llm", "0003_llmconversation_chat_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="llmconversation",
            name="chat_id",
        ),
        migrations.CreateModel(
            name="ChatManager",
            fields=[
                (
                    "chat_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="채팅 ID",
                    ),
                ),
                (
                    "topic",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="채팅 주제 요약",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="생성 일시"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="수정 일시"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="활성 상태"),
                ),
                (
                    "message_count",
                    models.IntegerField(default=0, verbose_name="메시지 수"),
                ),
                (
                    "pregnancy",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chat_rooms",
                        to="accounts.pregnancy",
                        verbose_name="임신 정보",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_rooms",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="사용자",
                    ),
                ),
            ],
            options={
                "verbose_name": "채팅방",
                "verbose_name_plural": "채팅방 목록",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="llmconversation",
            name="chat_room",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="llm.chatmanager",
                verbose_name="채팅방",
            ),
        ),
    ]
