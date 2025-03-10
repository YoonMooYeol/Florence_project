# Generated by Django 5.1.7 on 2025-03-10 07:58

import django.contrib.auth.models
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('user_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('username', models.CharField(error_messages={'blank': '아이디를 입력해주세요.', 'max_length': '아이디는 100자를 초과할 수 없습니다.', 'unique': '이미 사용 중인 아이디입니다.'}, max_length=100, unique=True, verbose_name='아이디')),
                ('email', models.EmailField(error_messages={'blank': '이메일을 입력해주세요.', 'invalid': '올바른 이메일 형식이 아닙니다.', 'unique': '이미 사용 중인 이메일입니다.'}, max_length=254, unique=True, verbose_name='이메일')),
                ('name', models.CharField(max_length=100, verbose_name='이름')),
                ('phone_number', models.CharField(blank=True, error_messages={'invalid': '올바른 전화번호 형식이 아닙니다.', 'max_length': '전화번호는 15자를 초과할 수 없습니다.', 'unique': '이미 등록된 전화번호입니다.'}, max_length=15, unique=True, verbose_name='전화번호')),
                ('gender', models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], max_length=10, null=True, verbose_name='성별')),
                ('is_pregnant', models.BooleanField(default=False, verbose_name='임신 여부')),
                ('address', models.CharField(blank=True, max_length=255, null=True, verbose_name='주소')),
                ('reset_code', models.CharField(blank=True, max_length=6, null=True)),
                ('reset_code_end', models.DateTimeField(blank=True, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='이 사용자가 속한 그룹들.', related_name='user_groups', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='이 사용자의 권한들.', related_name='user_permissions', to='auth.permission')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Pregnancy',
            fields=[
                ('pregnancy_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('husband_id', models.UUIDField(blank=True, null=True)),
                ('baby_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='태명')),
                ('due_date', models.DateField(blank=True, null=True, verbose_name='출산 예정일')),
                ('current_week', models.IntegerField(blank=True, null=True, verbose_name='현재 임신 주차')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('high_risk', models.BooleanField(default=False, verbose_name='고위험 임신 여부')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pregnancies', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '임신 정보',
                'verbose_name_plural': '임신 정보',
                'ordering': ['-created_at'],
            },
        ),
    ]
