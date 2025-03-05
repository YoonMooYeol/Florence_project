#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import django

# 시스템 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Django 설정 초기화
django.setup()

from openai import OpenAI
from healthcare.feedback_generation.generator import FeedbackGenerator
from healthcare.medical_search.crawler import MedicalCrawler

def test_feedback_generation():
    """피드백 생성 테스트"""
    print("=== 피드백 생성 테스트 시작 ===")
    
    # 테스트 데이터 생성
    interactions = [
        {
            "question": "오늘 하루 어떻게 지내셨나요?",
            "answer": "오늘은 조금 피곤했어요. 허리도 아프고 잠도 잘 안 오네요.",
            "emotion": "tiredness"
        },
        {
            "question": "수면에 어려움이 있으신 것 같네요. 어떤 이유 때문인 것 같으세요?",
            "answer": "아무래도 배가 점점 불러서 편한 자세를 찾기가 어려워요. 또 화장실도 자주 가게 되고요.",
            "emotion": "worry"
        },
        {
            "question": "식습관은 어떻게 유지하고 계신가요?",
            "answer": "과일과 채소를 많이 먹으려고 노력하고 있어요. 아이에게 좋은 영양분을 주고 싶어서요.",
            "emotion": "neutral"
        }
    ]

    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # 피드백 생성기 초기화
    generator = FeedbackGenerator(client=client)
    
    # 피드백 생성
    feedback = generator.generate_feedback(interactions)
    
    # 결과 출력
    print("\n=== 생성된 피드백 ===")
    print(f"요약: {feedback['summary']}")
    print(f"감정 분석: {feedback['mood_analysis']}")
    print("\n권장사항:")
    for i, rec in enumerate(feedback['recommendations'], 1):
        print(f"{i}. {rec}")
    
    print("\n의료 정보:")
    for i, tip in enumerate(feedback['medical_tips'], 1):
        print(f"{i}. {tip}")
    
    # 원본 텍스트 확인 (마크다운 형식이 제거되었는지 확인)
    print("\n=== 원본 텍스트 포맷 확인 ===")
    for i, rec in enumerate(feedback['recommendations'], 1):
        has_markdown = any(marker in rec for marker in ['**', '__', '*', '_', '[', ']', '(', ')', '#'])
        print(f"권장사항 {i}: {'마크다운 형식 포함' if has_markdown else '일반 텍스트'}")
    
    for i, tip in enumerate(feedback['medical_tips'], 1):
        has_markdown = any(marker in tip for marker in ['**', '__', '*', '_', '[', ']', '(', ')', '#'])
        print(f"의료 팁 {i}: {'마크다운 형식 포함' if has_markdown else '일반 텍스트'}")
    
    print("=== 피드백 생성 테스트 완료 ===")
    
    return feedback

def test_crawler():
    """의료 정보 크롤링 테스트"""
    print("\n=== 의료 정보 크롤링 테스트 시작 ===")
    
    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # 크롤러 초기화
    crawler = MedicalCrawler(client=client)
    
    # 검색 테스트
    query = "임신 중 허리 통증 완화 방법"
    print(f"검색 쿼리: {query}")
    
    # 검색 결과 가져오기
    results = crawler.search_medical_info(query, limit=3)
    print(f"검색 결과: {len(results)}개")
    
    # 결과 처리
    if results:
        processed_info = crawler.process_search_results(results)
        
        print("\n=== 처리된 의료 정보 ===")
        print("팁:")
        for i, tip in enumerate(processed_info['tips'], 1):
            print(f"{i}. {tip}")
            
        print("\n소스:")
        for i, source in enumerate(processed_info['sources'], 1):
            print(f"{i}. {source}")
        
        # 마크다운 형식 제거 확인
        print("\n=== 마크다운 형식 제거 확인 ===")
        for i, tip in enumerate(processed_info['tips'], 1):
            has_markdown = any(marker in tip for marker in ['**', '__', '*', '_', '[', ']', '(', ')', '#'])
            print(f"의료 팁 {i}: {'마크다운 형식 포함' if has_markdown else '일반 텍스트'}")
    
    print("=== 의료 정보 크롤링 테스트 완료 ===")

if __name__ == "__main__":
    # 테스트 실행
    feedback = test_feedback_generation()
    test_crawler() 