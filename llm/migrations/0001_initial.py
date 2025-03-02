# Generated by Django 4.2 on 2025-03-01 03:59

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMInteraction",
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
                    "query_type",
                    models.CharField(
                        default="general", max_length=50, verbose_name="질문 유형"
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="메타데이터"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="생성 시간"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="llm_interactions",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "LLM 상호작용",
                "verbose_name_plural": "LLM 상호작용 목록",
                "ordering": ["-created_at"],
            },
        ),
    ]
