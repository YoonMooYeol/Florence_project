from typing import List, Dict, Any
import json
import os
from datetime import datetime


class DataCollector:
    """대화 데이터 수집 및 저장 클래스"""

    def __init__(self, storage_dir: str = "output"):
        """
        데이터 수집기 초기화

        Args:
            storage_dir: 데이터 저장 디렉토리
        """
        self.storage_dir = storage_dir
        self.conversation_data = []
        self.current_session = None

        # 저장 디렉토리가 없으면 생성
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    def start_new_session(self) -> None:
        """새 대화 세션 시작"""
        self.current_session = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "interactions": [],
        }

    def record_interaction(
        self, question: str, answer: str, emotion: str, confidence: float, step: int
    ) -> None:
        """
        대화 상호작용 기록

        Args:
            question: 시스템 질문
            answer: 사용자 응답
            emotion: 감지된 감정
            confidence: 감정 분석 신뢰도
            step: 대화 단계
        """
        if self.current_session is None:
            self.start_new_session()

        interaction = {
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "emotion": emotion,
            "confidence": confidence,
        }

        self.current_session["interactions"].append(interaction)

    def save_session(self) -> str:
        """
        현재 세션을 파일로 저장

        Returns:
            저장된 파일 경로
        """
        if self.current_session is None or not self.current_session["interactions"]:
            return None

        session_id = self.current_session["session_id"]
        filename = f"{self.storage_dir}/session_{session_id}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.current_session, f, ensure_ascii=False, indent=2)

        # 대화 데이터 리스트에 세션 추가
        self.conversation_data.append(self.current_session)

        return filename

    def get_session_data(self) -> Dict[str, Any]:
        """현재 세션 데이터 반환"""
        return self.current_session

    def get_all_interactions(self) -> List[Dict[str, Any]]:
        """현재 세션의 모든 상호작용 반환"""
        if self.current_session is None:
            return []
        return self.current_session["interactions"]

    def reset(self) -> None:
        """현재 세션 초기화"""
        self.current_session = None
