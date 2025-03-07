from rest_framework import serializers
from .models import User, Pregnancy
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

class PregnancySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pregnancy
        fields = ['pregnancy_id', 'husband_id', 'baby_name', 'due_date', 
                 'current_week', 'created_at', 'updated_at', 'high_risk']
        read_only_fields = ['pregnancy_id', 'created_at', 'updated_at']

    def validate_current_week(self, value):
        if value is not None and (value < 1 or value > 42):
            raise serializers.ValidationError("임신 주차는 1주차에서 42주차 사이여야 합니다.")
        return value

    def validate_due_date(self, value):
        if value is not None:
            from datetime import date
            if value < date.today():
                raise serializers.ValidationError("출산 예정일은 오늘 이후여야 합니다.")
        return value
    
class UserUpdateSerializer(serializers.ModelSerializer):
    """사용자 정보 수정용 시리얼라이저"""
    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'phone_number', 'gender', 'address', 'is_pregnant')  # 실제 모델에 있는 필드들만 포함
        read_only_fields = ('user_id', 'email')  # 수정 불가능한 필드. user_id는 자동으로 생성되므로 수정 불가능

class ChangePasswordSerializer(serializers.Serializer):
    """비밀번호 변경 시리얼라이저"""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, data):
        # 새 비밀번호 일치 여부 확인
        if data.get('new_password') != data.get('new_password_confirm'):
            raise serializers.ValidationError({"new_password": "새 비밀번호가 일치하지 않습니다."})
        
        # 현재 비밀번호와 새 비밀번호가 같은지 확인
        if data.get('current_password') == data.get('new_password'):
            raise serializers.ValidationError({"new_password": "현재 비밀번호와 새 비밀번호가 같습니다."})
        
        return data

# 직렬화 클래스 정의
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = User.objects.get(email=value)
        if not user:
            raise serializers.ValidationError("해당 이메일의 사용자가 없습니다.")
        return value

class PasswordResetCheckSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        user = User.objects.get(reset_code=value)
        if not user or not user.check_reset_code(value):
            raise serializers.ValidationError("만료되었거나 잘못된 코드입니다.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    reset_code = serializers.CharField()
    new_password = serializers.CharField()

    def validate_code(self, value):
        # 코드로 사용자 존재 여부 확인
        user = User.objects.get(reset_code=value)
        if not user or not user.check_reset_code(value):
            raise serializers.ValidationError("만료되었거나 잘못된 코드입니다.")
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("비밀번호는 최소 8자 이상이어야 합니다.")
        return value