# Generated by Django 4.2 on 2025-03-06 17:02

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('event_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(error_messages={'blank': '제목을 입력해주세요.', 'max_length': '제목은 100자를 초과할 수 없습니다.'}, max_length=100, verbose_name='제목')),
                ('description', models.TextField(blank=True, null=True, verbose_name='설명')),
                ('event_day', models.DateField(verbose_name='일정 날짜')),
                ('event_time', models.TimeField(blank=True, null=True, verbose_name='일정 시간')),
                ('event_type', models.CharField(choices=[('appointment', '병원 예약'), ('medication', '약물 복용'), ('symptom', '증상 기록'), ('exercise', '운동'), ('other', '기타')], default='other', max_length=20, verbose_name='일정 유형')),
                ('is_recurring', models.BooleanField(default=False, verbose_name='반복 여부')),
                ('recurrence_pattern', models.CharField(blank=True, max_length=50, null=True, verbose_name='반복 패턴')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pregnancy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='accounts.pregnancy', verbose_name='임신 정보')),
            ],
            options={
                'verbose_name': '일정',
                'verbose_name_plural': '일정들',
                'ordering': ['event_day', 'event_time'],
            },
        ),
    ]
