from typing import List, Dict, Any
import os
import requests
import json
from datetime import datetime
from openai import OpenAI
from firecrawl import FirecrawlApp  # 최신 Firecrawl SDK 추가


class MedicalCrawler:
    """의료 정보 검색 및 크롤링 클래스"""

    def __init__(self, client: OpenAI = None):
        """
        의료 정보 검색기 초기화

        Args:
            client: OpenAI 클라이언트. None인 경우 자동으로 생성
        """
        self.client = client if client else OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.api_key = os.getenv("FIRECRAWL_API_KEY")
        if not self.api_key:
            print("경고: FIRECRAWL_API_KEY가 설정되지 않았습니다.")
        self.model = "gpt-4o-mini"
        # Firecrawl 앱 초기화
        self.firecrawl_app = None
        if self.api_key:
            self.firecrawl_app = FirecrawlApp(api_key=self.api_key)

    def search_medical_info(
        self, query: str, timeout: int = 30000, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Firecrawl API를 사용하여 의료 정보를 검색

        Args:
            query: 검색할 의료 관련 쿼리
            timeout: 검색 타임아웃 (밀리초, 기본값 30초)
            limit: 최대 결과 수

        Returns:
            검색 결과 목록
        """
        if not self.api_key or not self.firecrawl_app:
            print("Firecrawl API 키가 설정되지 않았거나 앱 초기화에 실패했습니다.")
            return []

        try:
            # Firecrawl의 검색 기능 사용
            print(f'"{query}" 검색 중...')

            # 검색하여 상위 결과 URL 가져오기
            search_results = self.firecrawl_app.search(
                query,
                params={"num_results": limit, "timeout": timeout},  # 검색 타임아웃 설정
            )

            results = []

            # 검색 결과 처리
            if isinstance(search_results, dict):
                if "data" in search_results:
                    search_items = search_results["data"]
                elif "results" in search_results:
                    search_items = search_results["results"]
                else:
                    print(
                        f"검색 결과에 데이터가 없습니다: {list(search_results.keys())}"
                    )
                    return []
            elif hasattr(search_results, "results"):
                search_items = search_results.results
            else:
                print(f"검색 결과 형식 오류: {type(search_results)}")
                return []

            # 최대 limit 개수만큼 처리
            for i, result in enumerate(search_items):
                if i >= limit:
                    break

                try:
                    # 결과가 dict인 경우와 객체인 경우 모두 처리
                    url = (
                        result.get("url", "")
                        if isinstance(result, dict)
                        else getattr(result, "url", "")
                    )
                    title = (
                        result.get("title", "")
                        if isinstance(result, dict)
                        else getattr(result, "title", "")
                    )

                    if not url:
                        continue

                    print(f"URL 스크랩 중: {url}")

                    # 검색된 URL 스크랩하기
                    scrape_result = self.firecrawl_app.scrape_url(
                        url,
                        params={
                            "timeout": timeout,  # 밀리초 단위 타임아웃
                            "formats": ["markdown"],
                        },
                    )

                    # 스크랩 결과 처리
                    markdown_content = None

                    if isinstance(scrape_result, dict):
                        if "markdown" in scrape_result:
                            markdown_content = scrape_result["markdown"]
                        elif (
                            "data" in scrape_result
                            and isinstance(scrape_result["data"], dict)
                            and "markdown" in scrape_result["data"]
                        ):
                            markdown_content = scrape_result["data"]["markdown"]
                    elif hasattr(scrape_result, "markdown"):
                        markdown_content = scrape_result.markdown

                    if not markdown_content:
                        continue

                    results.append(
                        {
                            "title": title,
                            "url": url,
                            "content": markdown_content[:10000],  # 길이 제한
                        }
                    )
                except Exception as e:
                    continue

            return results
        except Exception as e:
            return []

    def generate_queries_from_conversation(
        self, interactions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        대화 내용 전체를 분석하여 직접 검색 쿼리 생성

        Args:
            interactions: 대화 상호작용 목록 (질문과 응답)

        Returns:
            검색 쿼리 목록 (하나의 고품질 쿼리만 포함)
        """
        if not interactions:
            return ["임신 중 건강 관리와 산모 웰빙을 위한 전문가 조언"]

        # 대화 내용 전체를 문맥 있게 구성
        conversation_text = ""
        for i, interaction in enumerate(interactions):
            question = interaction.get("question", "")
            answer = interaction.get("answer", "")
            emotion = interaction.get("emotion", "neutral")

            conversation_text += f"Q: {question}\n"
            conversation_text += f"A: {answer}\n"
            conversation_text += f"감정: {emotion}\n\n"

        system_prompt = """
        당신은 산모의 대화 내용을 분석하여 의학적으로 필요한 정보를 찾아주는 전문가입니다.
        대화 전체의 맥락과 산모의 감정 상태를 분석하고, 특히 다음을 중점적으로 파악하세요:
        
        1. 산모가 언급하지 않거나 알지 못하는 중요한 건강 관련 정보
        2. 산모가 어려움을 겪고 있지만 명확하게 표현하지 못하는 영역
        3. 산모에게 부족해 보이는 지식이나 준비가 필요한 부분
        4. 산모의 불안이나 걱정을 해소할 수 있는 정보
        5. 산모의 현재 상황에서 놓치기 쉬운 중요한 건강 관리 요소
        
        위 분석을 바탕으로, 산모에게 가장 도움이 될 수 있는 하나의 구체적인 의료 정보 검색 쿼리를 생성해 주세요.
        쿼리는 충분히 구체적이고(예: "임신 중 불안감 해소를 위한 호흡 기법"과 같이), 
        의학적으로 정확하며, 산모가 현재 모르거나 부족한 부분을 보완할 수 있는 내용이어야 합니다.
        
        산모가 이미 잘 알고 있거나 잘하고 있는 영역보다는, 
        아직 모르거나 도움이 필요한 영역에 초점을 맞춘 검색 쿼리를 생성해주세요.
        """

        user_prompt = f"""
        다음은 산모와의 대화 내용입니다. 이 대화를 분석하여 산모에게 가장 부족하거나 필요한 의료 정보를 찾기 위한 
        하나의 고품질 검색 쿼리를 생성해 주세요.
        
        === 대화 내용 ===
        {conversation_text}
        =================
        
        위 대화를 바탕으로, 산모가 현재 모르거나 더 알아야 할 중요한 정보, 또는 어려움을 겪고 있지만 명확히 표현하지 않은 
        부분에 초점을 맞춘 구체적인 검색 쿼리 하나를 생성해주세요.
        
        산모가 이미 잘 알고 있거나 잘하고 있는 부분이 아닌, 부족하거나 더 도움이 필요한 영역에 대한 정보를 검색할 수 있는 쿼리여야 합니다.
        """

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            response_text = completion.choices[0].message.content.strip()

            # 쿼리 추출 - 기호나 번호가 있을 경우 제거
            query = response_text
            for prefix in [
                "-",
                "*",
                "•",
                "1.",
                "2.",
                "3.",
                "Query:",
                "query:",
                "쿼리:",
                "검색어:",
            ]:
                if query.startswith(prefix):
                    query = query.replace(prefix, "", 1).strip()
                    break

            # 따옴표로 감싸져 있는 경우 제거
            if (query.startswith('"') and query.endswith('"')) or (
                query.startswith("'") and query.endswith("'")
            ):
                query = query[1:-1].strip()

            return [query] if query else ["임신 중 놓치기 쉬운 건강 관리 요소와 해결책"]

        except Exception as e:
            print(f"쿼리 생성 오류: {str(e)}")
            return ["임신 중 놓치기 쉬운 건강 관리 요소와 해결책"]

    def process_search_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        검색 결과를 처리하여 유용한 의료 정보 추출

        Args:
            results: 검색 결과 목록

        Returns:
            처리된 의료 정보
        """
        if not results:
            return {
                "tips": ["검색 결과가 없습니다. 다른 질문을 시도해보세요."],
                "sources": [],
            }

        # 모든 결과의 내용을 결합
        combined_content = ""
        sources = []

        for result in results:
            if "content" in result and result["content"]:
                # 제목을 포함하여 내용의 맥락을 명확히 함
                if "title" in result and result["title"]:
                    combined_content += f"### {result['title']}\n\n"
                combined_content += result["content"] + "\n\n---\n\n"

            if "url" in result and result["url"] and result["url"] not in sources:
                if "title" in result and result["title"]:
                    sources.append(f"{result['title']} ({result['url']})")
                else:
                    sources.append(result["url"])

        # 청크 단위로 처리하기 위해 내용 분할
        chunk_size = 4000  # 각 청크의 최대 크기
        max_total_length = 15000  # 전체 처리할 최대 텍스트 길이

        # 내용이 너무 길면 잘라내기
        if len(combined_content) > max_total_length:
            combined_content = combined_content[:max_total_length]

        # 내용이 없으면 기본 메시지 반환
        if not combined_content.strip():
            return {
                "tips": [
                    "검색된 내용에서 유용한 정보를 추출할 수 없습니다. 다른 질문을 시도해보세요."
                ],
                "sources": [],
            }

        # 청크로 분할
        chunks = []
        current_length = 0
        current_chunk = ""

        paragraphs = combined_content.split("\n\n")
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                current_chunk += para + "\n\n"
                current_length += len(para) + 2
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para + "\n\n"
                current_length = len(para) + 2

        if current_chunk:
            chunks.append(current_chunk)

        # 의료 정보 추출을 위한 프롬프트
        system_prompt = """
        당신은 산모를 위한 의학 정보를 분석하고 요약하는 전문가입니다.
        제공된 텍스트에서 산모에게 실질적으로 유용하고 정확한 의학 정보를 추출하여 5-7개의 구체적인 팁으로 정리해주세요.
        
        다음 지침을 따라주세요:
        1. 각 팁은 구체적이고 실행 가능해야 합니다 (예: "건강하게 먹으세요"보다는 "하루 5회 소량의 균형 잡힌 식사를 하세요").
        2. 의학적으로 정확하고 최신 정보를 기반으로 해야 합니다.
        3. 산모의 상황에 맞는 맞춤형 조언이어야 합니다.
        4. 각 팁은 2-3문장으로 충분한 설명을 포함해야 합니다.
        5. 가능한 경우 "왜" 그 조언이 중요한지 간략한 이유를 포함하세요.
        6. 모호하거나 일반적인 조언은 피하고, 구체적인 행동 지침을 제시하세요.
        
        팁 형식:
        - [구체적인 조언]: [간략한 설명과 이유]
        """

        all_tips = []

        try:
            # 각 청크별로 처리
            for i, chunk in enumerate(chunks):
                chunk_prompt = f"""
                다음은 산모 건강과 관련된 검색 결과의 일부({i+1}/{len(chunks)})입니다. 
                이 내용을 철저히 분석하여 산모에게 가장 유용하고 실질적인 의학 정보를 구체적인 팁으로 정리해주세요.
                
                검색 주제: {results[0].get('title', '산모 건강 정보')}
                
                {chunk}
                
                위 내용에서 가장 중요하고 실행 가능한 조언을 추출하여, 산모가 바로 적용할 수 있는 구체적인 팁으로 제시해주세요.
                각 팁은 충분히 상세하고 명확해야 하며, 가능한 경우 그 조언이 중요한 이유도 간략히 설명해주세요.
                """

                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": chunk_prompt},
                    ],
                )

                response_text = completion.choices[0].message.content

                # 팁 추출
                chunk_tips = []
                for line in response_text.split("\n"):
                    line = line.strip()
                    if line and (
                        line.startswith("-")
                        or line.startswith("*")
                        or line.startswith("•")
                        or (line[0].isdigit() and line[1:].startswith("."))
                    ):
                        # 앞의 기호와 공백 제거
                        tip = line.lstrip("-*•0123456789. ").strip()
                        if tip and len(tip) > 10:  # 너무 짧은 팁 제외
                            chunk_tips.append(tip)

                # 팁이 추출되지 않았다면 전체 텍스트를 문장 단위로 분리
                if not chunk_tips:
                    sentences = response_text.split(".")
                    chunk_tips = [
                        s.strip() + "."
                        for s in sentences
                        if len(s.strip()) > 20 and len(s.strip()) < 200
                    ]

                    # 그래도 없으면 전체 텍스트 사용
                    if not chunk_tips:
                        chunk_tips = [response_text.strip()]

                all_tips.extend(chunk_tips)

            # 중복 팁 제거
            unique_tips = []
            for tip in all_tips:
                if not any(
                    self._is_similar_tip(tip, existing) for existing in unique_tips
                ):
                    unique_tips.append(tip)

            return {
                "tips": unique_tips[:7],  # 최대 7개 팁으로 제한
                "sources": sources[:5],  # 최대 5개 소스로 제한
            }

        except Exception as e:
            print(f"의료 정보 추출 중 오류 발생: {str(e)}")
            return {
                "tips": [
                    "의료 정보를 처리하는 중 오류가 발생했습니다. 다시 시도해주세요."
                ],
                "sources": sources,
            }

    def _is_similar_tip(self, tip1: str, tip2: str) -> bool:
        """두 팁이 유사한지 확인"""
        # 간단한 유사도 체크: 단어 50% 이상 일치하면 유사하다고 판단
        words1 = set(tip1.lower().split())
        words2 = set(tip2.lower().split())

        if not words1 or not words2:
            return False

        common_words = words1.intersection(words2)
        similarity = len(common_words) / min(len(words1), len(words2))

        return similarity > 0.5
