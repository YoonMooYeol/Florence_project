import rdflib
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS
import os
from django.conf import settings
from tqdm import tqdm
import json
from typing import List, Dict, Any, Tuple, Optional
import glob
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
import uuid
import pickle
from rag.models import RAG_DB
import asyncio
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import re
import traceback
from langchain.schema import Document

# pandas 모듈 import 시도
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("pandas 모듈을 찾을 수 없습니다. 기본 CSV 로더를 사용합니다.")

load_dotenv()

class RDFProcessor:
    """
    RDF 데이터를 처리하고 쿼리하는 기능을 제공하는 클래스
    """
    
    def __init__(self, rdf_file_path="data/rdf/*.rdf", format=None):
        """
        RDF 프로세서 초기화
        
        Args:
            rdf_file_path (str, optional): RDF 파일 경로. 기본값은 "data/rdf/*.rdf".
            format (str, optional): RDF 파일 형식 ('nt', 'xml', 'turtle' 등). 기본값은 None(자동 감지).
        """
        self.graph = rdflib.Graph()
        self.format = format
        
        # 파일 경로가 없는 경우 빈 그래프로 초기화
        if not rdf_file_path:
            print("RDF 파일 경로가 지정되지 않았습니다. 빈 그래프로 초기화합니다.")
            return
        
        self._load_files(rdf_file_path, format)
    
    def _load_files(self, file_path: str, format: Optional[str] = None) -> None:
        """
        파일 경로에 따라 RDF 파일을 로드
        
        Args:
            file_path (str): RDF 파일 경로 (glob 패턴 가능)
            format (Optional[str]): RDF 파일 형식
        """
        # glob 패턴인 경우 처리
        if '*' in file_path:
            matching_files = glob.glob(file_path)
            if not matching_files:
                print(f"매칭되는 RDF 파일이 없습니다: {file_path}")
                return
            
            # 모든 매칭 파일 로드
            for file_path in matching_files:
                if os.path.exists(file_path):
                    file_format = self._detect_format(file_path, format)
                    self.load_rdf(file_path, file_format)
        elif os.path.exists(file_path):
            file_format = self._detect_format(file_path, format)
            self.load_rdf(file_path, file_format)
        else:
            print(f"RDF 파일이 존재하지 않습니다: {file_path}")
    
    def _detect_format(self, file_path: str, format: Optional[str] = None) -> str:
        """
        파일 확장자에 따라 RDF 형식을 자동으로 감지
        
        Args:
            file_path (str): RDF 파일 경로
            format (Optional[str]): 사용자가 지정한 형식 (있는 경우)
            
        Returns:
            str: 감지된 RDF 형식
        """
        if format:
            return format
            
        if file_path.endswith('.rdf') or file_path.endswith('.xml'):
            return 'xml'
        elif file_path.endswith('.n-triples') or file_path.endswith('.nt'):
            return 'nt'
        elif file_path.endswith('.ttl'):
            return 'turtle'
        elif file_path.endswith('.jsonld'):
            return 'json-ld'
        else:
            # 기본값
            return 'xml'  # 기본값을 xml로 변경 (이전에는 nt)
    
    def load_rdf(self, file_path: str, format: Optional[str] = None) -> None:
        """
        RDF 파일을 로드하여 그래프에 추가
        
        Args:
            file_path (str): RDF 파일 경로
            format (Optional[str]): RDF 파일 형식. 기본값은 None(자동 감지).
        """
        try:
            # 형식이 지정되지 않은 경우 자동 감지
            if format is None:
                format = self._detect_format(file_path)
                
            print(f"RDF 파일 로드 중: {file_path} (형식: {format})")
            self.graph.parse(file_path, format=format)
            print(f"RDF 그래프 로드 완료: {len(self.graph)} 트리플")
        except Exception as e:
            print(f"RDF 파일 로드 중 오류 발생: {e}")
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        SPARQL 쿼리를 실행하고 결과를 반환
        
        Args:
            query (str): SPARQL 쿼리 문자열
            
        Returns:
            List[Dict[str, Any]]: 쿼리 결과를 딕셔너리 리스트로 반환
        """
        try:
            results = self.graph.query(query)
            result_list = []
            
            # 결과를 딕셔너리 리스트로 변환
            for row in results:
                row_dict = {}
                for var in results.vars:
                    value = row[var]
                    if isinstance(value, URIRef):
                        row_dict[var] = str(value)
                    elif isinstance(value, Literal):
                        row_dict[var] = value.value
                    else:
                        row_dict[var] = str(value)
                result_list.append(row_dict)
            
            return result_list
        except Exception as e:
            print(f"쿼리 실행 중 오류 발생: {e}")
            return []
    
    def get_resource_info(self, resource_uri: str) -> Dict[str, List[Any]]:
        """
        특정 리소스에 대한 모든 속성과 값을 가져옴
        
        Args:
            resource_uri (str): 리소스 URI
            
        Returns:
            Dict[str, List[Any]]: 속성을 키로, 값 리스트를 값으로 하는 딕셔너리
        """
        resource = URIRef(resource_uri)
        result = {}
        
        for s, p, o in self.graph.triples((resource, None, None)):
            pred = str(p)
            if pred not in result:
                result[pred] = []
            
            if isinstance(o, Literal):
                result[pred].append(o.value)
            else:
                result[pred].append(str(o))
        
        return result
    
    def get_resources_by_type(self, type_uri: str) -> List[str]:
        """
        특정 타입의 모든 리소스를 가져옴
        
        Args:
            type_uri (str): 타입 URI
            
        Returns:
            List[str]: 리소스 URI 리스트
        """
        type_ref = URIRef(type_uri)
        resources = []
        
        for s in self.graph.subjects(RDF.type, type_ref):
            resources.append(str(s))
        
        return resources
    
    def get_label(self, uri: str, lang: str = "ko") -> Optional[str]:
        """
        URI에 대한 라벨을 가져옴
        
        Args:
            uri (str): 리소스 URI
            lang (str, optional): 언어 코드. 기본값은 'ko'.
            
        Returns:
            Optional[str]: 라벨 문자열 또는 None
        """
        if not uri or not isinstance(uri, str):
            return None
            
        resource = URIRef(uri)
        for label in self.graph.objects(resource, RDFS.label):
            if isinstance(label, Literal) and (not lang or label.language == lang):
                return str(label)
        return None
    
    def convert_to_rag_format(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        RDF 쿼리 결과를 RAG 시스템에서 사용할 수 있는 형식으로 변환
        
        Args:
            results (List[Dict[str, Any]]): RDF 쿼리 결과
            
        Returns:
            List[Dict[str, Any]]: RAG 형식으로 변환된 결과
        """
        rag_data = []
        
        for item in results:
            # 각 리소스를 텍스트로 변환
            content_parts = []
            
            # 리소스 URI와 라벨 추가
            if 'uri' in item:
                content_parts.append(f"리소스: {item['uri']}")
            if 'label' in item and item['label']:
                content_parts.append(f"라벨: {item['label']}")
            
            # 속성 정보 추가
            if 'properties' in item:
                content_parts.append("속성:")
                for prop, values in item['properties'].items():
                    if values:
                        values_str = ', '.join([str(v) for v in values])
                        content_parts.append(f"  - {prop}: {values_str}")
            
            # 텍스트로 결합
            content = '\n'.join(content_parts)
            
            # RAG 형식으로 변환
            rag_item = {
                "content": content,
                "metadata": {
                    "source": "rdf",
                    "type": "knowledge_graph",
                    "uri": item.get('uri', ''),
                    "label": item.get('label', '')
                }
            }
            rag_data.append(rag_item)
        
        return rag_data
    
    def search_by_keyword(self, keyword: str, lang: str = "ko") -> List[Dict[str, Any]]:
        """
        키워드로 리소스를 검색
        
        Args:
            keyword (str): 검색 키워드
            lang (str, optional): 언어 코드. 기본값은 'ko'.
            
        Returns:
            List[Dict[str, Any]]: 검색 결과
        """
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?s ?label
        WHERE {{
            ?s rdfs:label ?label .
            FILTER(CONTAINS(STR(?label), "{keyword}"))
        }}
        LIMIT 100
        """
        
        results = self.execute_query(query)
        
        # 각 리소스에 대한 추가 정보 조회
        enriched_results = []
        for result in results:
            if 's' in result:
                enriched_result = self._enrich_resource_info(result['s'], result.get('label', ''))
                enriched_results.append(enriched_result)
        
        return enriched_results
    
    def _enrich_resource_info(self, resource_uri: str, label: str = "") -> Dict[str, Any]:
        """
        리소스 정보를 풍부하게 만들어 반환
        
        Args:
            resource_uri (str): 리소스 URI
            label (str, optional): 리소스 라벨
            
        Returns:
            Dict[str, Any]: 풍부한 리소스 정보
        """
        resource_info = self.get_resource_info(resource_uri)
        
        # 기본 정보 추가
        enriched_result = {
            'uri': resource_uri,
            'label': label or self.get_label(resource_uri),
            'properties': {}
        }
        
        # 속성 정보 추가
        for pred, values in resource_info.items():
            pred_label = self.get_label(pred) or pred
            enriched_result['properties'][pred_label] = []
            
            for value in values:
                if isinstance(value, str) and value.startswith('http'):
                    value_label = self.get_label(value)
                    if value_label:
                        enriched_result['properties'][pred_label].append(value_label)
                    else:
                        enriched_result['properties'][pred_label].append(value)
                else:
                    enriched_result['properties'][pred_label].append(value)
        
        return enriched_result

class RAGProcessor:
    """
    RAG 처리 클래스
    """
    TEMP_DIR = "data/temp_embeddings"
    DB_DIR = os.path.join(settings.BASE_DIR, "embeddings", "chroma_db")
    RDF_FILE_PATH = "data/rdf/wellness.rdf"
    
    # 중요 속성 목록 - 모든 임베딩 과정에서 우선적으로 고려할 속성들
    IMPORTANT_PROPERTIES = [
        # 🚨 금지 및 부작용 관련
        "금지약품", "금지하다", "부작용", "forbidMedicine",  
        
        # 🏥 건강 및 질병 관련
        "건강", "질병", "증상", "치료", "합병증", "면역력", "감염", "바이러스", 
        "독감", "코로나", "풍진", "톡소플라즈마", "B형간염", "C형간염", 
        "빈혈", "갑상선질환", "고혈압", "저혈압", "비만", "체중감소", "위장장애", 
        "요로감염", "변비", "relatedDisease",
        
        # 🤰 임신 및 출산 관련
        "임신", "출산", "산모", "태아", "영아", "아기", 
        "출산준비", "출산후관리", "산후우울증", "산후조리", "유산", "조산", 
        "자연분만", "제왕절개", "입덧", "태아발달", "태아건강", "양수", "태반", "태동", 
        "산통", "bodyTransformation", "fetusDevelopment",
        
        # 🍽 영양 및 식습관
        "음식", "영양", "식이요법", "영양소결핍", "과체중", "저체중", "단백질섭취", 
        "철분섭취", "칼슘섭취", "엽산섭취", "비타민D섭취", "임산부음식", 
        "권장음식", "피해야할음식", "카페인섭취", "알코올", "가공식품", "해산물", 
        "intakeNutrient", "recommendedFood", "avoidedFood",
        
        # 🏃‍♀ 생활 습관 및 환경 요인
        "운동", "운동부족", "과로", "자세", "자세교정", "스트레스", "스트레스해소", 
        "명상", "요가", "필라테스", "수면", "수면부족", "휴식", 
        "미세먼지", "화학물질노출", "전자파", 
        
        # 🧠 정신 건강 및 심리
        "우울증", "불안증", "정서안정", "산후스트레스", "사회적지지", "마음챙김", 
        "육아스트레스", "stressRelief"
    ]

    @staticmethod
    def parse_n_triples(file_path):
        """n-triples 파일을 파싱하여 주제별로 그룹화합니다."""
        print(f"n-triples 파일 파싱 중: {file_path}")
        
        # 주제별 트리플 그룹화
        subjects = {}
        
        # 임신 관련 키워드
        pregnancy_keywords = [
            "pregnancy", "maternal", "임신", "산모", "태아", "출산",
            "PregnancyPeriod", "FirstTrimester", "SecondTrimester", "ThirdTrimester"
        ]
        
        # n-triples 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"총 {len(lines)}개의 트리플 읽기 완료")
        
        # 트리플 파싱 정규식
        triple_pattern = re.compile(r'<([^>]+)>\s+<([^>]+)>\s+(.+)\s+\.')
        
        # 진행 상황 표시
        for line in tqdm(lines, desc="트리플 파싱"):
            match = triple_pattern.match(line.strip())
            if match:
                subject, predicate, obj = match.groups()
                
                # 주제가 subjects 딕셔너리에 없으면 추가
                if subject not in subjects:
                    subjects[subject] = []
                
                # 트리플 추가
                subjects[subject].append((predicate, obj))
        
        print(f"총 {len(subjects)}개의 주제 발견")
        
        # 임신 관련 주제 필터링
        pregnancy_subjects = {}
        for subject, triples in subjects.items():
            # 주제 URI에 임신 관련 키워드가 포함되어 있는지 확인
            if any(keyword in subject.lower() for keyword in pregnancy_keywords):
                pregnancy_subjects[subject] = triples
                continue
            
            # 트리플에 임신 관련 키워드가 포함되어 있는지 확인
            for predicate, obj in triples:
                if any(keyword in predicate.lower() for keyword in pregnancy_keywords) or \
                   any(keyword in obj.lower() for keyword in pregnancy_keywords):
                    pregnancy_subjects[subject] = triples
                    break
        
        print(f"임신 관련 주제 {len(pregnancy_subjects)}개 발견")
        
        return pregnancy_subjects

    @staticmethod
    def create_embeddings_from_subjects(subjects):
        """주제별 트리플에서 텍스트를 생성하고 임베딩합니다."""
        texts = []
        metadatas = []
        ids = []
        
        # 중요 속성 목록 가져오기
        important_props = RAGProcessor.IMPORTANT_PROPERTIES
        
        # 주제별로 텍스트 생성
        for idx, (subject, triples) in enumerate(subjects.items()):
            # 텍스트 생성
            content_parts = [f"주제: {subject}"]
            
            # 트리플 정보 추가
            predicates = {}
            important_attrs = {}
            
            for predicate, obj in triples:
                if predicate not in predicates:
                    predicates[predicate] = []
                
                # 객체가 URI인 경우 < > 제거
                if obj.startswith('<') and obj.endswith('>'):
                    obj = obj[1:-1]
                # 객체가 리터럴인 경우 따옴표와 언어 태그 제거
                elif obj.startswith('"') and obj.endswith('"'):
                    obj = obj[1:-1]
                elif obj.startswith('"') and '"^^' in obj:
                    obj = obj[1:obj.find('"^^')]
                elif obj.startswith('"') and '"@' in obj:
                    obj = obj[1:obj.find('"@')]
                
                # 중요 속성 확인
                for prop in important_props:
                    if prop in predicate.lower() or prop in obj.lower():
                        # 속성 이름 추출 (URI의 마지막 부분)
                        attr_name = predicate.split('/')[-1].split('#')[-1]
                        important_attrs[attr_name] = obj
                
                predicates[predicate].append(obj)
            
            # 중요 속성 먼저 추가
            for prop in important_props:
                for pred, values in predicates.items():
                    if prop in pred:
                        values_str = ', '.join(values)
                        content_parts.append(f"{pred}: {values_str}")
            
            # 나머지 속성 추가
            for pred, values in predicates.items():
                if not any(prop in pred for prop in important_props):
                    values_str = ', '.join(values)
                    content_parts.append(f"{pred}: {values_str}")
            
            # 텍스트로 결합
            content = '\n'.join(content_parts)
            
            # 내용이 너무 짧으면 건너뛰기
            if len(content) < 50:
                continue
            
            # 메타데이터 생성
            metadata = {
                "source": "rdf",
                "type": "maternal_health",
                "uri": subject
            }
            
            # 중요 속성 메타데이터 추가
            for k, v in important_attrs.items():
                metadata[f"important_{k}"] = v
            
            # 고유 ID 생성
            doc_id = f"maternal_{idx}_{hash(subject)}"
            
            texts.append(content)
            metadatas.append(metadata)
            ids.append(doc_id)
        
        return texts, metadatas, ids

    @staticmethod
    def embed_maternal_health_data(rdf_file_path: str = None, format: str = None, db_dir: str = None) -> Dict[str, Any]:
        """
        산모 건강 관련 RDF 데이터를 임베딩하여 벡터 데이터베이스에 저장
        개선된 버전 - 더 많은 관련 리소스 추출
        """
        try:
            if rdf_file_path is None:
                rdf_file_path = RAGProcessor.RDF_FILE_PATH
            
            if db_dir is None:
                db_dir = os.path.join(RAGProcessor.DB_DIR, "maternal_health_db")
                
            # RDF 데이터 처리
            print(f"🔍 산모 건강 RDF 파일 처리 중: {rdf_file_path}")
            
            # RDF 프로세서 초기화
            processor = RDFProcessor(rdf_file_path, format)
            
            # 개선된 쿼리 사용
            improved_pregnancy_query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX wsc: <http://www.wellness.ai/schema/class/>

            SELECT DISTINCT ?resource ?label WHERE {
                {
                    # 키워드 검색 (원래 효과적인 방식)
                    ?resource ?p ?o .
                    FILTER(isURI(?resource))
                    OPTIONAL { ?resource rdfs:label ?label }
                    FILTER(
                        CONTAINS(LCASE(STR(?resource)), "임신") || 
                        CONTAINS(LCASE(STR(?resource)), "출산") || 
                        CONTAINS(LCASE(STR(?resource)), "산모") || 
                        CONTAINS(LCASE(STR(?resource)), "태아") || 
                        CONTAINS(LCASE(STR(?resource)), "영아") || 
                        CONTAINS(LCASE(STR(?resource)), "아기") || 
                        CONTAINS(LCASE(STR(?resource)), "pregnancy") || 
                        CONTAINS(LCASE(STR(?resource)), "childbirth") || 
                        CONTAINS(LCASE(STR(?resource)), "maternal") || 
                        CONTAINS(LCASE(STR(?resource)), "fetus") || 
                        CONTAINS(LCASE(STR(?resource)), "infant") || 
                        CONTAINS(LCASE(STR(?resource)), "baby") ||
                        CONTAINS(LCASE(STR(?resource)), "pregnancyperiod") || 
                        CONTAINS(LCASE(STR(?resource)), "firsttrimester") || 
                        CONTAINS(LCASE(STR(?resource)), "secondtrimester") || 
                        CONTAINS(LCASE(STR(?resource)), "thirdtrimester")
                    )
                } UNION {
                    # 객체값 키워드 검색 (원래 효과적인 방식)
                    ?resource ?p ?o .
                    FILTER(isURI(?resource))
                    OPTIONAL { ?resource rdfs:label ?label }
                    FILTER(
                        CONTAINS(LCASE(STR(?o)), "임신") || 
                        CONTAINS(LCASE(STR(?o)), "출산") || 
                        CONTAINS(LCASE(STR(?o)), "산모") || 
                        CONTAINS(LCASE(STR(?o)), "태아") || 
                        CONTAINS(LCASE(STR(?o)), "영아") || 
                        CONTAINS(LCASE(STR(?o)), "아기") || 
                        CONTAINS(LCASE(STR(?o)), "pregnancy") || 
                        CONTAINS(LCASE(STR(?o)), "childbirth") || 
                        CONTAINS(LCASE(STR(?o)), "maternal") || 
                        CONTAINS(LCASE(STR(?o)), "fetus") || 
                        CONTAINS(LCASE(STR(?o)), "infant") || 
                        CONTAINS(LCASE(STR(?o)), "baby") ||
                        CONTAINS(LCASE(STR(?o)), "pregnancyperiod") || 
                        CONTAINS(LCASE(STR(?o)), "firsttrimester") || 
                        CONTAINS(LCASE(STR(?o)), "secondtrimester") || 
                        CONTAINS(LCASE(STR(?o)), "thirdtrimester")
                    )
                }
            }
            LIMIT 2000
            """
            
            # 임신 관련 리소스 조회
            pregnancy_resources = processor.execute_query(improved_pregnancy_query)
            print(f"🔢 임신 관련 리소스 발견: {len(pregnancy_resources)}개")
            
            # 임베딩할 텍스트 준비
            texts = []
            metadatas = []
            ids = []
            
            # 중요 속성 목록 사용
            important_props = RAGProcessor.IMPORTANT_PROPERTIES
            
            # rdflib 결과 키 확인
            if pregnancy_resources and len(pregnancy_resources) > 0:
                first_result = pregnancy_resources[0]
                result_keys = list(first_result.keys())
                print(f"SPARQL 결과 키: {result_keys}")
                
                # 리소스 URI를 포함하는 키 찾기
                resource_key = None
                label_key = None
                
                for key in result_keys:
                    key_str = str(key).lower()
                    if 'resource' in key_str:
                        resource_key = key
                    elif 'label' in key_str:
                        label_key = key
                
                if not resource_key:
                    print("⚠️ 리소스 URI를 포함하는 키를 찾을 수 없습니다.")
                    return {
                        "file_path": rdf_file_path,
                        "format": format,
                        "resource_count": len(pregnancy_resources),
                        "embedded_resources": 0,
                        "db_dir": db_dir,
                        "warning": "리소스 URI를 포함하는 키를 찾을 수 없습니다."
                    }
            
            # 각 리소스에 대한 정보 가져오기
            processed_uris = set()  # 중복 처리 방지
            
            for idx, resource in enumerate(pregnancy_resources):
                # rdflib Variable 객체로부터 값 추출
                resource_uri = str(resource[resource_key]) if resource_key and resource_key in resource else None
                
                if not resource_uri or resource_uri in processed_uris:
                    continue
                    
                processed_uris.add(resource_uri)
                    
                # 리소스 정보 가져오기
                resource_info = processor.get_resource_info(resource_uri)
                
                # 리소스 레이블 가져오기
                label = str(resource[label_key]) if label_key and label_key in resource and resource[label_key] is not None else None
                if label == "None":  # "None" 문자열 처리
                    label = None
                
                if not label:
                    label = processor.get_label(resource_uri)
                
                # 텍스트 생성
                text_parts = [f"주제: {label or resource_uri}"]
                
                # 중요 속성 추출
                important_attrs = {}
                
                # 중요 속성 먼저 추가
                for prop_key in resource_info:
                    if any(important_prop in prop_key.lower() for important_prop in important_props):
                        values = resource_info[prop_key]
                        values_str = ", ".join(str(v) for v in values)
                        text_parts.append(f"{prop_key}: {values_str}")
                        
                        # 중요 속성 메타데이터에 추가
                        attr_name = prop_key.split('/')[-1].split('#')[-1]
                        important_attrs[attr_name] = values_str
                
                # 나머지 속성 추가
                for prop_key in resource_info:
                    if not any(important_prop in prop_key.lower() for important_prop in important_props):
                        values = resource_info[prop_key]
                        values_str = ", ".join(str(v) for v in values)
                        text_parts.append(f"{prop_key}: {values_str}")
                
                # 최종 텍스트 생성
                text = "\n".join(text_parts)
                
                # 내용이 너무 짧으면 건너뛰기
                if len(text) < 50:
                    continue
                
                # 메타데이터 생성
                metadata = {
                    "source": rdf_file_path,
                    "uri": resource_uri,
                    "label": label or "",
                }
                
                # 중요 속성 메타데이터 추가
                for k, v in important_attrs.items():
                    metadata[f"important_{k}"] = v
                
                # 데이터 추가
                texts.append(text)
                metadatas.append(metadata)
                ids.append(f"maternal_{idx}")
            
            # 임베딩 생성
            print(f"🧠 데이터 임베딩 생성 시작: {len(texts)}개 텍스트")
            
            # 텍스트가 없는 경우 처리
            if len(texts) == 0:
                print("⚠️ 임베딩할 텍스트가 없습니다. 처리를 중단합니다.")
                return {
                    "file_path": rdf_file_path,
                    "format": format,
                    "resource_count": len(pregnancy_resources),
                    "embedded_resources": 0,
                    "db_dir": db_dir,
                    "warning": "임베딩할 텍스트가 없습니다."
                }
            
            # 벡터 임베딩 생성
            embeddings = RAGProcessor.create_embeddings(texts)
            
            # 벡터 데이터베이스 초기화
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
            vectorstore = Chroma(
                persist_directory=db_dir,
                embedding_function=embedding_function,
                collection_name="maternal_health_knowledge"
            )
            
            # 벡터 데이터베이스에 저장
            print(f"💾 벡터 데이터베이스 업데이트 시작")
            
            vectorstore._collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ 벡터 데이터베이스 업데이트 완료: {len(texts)}개 문서")
            
            return {
                "file_path": rdf_file_path,
                "format": format,
                "resource_count": len(pregnancy_resources),
                "embedded_resources": len(texts),
                "db_dir": db_dir
            }
            
        except Exception as e:
            print(f"❌ RDF 데이터 처리 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return {
                "error": str(e),
                "file_path": rdf_file_path,
                "format": format
            }

    @staticmethod
    def embed_maternal_health_data_from_ntriples(rdf_file_path: str = None, format: str = None, db_dir: str = None) -> Dict[str, Any]:
        """
        n-triples 파일에서 직접 산모 건강 데이터를 임베딩합니다.
        """
        try:
            print(f"임베딩 시작: {rdf_file_path}")
            
            if rdf_file_path is None:
                rdf_file_path = RAGProcessor.RDF_FILE_PATH
                
            if db_dir is None:
                db_dir = os.path.join(RAGProcessor.DB_DIR, "maternal_health_db")
                
            # n-triples 파일 파싱
            print(f"n-triples 파일 파싱 중: {rdf_file_path}")
            subjects = RAGProcessor.parse_n_triples(rdf_file_path)
            
            # 임신 관련 키워드 목록
            pregnancy_keywords = [
                "임신", "출산", "산모", "태아", "영아", "아기", "pregnancy", 
                "childbirth", "maternal", "fetus", "infant", "baby",
                "PregnancyPeriod", "FirstTrimester", "SecondTrimester", "ThirdTrimester"
            ]
            
            # 임신 관련 주제 필터링
            pregnancy_subjects = {}
            for subject, triples in subjects.items():
                # 주제 URI에 임신 관련 키워드가 포함되어 있는지 확인
                if any(keyword in subject for keyword in pregnancy_keywords):
                    pregnancy_subjects[subject] = triples
                    continue
                    
                # 트리플에 임신 관련 키워드가 포함되어 있는지 확인
                for _, obj in triples:
                    if any(keyword in obj for keyword in pregnancy_keywords):
                        pregnancy_subjects[subject] = triples
                        break
            
            print(f"임신 관련 주제 {len(pregnancy_subjects)}개 발견")
            
            # 임베딩 생성
            texts, metadatas, ids = RAGProcessor.create_embeddings_from_subjects(pregnancy_subjects)
            
            # 벡터 데이터베이스 초기화
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
            vectorstore = Chroma(
                persist_directory=db_dir,
                embedding_function=embedding_function,
                collection_name="maternal_health_knowledge"
            )
            
            # 벡터 데이터베이스에 저장
            print(f"💾 벡터 데이터베이스 업데이트 시작")
            
            vectorstore._collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            print(f"✅ 벡터 데이터베이스 업데이트 완료: {len(texts)}개 문서")
            
            return {
                "file_path": rdf_file_path,
                "format": format,
                "triple_count": len(subjects),
                "embedded_resources": len(texts),
                "db_dir": db_dir
            }
            
        except Exception as e:
            print(f"❌ n-triples 파일 처리 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return {
                "error": str(e),
                "file_path": rdf_file_path,
                "format": format
            }

    @staticmethod
    def load_and_preprocess_csv(csv_pattern):
        """CSV 파일들을 찾아서 반환."""
        csv_files = glob.glob(csv_pattern)
        if not csv_files:
            print(f"CSV 파일을 찾을 수 없습니다: {csv_pattern}")
            return None
        print(f"처리할 CSV 파일: {len(csv_files)}개")
        for file in csv_files:
            print(f"- {file}")
        return csv_files

    @staticmethod
    def filter_processed_files(csv_files):
        """이미 처리된 파일을 제외하고 새로운 파일 목록만 반환."""
        processed_files = set(RAG_DB.objects.values_list('file_path', flat=True))
        new_files = [f for f in csv_files if f not in processed_files]
        print(f"처리할 새로운 CSV 파일: {len(new_files)}개")
        return new_files

    @staticmethod
    def initialize_chroma_db():
        """Chroma DB를 초기화하거나 기존 DB를 로드."""
        db_dir = RAGProcessor.DB_DIR
        print("\n=== Chroma DB 상태 ===")
        print(f"사용 중인 DB 경로: {db_dir}")
        print(f"절대 경로: {os.path.abspath(db_dir)}")
        
        # DB 파일 존재 여부 확인
        if os.path.exists(f"{db_dir}/chroma.sqlite3"):
            print(f"chroma.sqlite3 파일 크기: {os.path.getsize(f'{db_dir}/chroma.sqlite3')} bytes")
        
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", chunk_size=1000)

        if os.path.exists(db_dir) and os.path.exists(f"{db_dir}/chroma.sqlite3"):
            print("기존 Chroma DB 로드 중...")
            vectorstore = Chroma(
                persist_directory=db_dir,
                embedding_function=embeddings,
                collection_name="korean_dialogue"
            )
            existing_ids = set(vectorstore._collection.get()['ids'])
            print(f"기존 문서 수: {len(existing_ids)}")
        else:
            print("새로운 Chroma DB 생성")
            vectorstore = None
            existing_ids = set()

        return vectorstore, existing_ids

    @staticmethod
    def load_csv_with_metadata(csv_file):
        """CSV 파일을 로드하고 메타데이터를 추가합니다."""
        try:
            print(f"\n파일 처리 중: {csv_file}")
            
            # 중요 속성 목록 가져오기
            important_props = RAGProcessor.IMPORTANT_PROPERTIES
            
            # pandas가 없으면 CSVLoader 사용
            if not PANDAS_AVAILABLE:
                loader = CSVLoader(file_path=csv_file)
                docs = loader.load()
                
                # 각 문서에 메타데이터 추가
                for i, doc in enumerate(docs):
                    # 기존 메타데이터 보존
                    doc.metadata["source"] = csv_file
                    doc.metadata["row_index"] = i
                    
                    # 중요 속성 메타데이터 추출
                    content = doc.page_content
                    for prop in important_props:
                        if prop in content.lower():
                            # 해당 속성이 포함된 줄 찾기
                            lines = content.split('\n')
                            for line in lines:
                                if prop in line.lower():
                                    # 속성 이름과 값 추출
                                    if ':' in line:
                                        attr_name = line.split(':', 1)[0].strip()
                                        attr_value = line.split(':', 1)[1].strip()
                                        doc.metadata[f"important_{attr_name}"] = attr_value
                
                return docs
                
            # pandas를 사용한 처리
            df = pd.read_csv(csv_file)
            docs = []
            
            # 각 행을 문서로 변환
            for i, row in df.iterrows():
                # 텍스트 생성
                text_parts = []
                important_attrs = {}
                
                # 중요 속성 먼저 추가
                for col in df.columns:
                    if any(important_prop in col.lower() for important_prop in important_props) and pd.notna(row[col]):
                        text_parts.append(f"{col}: {row[col]}")
                        important_attrs[col] = str(row[col])
                
                # 나머지 속성 추가
                for col in df.columns:
                    if not any(important_prop in col.lower() for important_prop in important_props) and pd.notna(row[col]):
                        text_parts.append(f"{col}: {row[col]}")
                        
                        # 값에 중요 키워드가 포함된 경우 메타데이터에 추가
                        value = str(row[col])
                        for prop in important_props:
                            if prop in value.lower():
                                important_attrs[f"contains_{prop}_in_{col}"] = "true"
                
                # 최종 텍스트 생성
                text = "\n".join(text_parts)
                
                # 메타데이터 생성
                metadata = {
                    "source": csv_file,
                    "row_index": i,
                }
                
                # 메타데이터에 열 정보 추가
                for col in df.columns:
                    if pd.notna(row[col]):
                        metadata[col] = str(row[col])
                
                # 중요 속성 메타데이터 추가
                for k, v in important_attrs.items():
                    metadata[f"important_{k}"] = v
                
                # 문서 생성
                doc = Document(
                    page_content=text,
                    metadata=metadata
                )
                
                docs.append(doc)
            
            print(f"CSV 파일에서 {len(docs)}개 문서 생성 완료")
            return docs
            
        except Exception as e:
            print(f"❌ CSV 파일 로드 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return []

    @staticmethod
    def filter_new_documents(docs, existing_ids, csv_file):
        """이미 존재하는 문서를 제외하고 새 문서만 필터링."""
        new_docs = []
        for idx, doc in enumerate(docs):
            doc.metadata['source_file'] = os.path.basename(csv_file)
            unique_id = str(uuid.uuid4())
            doc_id = f"doc_{unique_id}_{idx}"
            if doc_id not in existing_ids:
                doc.metadata['doc_id'] = doc_id
                new_docs.append(doc)
        print(f"새로운 문서 발견: {len(new_docs)}개")
        return new_docs

    @staticmethod
    def split_documents(docs):
        """문서를 청크로 분할."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        splits = text_splitter.split_documents(docs)
        print(f"분할 완료: {len(splits)}개 청크")
        return splits

    @staticmethod
    def prepare_data_for_chroma(splits):
        """Chroma DB에 저장할 텍스트, 메타데이터, ID 준비."""
        texts, metadatas, ids = [], [], []
        
        # 중요 속성 목록 가져오기
        important_props = RAGProcessor.IMPORTANT_PROPERTIES
        
        for doc in splits:
            # 텍스트 내용에 중요 속성이 있는지 확인
            content = doc.page_content
            important_attrs = {}
            
            # 중요 속성을 메타데이터에 추가
            for prop in important_props:
                if prop in content.lower():
                    # 해당 속성이 포함된 줄 찾기
                    lines = content.split('\n')
                    for line in lines:
                        if prop in line.lower():
                            # 속성 이름과 값 추출
                            if ':' in line:
                                attr_name = line.split(':', 1)[0].strip()
                                attr_value = line.split(':', 1)[1].strip()
                                important_attrs[attr_name] = attr_value
            
            # 텍스트 내용 추가
            texts.append(f"content: {content}")
            
            # 기본 메타데이터 설정
            metadata = {
                "emotion": doc.metadata.get('emotion', ''),
                "source": doc.metadata.get('source', ''),
                "source_file": doc.metadata.get('source_file', '')
            }
            
            # 원본 메타데이터 복사
            for k, v in doc.metadata.items():
                if k not in metadata:
                    metadata[k] = v
                    
            # 중요 속성 메타데이터 추가
            for k, v in important_attrs.items():
                metadata[f"important_{k}"] = v
                
            metadatas.append(metadata)
            ids.append(doc.metadata.get('doc_id'))
        
        return texts, metadatas, ids

    @staticmethod
    async def create_embeddings_async(texts: List[str], pbar: tqdm, batch_size: int = 20, concurrent_tasks: int = 5) -> List[List[float]]:
        """텍스트 리스트의 임베딩을 비동기로 생성합니다."""
        embedding_function = OpenAIEmbeddings(
            model="text-embedding-3-small",
            chunk_size=1000
        )
        
        all_embeddings = []
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        semaphore = asyncio.Semaphore(concurrent_tasks)
        async def process_batch(batch):
            async with semaphore:
                await asyncio.sleep(0.1)
                return await embedding_function.aembed_documents(batch)
        tasks = [process_batch(batch) for batch in batches]
        for coro in asyncio.as_completed(tasks):
            embeddings = await coro
            if embeddings:
                all_embeddings.extend(embeddings)
                pbar.update(batch_size)
        return all_embeddings

    @staticmethod
    def get_optimal_embedding_params(num_texts: int) -> tuple[int, int]:
        """
        입력 텍스트의 총 개수(num_texts)와 CPU 코어 수를 기준으로 최적의 batch_size와
        concurrent_tasks 값을 계산합니다.

        Returns:
            tuple: (batch_size, concurrent_tasks)
        """
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        # 텍스트 수에 따라 배치 크기를 조정하는 간단한 heuristic
        if num_texts < 100:
            batch_size = 10
        elif num_texts < 1000:
            batch_size = 20
        else:
            batch_size = 50

        # 동시 실행 태스크는 CPU 코어 수와 상한값 10을 고려
        concurrent_tasks = min(10, cpu_count)
        print(
            f"Optimal Parameters determined: batch_size={batch_size}, "
            f"concurrent_tasks={concurrent_tasks} based on {num_texts} texts and {cpu_count} CPUs"
        )
        return batch_size, concurrent_tasks

    @staticmethod
    def create_embeddings(texts: List[str]) -> List[List[float]]:
        """동기 방식으로 비동기 임베딩 생성을 실행합니다.
        
        입력 텍스트의 수에 따라 최적의 batch_size와 concurrent_tasks를 계산하여 임베딩을 생성합니다.
        """
        batch_size, concurrent_tasks = RAGProcessor.get_optimal_embedding_params(len(texts))
        with tqdm(total=len(texts), desc="임베딩 생성 중") as pbar:
            embeddings = asyncio.run(
                RAGProcessor.create_embeddings_async(texts, pbar, batch_size, concurrent_tasks)
            )
        return embeddings

    @staticmethod
    def visualize_embedding_progress(total_files, processed_files, current_file, progress_pct):
        """임베딩 진행 상황을 시각적으로 표시합니다."""
        terminal_width = os.get_terminal_size().columns - 10
        bar_width = terminal_width - 40
        
        # 전체 진행 상황 계산
        overall_progress = (processed_files / total_files) * 100 if total_files > 0 else 0
        
        # 전체 진행 상황 바
        overall_filled = int(bar_width * overall_progress / 100)
        overall_bar = f"[{'=' * overall_filled}{' ' * (bar_width - overall_filled)}]"
        
        # 현재 파일 진행 상황 바
        file_filled = int(bar_width * progress_pct / 100)
        file_bar = f"[{'=' * file_filled}{' ' * (bar_width - file_filled)}]"
        
        # 출력
        print("\033[H\033[J")  # 화면 지우기
        print(f"📊 임베딩 진행 상황")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📁 전체 파일: {total_files}개 중 {processed_files}개 완료 ({overall_progress:.1f}%)")
        print(f"{overall_bar}")
        print(f"📄 현재 파일: {os.path.basename(current_file)} ({progress_pct:.1f}%)")
        print(f"{file_bar}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    @staticmethod
    def process_files(csv_files: List[str], existing_ids: set, vectorstore, db_dir: str):
        """CSV 파일들을 처리하고 진행상황을 시각화합니다."""
        total_new_docs = 0
        processed_count = 0
        total_files = len(csv_files)

        print("\n=== CSV 파일 처리 시작 ===")
        for idx, csv_file in enumerate(csv_files):
            try:
                # 진행 상황 표시
                RAGProcessor.visualize_embedding_progress(
                    total_files, 
                    processed_count, 
                    csv_file, 
                    (idx / total_files) * 100 if total_files > 0 else 0
                )
                
                # CSV 파일 로드 및 메타데이터 추가
                docs = RAGProcessor.load_csv_with_metadata(csv_file)
                if not docs:
                    continue

                # 새 문서 필터링
                new_docs = RAGProcessor.filter_new_documents(docs, existing_ids, csv_file)
                if not new_docs:
                    continue

                # 문서 분할
                total_new_docs += len(new_docs)
                splits = RAGProcessor.split_documents(new_docs)
                
                # 데이터 준비
                texts, metadatas, ids = RAGProcessor.prepare_data_for_chroma(splits)
                
                print(f"\n📄 [{os.path.basename(csv_file)}] 처리 중...")
                print(f"   - 텍스트 수: {len(texts)}개")
                
                # 임시 저장된 임베딩 확인
                temp_embeddings = RAGProcessor.load_temp_embeddings(csv_file)
                
                if temp_embeddings is not None:
                    print("💾 기존 임시 임베딩 사용")
                    embeddings = temp_embeddings
                else:
                    print("🔄 새로운 임베딩 생성 시작")
                    embeddings = RAGProcessor.create_embeddings(texts)
                    RAGProcessor.save_temp_embeddings(csv_file, embeddings)
                
                # Chroma DB 업데이트
                vectorstore = RAGProcessor.update_chroma_db(
                    vectorstore, texts, embeddings, metadatas, ids, db_dir
                )
                
                # 처리 완료 기록
                RAGProcessor.save_processed_file_info(csv_file)
                processed_count += 1
                
                # 최종 진행 상황 표시
                RAGProcessor.visualize_embedding_progress(
                    total_files, 
                    processed_count, 
                    csv_file, 
                    100.0
                )
                
                print(f"✅ [{os.path.basename(csv_file)}] 처리 완료\n")

            except Exception as e:
                print(f"❌ 파일 처리 중 오류 발생 ({os.path.basename(csv_file)}): {e}")
                continue

        return vectorstore, total_new_docs, processed_count

    @staticmethod
    def update_chroma_db(vectorstore, texts, embeddings, metadatas, ids, db_dir):
        """Chroma DB에 데이터를 배치 단위로 추가하고 진행상황을 표시합니다."""
        MAX_BATCH_SIZE = 5000

        if vectorstore is None:
            print("🔨 새로운 Chroma DB 생성 중...")
            embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
            vectorstore = Chroma(
                persist_directory=db_dir,
                embedding_function=embedding_function,
                collection_name="korean_dialogue"
            )

        total_batches = (len(texts) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        print(f"📦 Chroma DB 업데이트 시작 (총 {total_batches}개 배치)")
        
        for i in tqdm(range(0, len(texts), MAX_BATCH_SIZE), desc="💫 DB 업데이트"):
            end_idx = min(i + MAX_BATCH_SIZE, len(texts))
            vectorstore._collection.add(
                embeddings=embeddings[i:end_idx],
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
        
        print(f"✨ DB 업데이트 완료 (총 {len(texts)}개 문서)")
        return vectorstore

    @staticmethod
    async def async_update_chroma_db(vectorstore, texts, embeddings, metadatas, ids, db_dir):
        """
        비동기 방식으로 Chroma DB를 업데이트합니다.
        최대 배치 사이즈 5000개를 고려하여 vectorstore._collection.add 호출을
        asyncio.to_thread로 감싸서 동시에 실행합니다.

        Returns:
            업데이트된 vectorstore 인스턴스.
        """
        MAX_BATCH_SIZE = 5000
        total_batches = (len(texts) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        print(f"📦 비동기 Chroma DB 업데이트 시작 (총 {total_batches}개 배치)")
        tasks = []
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            end_idx = min(i + MAX_BATCH_SIZE, len(texts))
            tasks.append(
                asyncio.to_thread(
                    vectorstore._collection.add,
                    embeddings=embeddings[i:end_idx],
                    documents=texts[i:end_idx],
                    metadatas=metadatas[i:end_idx],
                    ids=ids[i:end_idx]
                )
            )
        await asyncio.gather(*tasks)
        print(f"✨ 비동기 DB 업데이트 완료 (총 {len(texts)}개 문서)")
        return vectorstore

    @staticmethod
    def save_processed_file_info(csv_file):
        """처리된 파일 정보를 DB에 저장."""
        RAG_DB.objects.create(file_name=os.path.basename(csv_file), file_path=csv_file)

    @staticmethod
    def get_temp_embedding_path(file_name):
        """임시 임베딩 파일 경로를 반환합니다."""
        if not os.path.exists(RAGProcessor.TEMP_DIR):
            os.makedirs(RAGProcessor.TEMP_DIR)
        return os.path.join(RAGProcessor.TEMP_DIR, f"{os.path.basename(file_name)}.pkl")

    @staticmethod
    def save_temp_embeddings(file_name, data):
        """임베딩 데이터를 임시 파일로 저장합니다."""
        temp_path = RAGProcessor.get_temp_embedding_path(file_name)
        with open(temp_path, 'wb') as f:
            pickle.dump(data, f)

    @staticmethod
    def load_temp_embeddings(file_name):
        """임시 저장된 임베딩 데이터를 로드합니다."""
        temp_path = RAGProcessor.get_temp_embedding_path(file_name)
        if os.path.exists(temp_path):
            with open(temp_path, 'rb') as f:
                return pickle.load(f)
        return None

    @staticmethod
    def process_conversation_json(conversation, existing_ids, vectorstore):
        """JSON 대화 데이터를 처리하고 임베딩합니다."""
        try:
            # 대화 정보 추출
            info = conversation.get("info", {})
            utterances = conversation.get("utterances", [])
            
            # 메타데이터 준비
            base_metadata = {
                "source": "conversation",
                "conversation_id": info.get("id", ""),
                "domain": info.get("domain", ""),
                "topic": info.get("topic", ""),
                "scenario": info.get("scenario", "")
            }
            
            # 중요 속성 목록 사용
            important_props = RAGProcessor.IMPORTANT_PROPERTIES
            
            # 텍스트 및 메타데이터 준비
            texts = []
            metadatas = []
            ids = []
            
            # 대화 컨텍스트 추적
            context = []
            
            # 각 발화 처리
            for idx, utterance in enumerate(utterances):
                # 발화 정보 추출
                speaker = utterance.get("speaker", "")
                text = utterance.get("text", "")
                
                # 빈 발화 건너뛰기
                if not text.strip():
                    continue
                
                # 컨텍스트 업데이트
                context.append(f"{speaker}: {text}")
                
                # 컨텍스트 윈도우 유지 (최대 5개 발화)
                if len(context) > 5:
                    context = context[-5:]
                
                # 현재 컨텍스트 문자열 생성
                context_str = "\n".join(context)
                
                # 메타데이터 생성
                metadata = base_metadata.copy()
                metadata.update({
                    "speaker": speaker,
                    "utterance_index": idx,
                    "text": text
                })
                
                # 중요 속성 식별 및 추가
                important_attrs = {}
                
                # 텍스트에서 중요 속성 찾기
                for prop in important_props:
                    if prop in text.lower():
                        important_attrs[f"contains_{prop}"] = "true"
                
                # 각 발화의 모든 필드에서 중요 속성 찾기
                for key, value in utterance.items():
                    if isinstance(value, str):
                        # 값이 중요 속성을 포함하는지 확인
                        for prop in important_props:
                            if prop in value.lower():
                                important_attrs[f"contains_{prop}_in_{key}"] = "true"
                                
                        # 키가 중요 속성과 관련되어 있는지 확인
                        if any(prop in key.lower() for prop in important_props):
                            important_attrs[key] = value
                
                # 중요 속성 메타데이터 추가
                for k, v in important_attrs.items():
                    metadata[k] = v
                
                # 고유 ID 생성
                doc_id = f"conv_{info.get('id', '')}_{idx}"
                
                # 이미 처리된 ID 건너뛰기
                if doc_id in existing_ids:
                    continue
                
                # 데이터 추가
                texts.append(context_str)
                metadatas.append(metadata)
                ids.append(doc_id)
            
            # 임베딩 생성 및 저장
            if texts:
                print(f"🧠 대화 임베딩 생성 시작: {len(texts)}개 텍스트")
                embeddings = RAGProcessor.create_embeddings(texts)
                
                print(f"💾 벡터 데이터베이스 업데이트 시작")
                RAGProcessor.update_chroma_db(
                    vectorstore, texts, embeddings, metadatas, ids, RAGProcessor.DB_DIR
                )
                
                print(f"✅ 벡터 데이터베이스 업데이트 완료: {len(texts)}개 문서")
            
            return vectorstore, len(texts), len(texts)
            
        except Exception as e:
            print(f"❌ 대화 데이터 처리 중 오류 발생: {str(e)}")
            return vectorstore, 0, 0

    @staticmethod
    def process_rdf_data(rdf_file_path: str = None, format: str = None) -> Dict[str, Any]:
        """
        RDF 데이터를 처리하고 임베딩합니다.
        """
        try:
            # RDF 파일 경로 설정
            if rdf_file_path is None:
                rdf_file_path = RAGProcessor.RDF_FILE_PATH
            
            # RDF 프로세서 초기화
            processor = RDFProcessor(rdf_file_path, format)
            
            # 임신 관련 키워드 목록
            pregnancy_keywords = [
                "임신", "출산", "산모", "태아", "영아", "아기", "pregnancy", 
                "childbirth", "maternal", "fetus", "infant", "baby",
                "PregnancyPeriod", "FirstTrimester", "SecondTrimester", "ThirdTrimester"
            ]
            
            # 임신 관련 리소스 조회 쿼리
            pregnancy_resources_query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?resource ?label WHERE {{
                {{
                    ?resource ?p ?o .
                    FILTER(isURI(?resource))
                    OPTIONAL {{ ?resource rdfs:label ?label }}
                    FILTER(
                        {" || ".join([f'CONTAINS(LCASE(STR(?resource)), "{keyword.lower()}")' for keyword in pregnancy_keywords])}
                    )
                }} UNION {{
                    ?resource ?p ?o .
                    FILTER(isURI(?resource))
                    OPTIONAL {{ ?resource rdfs:label ?label }}
                    FILTER(
                        {" || ".join([f'CONTAINS(LCASE(STR(?o)), "{keyword.lower()}")' for keyword in pregnancy_keywords])}
                    )
                }}
            }}
            LIMIT 1000
            """
            
            # 임신 관련 리소스 조회
            resource_results = processor.execute_query(pregnancy_resources_query)
            print(f"🔢 임신 관련 리소스 발견: {len(resource_results)}개")
            
            # 리소스 URI 추출
            resource_uris = [result["resource"] for result in resource_results]
            
            print(f"디버깅: 발견된 리소스 URI 샘플: {resource_uris[:5] if len(resource_uris) > 5 else resource_uris}")
            
            # 임베딩 생성을 위한 텍스트 및 메타데이터 준비
            texts = []
            metadatas = []
            ids = []
            
            # 중요 속성 목록 사용
            important_props = RAGProcessor.IMPORTANT_PROPERTIES
            
            # 디버깅 정보 추가
            processed_resources = 0
            total_text_parts = 0
            
            # 각 리소스에 대한 정보 가져오기
            for i, uri in enumerate(tqdm(resource_uris, desc="리소스 처리")):
                # 리소스 정보 가져오기
                resource_info = processor.get_resource_info(uri)
                
                # 리소스 레이블 가져오기
                label = next((result.get("label") for result in resource_results if result.get("resource") == uri), None)
                if label is None:
                    label = processor.get_label(uri)
                
                # 텍스트 생성
                text_parts = [f"주제: {label or uri}"]
                
                # 중요 속성 관련 메타데이터 추출
                important_attrs = {}
                
                # 중요 속성 먼저 추가
                for prop_key in resource_info:
                    if any(important_prop in prop_key.lower() for important_prop in important_props):
                        values = resource_info[prop_key]
                        values_str = ", ".join(str(v) for v in values)
                        text_parts.append(f"{prop_key}: {values_str}")
                        
                        # 중요 속성 메타데이터에 추가
                        attr_name = prop_key.split('/')[-1].split('#')[-1]
                        important_attrs[attr_name] = values_str
                
                # 나머지 속성 추가
                for prop_key in resource_info:
                    if not any(important_prop in prop_key.lower() for important_prop in important_props):
                        values = resource_info[prop_key]
                        values_str = ", ".join(str(v) for v in values)
                        text_parts.append(f"{prop_key}: {values_str}")
                        
                        # 객체에 중요 키워드가 포함된 경우에도 메타데이터에 추가
                        for value in values:
                            for prop in important_props:
                                if isinstance(value, str) and prop in value.lower():
                                    attr_name = prop_key.split('/')[-1].split('#')[-1]
                                    important_attrs[f"related_{attr_name}"] = str(value)
                
                # 최종 텍스트 생성
                text = "\n".join(text_parts)
                
                # 텍스트 길이 확인 (너무 짧은 텍스트는 건너뛰기)
                if len(text) < 50:
                    print(f"경고: 텍스트가 너무 짧음 ({len(text)}자) - {uri}")
                    continue
                
                # 메타데이터 생성
                metadata = {
                    "source": rdf_file_path,
                    "uri": uri,
                    "label": label or "",
                }
                
                # 중요 속성 메타데이터 추가
                for k, v in important_attrs.items():
                    metadata[f"important_{k}"] = v
                
                # 데이터 추가
                texts.append(text)
                metadatas.append(metadata)
                ids.append(f"rdf-{i}")
                
                # 디버깅 정보 업데이트
                processed_resources += 1
                total_text_parts += len(text_parts)
            
            # 디버깅 정보 출력
            print(f"디버깅: 처리된 리소스 수: {processed_resources}")
            print(f"디버깅: 평균 텍스트 부분 수: {total_text_parts / processed_resources if processed_resources > 0 else 0}")
            
            # 임베딩 생성
            print(f"🧠 데이터 임베딩 생성 시작: {len(texts)}개 텍스트")
            
            # 텍스트가 없는 경우 처리
            if len(texts) == 0:
                print("⚠️ 임베딩할 텍스트가 없습니다. 처리를 중단합니다.")
                return {
                    "file_path": rdf_file_path,
                    "format": format,
                    "resource_count": len(resource_uris),
                    "embedded_resources": 0,
                    "db_dir": RAGProcessor.DB_DIR,
                    "warning": "임베딩할 텍스트가 없습니다."
                }
                
            embeddings = RAGProcessor.create_embeddings(texts)
            
            # Chroma DB 초기화
            vectorstore, _ = RAGProcessor.initialize_chroma_db()
            
            # Chroma DB 업데이트
            print(f"💾 벡터 데이터베이스 업데이트 시작")
            RAGProcessor.update_chroma_db(
                vectorstore, texts, embeddings, metadatas, ids, RAGProcessor.DB_DIR
            )
            
            print(f"✅ 벡터 데이터베이스 업데이트 완료: {len(texts)}개 문서")
            
            return {
                "file_path": rdf_file_path,
                "format": format,
                "resource_count": len(resource_uris),
                "embedded_resources": len(texts),
                "db_dir": RAGProcessor.DB_DIR
            }
            
        except Exception as e:
            print(f"❌ RDF 데이터 처리 중 오류 발생: {str(e)}")
            traceback.print_exc()
            return {
                "error": str(e),
                "file_path": rdf_file_path,
                "format": format
            }

class RAGQuery:
    @staticmethod
    def create_qa_chain():
        """공유된 DB_DIR을 사용하여 QA 체인 생성"""
        db_dir = RAGProcessor.DB_DIR
        vectorstore = Chroma(
            persist_directory=db_dir,
            embedding_function=OpenAIEmbeddings(
                model="text-embedding-3-small"
            ),
            collection_name="korean_dialogue"
        )
        
        # 필터 제거하고 테스트
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 10},  # 상위 10개 결과
            filter={"emotion": "happy"},
        )
        
        # 디버깅을 위한 컬렉션 정보 출력
        print(f"컬렉션 내 문서 수: {vectorstore._collection.count()}")
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7
        )

        # 프롬프트 템플릿 수정: 채팅 히스토리와 리트리브된 문서를 별도의 키로 전달
        template = """당신은 산모를 위한 친절한 상담사입니다. 모든 질문은 산모가 하는 것으로 간주하고 응답해주세요.
        
        검색된 정보:
        {retrieved_context}
        
        산모의 질문:
        {question}
        
        답변 시 주의사항:
        1. 산모의 입장에서 공감하고 지지하는 태도로 응답하세요.
        2. 산모의 불안을 줄이고 안심시키는 방향으로 답변하세요.
        3. 답변은 친절하고 따뜻한 말투로 작성하세요.
        4. "~님"과 같은 존칭을 사용하여 존중하는 태도를 보여주세요.
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm
        
        return retriever, chain

    @staticmethod
    def create_maternal_health_qa_chain():
        """산모 건강 데이터를 위한 QA 체인 생성"""
        maternal_db_dir = os.path.join(RAGProcessor.DB_DIR, "maternal_health_db")
        
        # 산모 건강 데이터베이스가 존재하는지 확인
        if not os.path.exists(maternal_db_dir):
            print(f"산모 건강 데이터베이스가 존재하지 않습니다: {maternal_db_dir}")
            # 기본 데이터베이스 사용
            return RAGQuery.create_qa_chain()
        
        vectorstore = Chroma(
            persist_directory=maternal_db_dir,
            embedding_function=OpenAIEmbeddings(
                model="text-embedding-3-small"
            ),
            collection_name="maternal_health_knowledge"
        )
        
        # 디버깅을 위한 컬렉션 정보 출력
        print(f"산모 건강 컬렉션 내 문서 수: {vectorstore._collection.count()}")
        
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5},  # 상위 5개 결과
        )
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.5  # 의료 정보는 더 정확하게
        )

        # 산모 건강 관련 프롬프트 템플릿
        template = """당신은 산모를 위한 친절하고 공감적인 건강 상담사입니다. 모든 질문은 산모가 하는 것으로 간주하고 응답해주세요.
        
        다음은 산모 건강 관련 지식 그래프에서 검색된 정보입니다:
        {retrieved_context}
        
        산모의 질문:
        {question}
        
        답변 시 주의사항:
        1. 산모의 입장에서 공감하고 지지하는 태도로 응답하세요.
        2. 검색된 정보를 기반으로 정확한 답변을 제공하되, 의학적 정보는 신중하게 전달하세요.
        3. 산모의 불안을 줄이고 안심시키는 방향으로 답변하되, 사실에 기반해야 합니다.
        4. 필요한 경우 의사와 상담할 것을 권유하세요.
        5. 답변은 친절하고 따뜻한 말투로 작성하세요.
        6. 산모가 겪을 수 있는 감정적 어려움에 공감하고, 정서적 지원을 제공하세요.
        7. "~님"과 같은 존칭을 사용하여 존중하는 태도를 보여주세요.
        8. 산모의 건강과 아기의 건강 모두를 고려한 조언을 제공하세요.
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm
        
        return retriever, chain

    @staticmethod
    def get_answer(question: str):
        # 벡터스토어에서 추가적인 문서(대화 관련 문맥) 가져오기
        retriever, chain = RAGQuery.create_qa_chain()
        retrieved_docs = retriever.invoke(question)
        retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])
        print(f"Retrieved Context: {retrieved_context}")
        result = chain.invoke({
            "retrieved_context": retrieved_context,
            "question": question
        })
        return result.content
        
    @staticmethod
    def get_maternal_health_answer(question: str):
        """산모 건강 관련 질문에 대한 답변 생성"""
        # 모든 질문을 산모 건강 관련 질문으로 처리
        # 산모 건강 QA 체인 사용
        retriever, chain = RAGQuery.create_maternal_health_qa_chain()
        
        retrieved_docs = retriever.invoke(question)
        retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])

        print(f"Retrieved Context: {retrieved_context}")
        result = chain.invoke({
            "retrieved_context": retrieved_context,
            "question": question
        })
        return result.content