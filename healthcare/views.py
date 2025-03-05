import os
from openai import OpenAI
from dotenv import load_dotenv
from .emotion_analysis.analyzer import EmotionAnalyzer
from .conversation.dialogue import DialogueManager
from .data_collection.collector import DataCollector
from .feedback_generation.generator import FeedbackGenerator
from .medical_search.crawler import MedicalCrawler
from .utils import format_feedback_for_display, ensure_dir_exists, analyze_emotion
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import ConversationSession, Message, Feedback
from django.shortcuts import get_object_or_404
from .serializers import (
    ConversationListSerializer, 
    ConversationDetailSerializer, 
    HealthcareResponseSerializer,
    MessageSerializer
)

# 환경 변수 로드
load_dotenv()


class ConversationListView(APIView):
    """사용자의 대화 기록 목록을 반환하는 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        conversations = ConversationSession.objects.filter(user=user).order_by('-created_at')
        
        result = []
        for conversation in conversations:
            # 메시지 수 계산
            message_count = conversation.messages.count()
            
            # 피드백 정보 확인
            has_feedback = hasattr(conversation, 'feedback')
            feedback_summary = None
            if has_feedback:
                feedback_summary = conversation.feedback.summary
            
            # 마지막 메시지 시간 (있는 경우)
            last_message_time = None
            last_message = conversation.messages.order_by('-created_at').first()
            if last_message:
                last_message_time = last_message.created_at
            
            # 대화 정보 구성
            conversation_data = {
                'id': str(conversation.id),
                'created_at': conversation.created_at,
                'updated_at': last_message_time or conversation.created_at,
                'is_completed': conversation.is_completed,
                'message_count': message_count,
                'has_feedback': has_feedback,
                'feedback_summary': feedback_summary
            }
            
            result.append(conversation_data)
        
        return Response(result)
    
    def post(self, request):
        """새 대화 세션 생성"""
        user = request.user
        conversation = ConversationSession.objects.create(user=user)
        
        return Response({
            'id': str(conversation.id),
            'created_at': conversation.created_at,
            'is_completed': conversation.is_completed
        }, status=status.HTTP_201_CREATED)


class ConversationDetailView(APIView):
    """특정 대화 세션의 상세 정보를 반환하는 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, conversation_id):
        user = request.user
        conversation = get_object_or_404(ConversationSession, id=conversation_id, user=user)
        
        # 메시지 목록 가져오기
        messages = conversation.messages.all().order_by('created_at')
        
        # 메시지 형식 변환
        formatted_messages = []
        
        # 대화 컨텍스트 및 감정 추적을 위한 변수
        emotion_counts = {}
        last_emotion = 'neutral'
        conversation_topics = set()
        
        for msg in messages:
            # 질문 메시지 (봇)
            if msg.question:
                formatted_messages.append({
                    'id': str(msg.id),
                    'sender': 'bot',
                    'content': msg.question,
                    'time': msg.created_at.strftime('%H:%M'),
                    'emotion': msg.emotion,
                    'step': msg.step
                })
            
            # 답변 메시지 (사용자)
            if msg.answer:
                formatted_messages.append({
                    'id': str(msg.id) + '_answer',
                    'sender': 'user',
                    'content': msg.answer,
                    'time': msg.created_at.strftime('%H:%M'),
                    'emotion': msg.emotion,
                    'step': msg.step
                })
                
                # 감정 상태 추적
                if msg.emotion:
                    if msg.emotion not in emotion_counts:
                        emotion_counts[msg.emotion] = 0
                    emotion_counts[msg.emotion] += 1
                    last_emotion = msg.emotion
                    
                # 간단한 토픽 추출 (키워드 기반)
                keywords = ['기분', '식단', '운동', '수면', '통증', '스트레스', '병원']
                for keyword in keywords:
                    if keyword in msg.answer:
                        conversation_topics.add(keyword)
        
        # 대화 시작부터 경과 시간 계산 (분 단위)
        elapsed_time = None
        if conversation.created_at:
            from django.utils import timezone
            now = timezone.now()
            time_diff = now - conversation.created_at
            elapsed_time = int(time_diff.total_seconds() / 60)  # 분 단위로 변환
        
        # 대화 정보 구성
        response_data = {
            'id': str(conversation.id),
            'created_at': conversation.created_at,
            'is_completed': conversation.is_completed,
            'messages': formatted_messages,
            'has_feedback': hasattr(conversation, 'feedback'),
            'context': {
                'elapsed_time_minutes': elapsed_time,
                'dominant_emotion': max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else 'neutral',
                'current_emotion': last_emotion,
                'topics_discussed': list(conversation_topics),
                'total_exchanges': len(messages)
            }
        }
        
        # 피드백 정보 추가 (있는 경우)
        if hasattr(conversation, 'feedback'):
            response_data['feedback'] = {
                'summary': conversation.feedback.summary,
                'emotional_analysis': conversation.feedback.emotional_analysis,
                'health_tips': conversation.feedback.health_tips,
                'medical_info': conversation.feedback.medical_info
            }
        
        return Response(response_data)


