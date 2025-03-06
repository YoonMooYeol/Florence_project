# Generated by Django 4.2 on 2025-03-06 08:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_phone_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(error_messages={'blank': '이메일을 입력해주세요.', 'invalid': '올바른 이메일 형식이 아닙니다.', 'unique': '이미 사용 중인 이메일입니다.'}, max_length=254, unique=True, verbose_name='이메일'),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone_number',
            field=models.CharField(error_messages={'blank': '전화번호를 입력해주세요.', 'max_length': '전화번호는 15자를 초과할 수 없습니다.', 'unique': '이미 등록된 전화번호입니다.'}, max_length=15, unique=True, verbose_name='전화번호'),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(error_messages={'blank': '아이디를 입력해주세요.', 'max_length': '아이디는 100자를 초과할 수 없습니다.', 'unique': '이미 사용 중인 아이디입니다.'}, max_length=100, unique=True, verbose_name='아이디'),
        ),
    ]
