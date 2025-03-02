# Generated by Django 4.2 on 2025-03-02 04:21

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
            name="LLMConversation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("query", models.TextField(verbose_name="사용자 질문")),
                ("response", models.TextField(verbose_name="LLM 응답")),
                (
                    "user_info",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="사용자 정보"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="생성 시간"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="수정 시간"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_conversations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "LLM 대화",
                "verbose_name_plural": "LLM 대화 목록",
                "ordering": ["-created_at"],
            },
        ),
    ]
