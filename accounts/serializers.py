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
        read_only_fields = ('user_id',)  # 수정 불가능한 필드. user_id는 자동으로 생성되므로 수정 불가능
        # username도 수정 불가능하게 할지 고려해야 함***
        
    def validate_email(self, value):
        # 이메일 변경 시 중복 검사
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value

    # username 수정 불가능하게 변경시 삭제해야 함***
    def validate_username(self, value):
        # username 변경 시 중복 검사
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("이미 사용 중인 사용자 이름입니다.")
        return value