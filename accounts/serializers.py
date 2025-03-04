from rest_framework import serializers
from .models import User
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['user_id', 'username', 'name', 'email', 'phone_number', 'password', 'password_confirm', 'gender', 'is_pregnant', 'address']
        read_only_fields = ['user_id']
    
    def validate(self, data):
        # 비밀번호 확인 검증
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return data
    
    def create(self, validated_data):
        # password_confirm 필드 제거
        validated_data.pop('password_confirm', None)
        
        # User 생성
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        
        # 추가 필드 설정
        if 'phone_number' in validated_data:
            user.phone_number = validated_data['phone_number']
        if 'gender' in validated_data:
            user.gender = validated_data['gender']
        if 'is_pregnant' in validated_data:
            user.is_pregnant = validated_data['is_pregnant']
        if 'address' in validated_data:
            user.address = validated_data['address']
        
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)