class HealthcareView(APIView):
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능
    
    def post(self, request):
        """메인 함수"""
        # 요청에서 데이터 가져오기
        data = request.data
        user_answers = data.get('answers', [])  # 사용자가 미리 준비한 답변 리스트
        
        log_messages = []  # 로그 메시지를 저장할 리스트
        
        log_messages.append("\n===== 산모 컨디션 체크 시스템 =====\n")
        log_messages.append(
            "안녕하세요! 오늘 하루 어떻게 지내셨는지 대화를 통해 알아보고 맞춤형 피드백을 제공해 드리겠습니다."
        )
        log_messages.append("산모 상태에 맞는 의학 정보도 함께 제공됩니다.")
        log_messages.append("총 10개의 질문을 통해 컨디션을 체크하고 종합적인 피드백을 생성합니다.\n")

        # API 키 확인
        openai_key = os.getenv("OPENAI_API_KEY")
        firecrawl_key = os.getenv("FIRECRAWL_API_KEY")

        if not openai_key:
            log_messages.append("경고: OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
            return Response({"error": "OpenAI API 키가 설정되지 않았습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not firecrawl_key:
            log_messages.append(
                "경고: FIRECRAWL_API_KEY가 설정되지 않았습니다. 의료 정보 검색 기능이 제한됩니다."
            )

        # 현재 로그인한 사용자 가져오기
        user = request.user
        
        # 새 대화 세션 생성
        conversation_session = ConversationSession.objects.create(
            user=user,
            is_completed=False
        )

        # OpenAI 클라이언트 초기화
        client = OpenAI()

        # 모듈 초기화
        emotion_analyzer = EmotionAnalyzer(client=client)
        dialogue_manager = DialogueManager(client=client)
        data_collector = DataCollector()
        feedback_generator = FeedbackGenerator(client=client)
        medical_crawler = MedicalCrawler(client=client)

        # 새 세션 시작
        data_collector.start_new_session()

        # 대화 진행
        step = 0
        current_emotion = "neutral"  # 초기 감정 상태
        questions_and_answers = []  # 질문과 답변을 저장할 리스트

        while not dialogue_manager.is_conversation_complete() and step < len(user_answers):
            # 다음 질문 가져오기
            question = dialogue_manager.get_next_question(emotion=current_emotion)

            if not question:
                break

            # 질문 표시 및 사용자 응답 받기
            step += 1  # 단계를 먼저 증가시켜 1부터 시작하도록 함
            log_messages.append(f"\n[{step}/10] {question}")
            
            # 사용자 답변 가져오기
            answer = user_answers[step-1] if step-1 < len(user_answers) else "응답 없음"
            log_messages.append(f"> {answer}")
            
            # 질문과 답변 저장
            questions_and_answers.append({
                "question": question,
                "answer": answer
            })

            # 이전 대화 내용 가져오기
            previous_interactions = data_collector.get_all_interactions()

            # 맥락을 고려한 감정 분석
            emotion_result = emotion_analyzer.analyze_emotion_with_context(
                question=question, answer=answer, conversation_history=previous_interactions
            )
            current_emotion = emotion_result["emotion"]

            # 분석된 감정 출력 (디버깅용)
            log_messages.append(
                f"[시스템] 감지된 감정: {current_emotion} (신뢰도: {emotion_result['confidence']:.2f})"
            )

            # 상호작용 기록
            data_collector.record_interaction(
                question=question,
                answer=answer,
                emotion=current_emotion,
                confidence=emotion_result["confidence"],
                step=step - 1,  # 0부터 시작하는 원래 step 값 유지
            )
            
            # 데이터베이스에 메시지 저장
            Message.objects.create(
                session=conversation_session,
                question=question,
                answer=answer,
                emotion=current_emotion,
                confidence=emotion_result["confidence"],
                step=step-1
            )

        log_messages.append("\n모든 질문이 완료되었습니다. 피드백을 생성 중입니다...\n")

        # 세션 저장
        session_file = data_collector.save_session()
        
        # 대화 세션 완료로 표시
        conversation_session.is_completed = True
        conversation_session.save()

        # 의료 정보 검색
        log_messages.append("의료 정보를 검색 중입니다...")

        # 모든 상호작용 가져오기
        interactions = data_collector.get_all_interactions()

        # 대화 내용 기반 검색 쿼리 직접 생성 - 하나의 고품질 쿼리로 개선
        search_query = medical_crawler.generate_queries_from_conversation(interactions)[0]

        # 의료 정보 검색 및 처리
        medical_info = {"tips": [], "sources": []}

        search_results = medical_crawler.search_medical_info(
            search_query, limit=1
        )  # 하나의 검색 결과만 가져오기

        if search_results:
            processed_results = medical_crawler.process_search_results(search_results)

            # 팁 및 소스 추가
            medical_info["tips"] = processed_results["tips"]
            medical_info["sources"] = processed_results["sources"]

        # 최대 7개 팁으로 제한
        if len(medical_info["tips"]) > 7:
            medical_info["tips"] = medical_info["tips"][:7]

        # 의료 정보가 없는 경우 기본 메시지 추가
        if not medical_info["tips"]:
            medical_info["tips"] = [
                "관련 의료 정보를 찾을 수 없습니다. 궁금한 점이 있으시면 의료 전문가와 상담하세요."
            ]

        # 피드백 생성
        feedback = feedback_generator.generate_feedback(interactions, medical_info)

        # 피드백 저장
        session_id = data_collector.get_session_data()["session_id"]
        feedback_file = feedback_generator.save_feedback(feedback, session_id)

        # 피드백 표시
        formatted_feedback = format_feedback_for_display(feedback)
        log_messages.append(formatted_feedback)

        log_messages.append(f"\n피드백이 '{feedback_file}' 파일에 저장되었습니다.")
        log_messages.append("\n===== 산모 컨디션 체크 완료 =====\n")
        
        # 디버깅을 위해 로그 메시지를 콘솔에 출력
        for msg in log_messages:
            print(msg)
            
        # 데이터베이스에 피드백 저장
        db_feedback = Feedback.objects.create(
            session=conversation_session,
            summary=feedback.get('summary', ''),
            emotional_analysis=feedback.get('mood_analysis', ''),
            health_tips='\n'.join([f"• {rec}" for rec in feedback.get('recommendations', [])])
        )
        
        # 의료 정보 저장
        db_feedback.set_tips(medical_info['tips'])
        db_feedback.set_sources(medical_info.get('sources', []))
        db_feedback.save()

        # JSON 응답 반환
        response_data = {
            "status": "success",
            "conversation_id": str(conversation_session.id),
            "feedback": formatted_feedback,
            "medical_info": medical_info,
            "log_messages": log_messages,
            "questions_and_answers": questions_and_answers
        }
        serializer = HealthcareResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NextQuestionView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, conversation_id):
        try:
            conversation = get_object_or_404(ConversationSession, id=conversation_id, user=request.user)
            
            # 대화 단계 계산
            messages = Message.objects.filter(session=conversation).order_by('created_at')
            answered_messages = messages.exclude(answer="")
            current_step = answered_messages.count()  # 답변이 있는 메시지 수로 계산
            
            # OpenAI 클라이언트 초기화
            client = OpenAI()
            
            # 대화 관리자 초기화 - OpenAI 클라이언트 전달
            dialogue_manager = DialogueManager(client=client)
            dialogue_manager.current_step = current_step
            
            # 현재 감정 상태 분석 (이전 메시지 기반)
            last_user_message = Message.objects.filter(
                session=conversation
            ).exclude(
                answer=""
            ).order_by('-created_at').first()
            
            emotion = "neutral"  # 기본값
            if last_user_message:
                # 감정 분석 로직
                emotion = analyze_emotion(last_user_message.answer)
            
            # 다음 질문 가져오기
            next_question = dialogue_manager.get_next_question(emotion)
            
            # 이미 해당 단계의 질문이 있는지 확인
            existing_question = Message.objects.filter(
                session=conversation,
                step=current_step + 1,
                answer=""
            ).first()
            
            if existing_question:
                # 이미 질문이 있으면 그 질문을 반환
                next_question = existing_question.question
            else:
                # 질문을 메시지로 저장
                Message.objects.create(
                    session=conversation,
                    question=next_question,
                    answer="",
                    step=current_step + 1
                )
            
            return Response({
                "question": next_question,
                "step": dialogue_manager.current_step,
                "total_steps": dialogue_manager.max_steps
            })
            
        except ConversationSession.DoesNotExist:
            return Response(
                {"error": "대화를 찾을 수 없습니다."}, 
                status=status.HTTP_404_NOT_FOUND
            )


class AnswerView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, conversation_id):
        try:
            conversation = get_object_or_404(ConversationSession, id=conversation_id, user=request.user)
            user_answer = request.data.get('answer', '')
            
            if not user_answer:
                return Response(
                    {"error": "답변이 필요합니다."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 마지막 질문 메시지 찾기
            last_question = Message.objects.filter(
                session=conversation,
                answer=""
            ).order_by('-created_at').first()
            
            if last_question:
                # 감정 분석
                emotion = analyze_emotion(user_answer)
                
                # 기존 메시지에 답변과 감정 추가
                last_question.answer = user_answer
                last_question.emotion = emotion
                last_question.save()
            else:
                # 새 메시지 생성 (비정상 케이스)
                current_step = conversation.messages.count() + 1
                Message.objects.create(
                    session=conversation,
                    question="",
                    answer=user_answer,
                    step=current_step
                )
            
            # 대화 단계 계산
            current_step = conversation.messages.count()
            
            # OpenAI 클라이언트 초기화
            client = OpenAI()
            
            # 대화 관리자 초기화 - OpenAI 클라이언트 전달
            dialogue_manager = DialogueManager(client=client)
            dialogue_manager.current_step = current_step
            
            # 대화 완료 여부 확인
            is_completed = dialogue_manager.is_conversation_complete()
            
            if is_completed:
                conversation.is_completed = True
                conversation.save()
                
                # 피드백 생성 작업 시작 (비동기로 처리)
                from .feedback_generation.generator import generate_feedback
                generate_feedback(conversation_id)
            
            return Response({
                "is_completed": is_completed,
                "step": dialogue_manager.current_step,
                "total_steps": dialogue_manager.max_steps
            })
            
        except ConversationSession.DoesNotExist:
            return Response(
                {"error": "대화를 찾을 수 없습니다."}, 
                status=status.HTTP_404_NOT_FOUND
            )



