from rest_framework import serializers
from .models import User
from django.contrib.auth.hashers import make_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'name', 'email', 'phone_number', 'password_hash', 'gender', 'is_pregnant', 'address']
        extra_kwargs = {'password_hash': {'write_only': True}}

    def create(self, validated_data):
        validated_data['password_hash'] = make_password(validated_data['password_hash'])  # 비밀번호 해시화
        return super().create(validated_data)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)