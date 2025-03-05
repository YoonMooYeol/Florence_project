from healthcare.conversation.dialogue import DialogueManager
from openai import OpenAI
import os

# 환경 변수에서 프로젝트 루트 경로 추가
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':' + os.getcwd()

# OpenAI 클라이언트 초기화
client = OpenAI()

# DialogueManager 초기화
dm = DialogueManager(client=client)

# 다양한 감정 상태로 10단계 질문 생성 시뮬레이션
emotions = ['neutral', 'positive', 'negative', 'neutral', 'positive', 
            'negative', 'neutral', 'positive', 'negative', 'neutral']
questions = []

# 질문 생성
for emotion in emotions:
    question = dm.get_next_question(emotion)
    questions.append(question)

# 결과 출력
print('===== LLM 생성 질문 목록 =====')
for i, q in enumerate(questions, 1):
    print(f'{i}. [{emotions[i-1]}] {q}') 