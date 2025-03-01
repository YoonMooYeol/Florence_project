from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'name', 'email', 'phone_number', 'password', 'gender', 'is_pregnant', 'address']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # User 모델의 set_password 메서드를 사용하여 비밀번호 해시화
        user = User(
            name=validated_data['name'],
            email=validated_data['email'],
            phone_number=validated_data.get('phone_number'),
            gender=validated_data.get('gender'),
            is_pregnant=validated_data.get('is_pregnant', False),
            address=validated_data.get('address')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)