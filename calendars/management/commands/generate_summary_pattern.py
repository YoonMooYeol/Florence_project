import random
from datetime import datetime, timedelta
import uuid
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from calendars.models import DailyConversationSummary
from accounts.models import Pregnancy

User = get_user_model()

class Command(BaseCommand):
    help = '패턴화된 날짜(3일 생성, 2일 건너뛰기)로 더미 LLM 대화 요약 데이터 생성'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            help='요약을 생성할 사용자의 username (미지정 시 모든 사용자)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='생성할 기준 일수 (기본값: 30일)'
        )
        parser.add_argument(
            '--pattern',
            default='3,2',
            help='생성 패턴 "생성일,건너뛰기일" 형식 (기본값: "3,2" - 3일 생성, 2일 건너뛰기)'
        )
        parser.add_argument(
            '--start-date',
            help='시작 날짜 (YYYY-MM-DD 형식, 기본값: N일 전)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='기존 요약 데이터 삭제 후 생성'
        )

    def handle(self, *args, **options):
        # 옵션 파싱
        username = options.get('user')
        days = options.get('days')
        pattern_str = options.get('pattern', '3,2')
        start_date_str = options.get('start_date')
        clear = options.get('clear')

        # 패턴 파싱
        try:
            create_days, skip_days = map(int, pattern_str.split(','))
            if create_days <= 0 or skip_days < 0:
                raise ValueError("생성일은 1 이상, 건너뛰기일은 0 이상이어야 합니다")
        except ValueError as e:
            raise CommandError(f"패턴 형식이 잘못되었습니다: {str(e)}")

        # 사용자 목록 가져오기
        if username:
            try:
                users = [User.objects.get(username=username)]
                self.stdout.write(f"사용자 '{username}'에 대한 패턴화된 더미 요약 생성")
            except User.DoesNotExist:
                raise CommandError(f"사용자 '{username}'을(를) 찾을 수 없습니다.")
        else:
            users = User.objects.filter(is_active=True)
            self.stdout.write(f"{users.count()}명의 사용자에 대한 패턴화된 더미 요약 생성")

        # 날짜 범위 설정
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError("날짜 형식이 잘못되었습니다. YYYY-MM-DD 형식으로 입력하세요.")
        else:
            start_date = (timezone.now().date() - timedelta(days=days-1))

        # 패턴에 따른 날짜 목록 생성
        pattern_dates = []
        current_date = start_date
        
        while current_date <= timezone.now().date():
            # create_days 동안 날짜 추가
            for i in range(create_days):
                if current_date <= timezone.now().date():
                    pattern_dates.append(current_date)
                    current_date += timedelta(days=1)
            
            # skip_days 동안 날짜 건너뛰기
            current_date += timedelta(days=skip_days)
        
        self.stdout.write(f"패턴 {create_days}일 생성, {skip_days}일 건너뛰기로 {len(pattern_dates)}일의 요약 생성 예정")

        # 기존 데이터 삭제 옵션
        if clear:
            if username:
                deleted, _ = DailyConversationSummary.objects.filter(user__username=username).delete()
                self.stdout.write(f"사용자 '{username}'의 요약 {deleted}개 삭제 완료")
            else:
                deleted, _ = DailyConversationSummary.objects.all().delete()
                self.stdout.write(f"모든 사용자의 요약 {deleted}개 삭제 완료")

        # 임신 단계별 더미 요약 내용
        pregnancy_stage_summaries = {
            'first_trimester': [
                "오늘은 입덧 증상이 심했습니다. 생강차가 도움이 된다는 정보를 얻었습니다. 또한 초기 임신 중 필요한 비타민과 영양소에 관해 배웠고, 특히 엽산 섭취가 중요하다는 것을 확인했습니다.",
                "오늘은 임신 초기에 나타날 수 있는 피로감에 대해 알아보았습니다. 작은 간식을 자주 먹고 충분한 휴식을 취하는 것이 좋다고 합니다. 또한 초음파 검사 일정을 계획하는 방법에 대해서도 정보를 얻었습니다.",
                "임신 초기 감정 변화와 호르몬 변화에 대해 배웠습니다. 가벼운 운동이 기분 개선에 도움이 된다고 합니다. 임신 사실을 주변에 언제 알리는 것이 좋을지에 대한 조언도 얻었습니다.",
                "오늘은 태아 발달 초기 단계에 관한 정보를 알아보았습니다. 현재 심장이 형성되기 시작하고 있으며, 이 시기에 특히 건강한 식습관이 중요하다는 것을 배웠습니다. 초기 임신 중 피해야 할 음식 목록도 확인했습니다.",
                "임신 초기 증상 중 하나인 두통에 대처하는 방법을 알아보았습니다. 카페인을 줄이고 충분한 수분을 섭취하는 것이 도움이 된다고 합니다. 임신 초기 약물 복용에 관한 주의사항도 확인했습니다."
            ],
            'second_trimester': [
                "태아의 움직임을 처음 느꼈습니다! 이 시기에는 '퀵닝'이라 불리는 첫 태동을 경험하게 된다고 합니다. 임신 중기에 적합한 운동 방법에 대해서도 알아보았고, 수영과 요가가 추천된다는 것을 배웠습니다.",
                "임신 중기에 접어들며 에너지 수준이 향상되었습니다. 이 시기에는 입덧이 줄어들고 활동적인 생활이 가능하다고 합니다. 임신 중 여행 계획에 관한 조언과 안전 수칙도 함께 얻었습니다.",
                "오늘은 태아 성별 검사에 관한 정보를 알아보았습니다. 초음파 검사로 확인할 수 있으며, 임신 18-20주 사이에 진행되는 정밀 초음파 검사에서 더 정확한 결과를 얻을 수 있다고 합니다.",
                "임신 중기에 나타날 수 있는 허리 통증 관리법에 대해 배웠습니다. 바른 자세 유지와 특수 쿠션 사용이 도움이 된다고 합니다. 태아 발달에 따른 영양 요구 사항 변화에 대해서도 정보를 얻었습니다.",
                "태아와의 유대감 형성을 위한 방법을 알아보았습니다. 태아에게 말을 걸거나 음악을 들려주는 것이 좋다고 합니다. 또한 임신 중기에 권장되는 수면 자세와 베개 사용법에 대해서도 배웠습니다."
            ],
            'third_trimester': [
                "출산 준비 계획을 세웠습니다. 분만 가방에 필요한 물품 목록을 확인하고, 출산 시 진통 대처 방법에 대해 배웠습니다. 또한 출산 후 첫 주에 필요한 준비물과 도움을 요청할 수 있는 지원 네트워크를 정리했습니다.",
                "브랙스턴 힉스 수축을 경험했습니다. 이는 실제 진통과 달리 불규칙적이며 출산이 가까워질수록 빈번해진다고 합니다. 출산 징후를 구별하는 방법과 언제 병원에 가야 하는지에 대한 정보도 얻었습니다.",
                "출산 방법에 대한 옵션을 탐색했습니다. 자연 분만과 제왕절개의 장단점을 비교하고, 각 상황에서 필요한 준비 사항을 알아보았습니다. 출산 계획서 작성에 관한 조언도 받았습니다.",
                "임신 후기 잦은 소변과 수면 문제에 대처하는 방법을 배웠습니다. 측면으로 눕고 다리 사이에 베개를 끼우는 것이 편안한 수면에 도움이 된다고 합니다. 아기를 위한 방 준비에 관한 체크리스트도 작성했습니다.",
                "모유 수유에 관한 정보를 수집했습니다. 올바른 수유 자세와 빈도, 초기에 나타날 수 있는 어려움에 대처하는 방법을 알아보았습니다. 또한 신생아 돌봄에 필요한 기본 지식과 준비물을 정리했습니다."
            ]
        }

        # 더미 요약 생성
        created_count = 0

        for user in users:
            # 사용자의 임신 정보 가져오기 (없으면 None)
            pregnancy = Pregnancy.objects.filter(user=user).first()
            
            # 현재 임신 주차에 따른 단계 결정
            if pregnancy and pregnancy.due_date:
                weeks_pregnant = (timezone.now().date() - pregnancy.due_date).days // 7 + 40
                
                if weeks_pregnant < 0:
                    weeks_pregnant = random.randint(1, 40)  # 유효하지 않은 값이면 랜덤 생성
                
                if weeks_pregnant <= 13:
                    stage = 'first_trimester'
                elif weeks_pregnant <= 26:
                    stage = 'second_trimester'
                else:
                    stage = 'third_trimester'
            else:
                # 임신 정보가 없으면 랜덤 단계 선택
                stage = random.choice(['first_trimester', 'second_trimester', 'third_trimester'])
            
            # 패턴 날짜별 요약 생성
            for date in pattern_dates:
                # 이미 해당 날짜에 요약이 있는지 확인
                if DailyConversationSummary.objects.filter(user=user, summary_date=date).exists():
                    self.stdout.write(self.style.WARNING(
                        f"사용자 '{user.username}'의 {date} 요약이 이미 존재합니다. 건너뜁니다."
                    ))
                    continue
                
                # 랜덤 요약 텍스트 선택
                summary_text = random.choice(pregnancy_stage_summaries[stage])
                
                # 요약 생성
                DailyConversationSummary.objects.create(
                    user=user,
                    pregnancy=pregnancy,
                    summary_date=date,
                    summary_text=summary_text
                )
                created_count += 1
                
                if created_count % 10 == 0:
                    self.stdout.write(f"{created_count}개의 요약 생성됨...")
        
        self.stdout.write(self.style.SUCCESS(f"총 {created_count}개의 패턴화된 더미 요약 데이터가 생성되었습니다!")) 