from typing import Dict, List, Any
from ..method import SimpleRAG

class PregnancyService:
    """
    임신 관련 정보 검색 서비스
    
    임신 주차에 맞는 정보를 검색하는 기능을 제공합니다.
    """
    
    @staticmethod
    def search_pregnancy_info(query: str, pregnancy_week: int, k: int = 3) -> Dict[str, Any]:
        """
        임신 주차에 맞는 정보를 검색합니다.
        
        Args:
            query: 검색 쿼리
            pregnancy_week: 임신 주차
            k: 반환할 문서 수
            
        Returns:
            검색 결과
        """
        # SimpleRAG의 임신 주차 기반 검색 메서드 사용
        documents = SimpleRAG.search_by_pregnancy_week(query, pregnancy_week, k)
        
        # 결과 포맷팅
        results = {
            "query": query,
            "pregnancy_week": pregnancy_week,
            "documents": []
        }
        
        for doc in documents:
            # 문서 정보 추출
            doc_info = {
                "content": doc.page_content,
                "metadata": doc.metadata
            }
            
            # 임신 주차 정보 추가
            doc_week = doc.metadata.get('pregnancy_week')
            if doc_week is not None:
                doc_info["pregnancy_week"] = doc_week
                
            results["documents"].append(doc_info)
            
        return results 