from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from .method import RAGProcessor, RAGQuery, RDFProcessor
from .models import RAG_DB
from dotenv import load_dotenv
import os
from tqdm import tqdm
import json
import time
import glob
import rdflib
from rdflib import URIRef

# 환경 변수 로드
load_dotenv()

# RAGProcessor에서 정의된 경로 사용
DB_DIR = RAGProcessor.DB_DIR
CSV_PATTERN = "data/rag/*.csv"

# DB_DIR이 존재하지 않으면 생성
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

class RAGQueryView(APIView):
    """
    RAG 시스템에 질의하는 API 뷰
    
    Endpoints:
        GET /rag/query/: API 사용 방법 반환
        POST /rag/query/: RAG 시스템에 질의
    """
    parser_classes = (JSONParser,)
    permission_classes = []  # 인증 비활성화
    
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': 'RAG 쿼리 API',
            'usage': {
                'method': 'POST',
                'description': 'RAG 시스템에 질의합니다.',
                'endpoint': '/v1/rag/query/',
                'parameters': {
                    'query': '(필수) 쿼리 텍스트',
                    'max_tokens': '(선택) 응답 최대 토큰 수',
                    'use_maternal_health': '(선택) 산모 건강 데이터 사용 여부 (기본값: true)'
                }
            }
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """RAG 시스템에 질의합니다. 모든 질문은 산모가 하는 것으로 간주합니다."""
        try:
            query = request.data.get('query')
            max_tokens = request.data.get('max_tokens', 150)
            use_maternal_health = request.data.get('use_maternal_health', True)  # 기본값을 True로 변경
            
            if not query:
                return Response({
                    'error': '쿼리가 제공되지 않았습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 모든 질문을 산모 건강 관련 질문으로 처리
            retriever, chain = RAGQuery.create_maternal_health_qa_chain()
            retrieved_docs = retriever.invoke(query)
            retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])
            result = chain.invoke({
                "retrieved_context": retrieved_context,
                "question": query
            }).content
            
            return Response({
                'message': 'RAG 쿼리 완료',
                'query': query,
                'result': result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error code: {e.__class__.__name__} - {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RAGAutoEmbedView(APIView):
    """
    data 폴더의 모든 파일을 자동으로 임베딩하는 API 뷰
    
    Endpoints:
        GET /rag/auto-embed/: API 사용 방법 반환
        POST /rag/auto-embed/: 모든 데이터 파일 자동 임베딩
    """
    permission_classes = []  # 인증 비활성화
    
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': '자동 임베딩 API',
            'usage': {
                'method': 'POST',
                'description': 'data 폴더의 모든 파일을 자동으로 임베딩합니다.',
                'endpoint': '/v1/rag/auto-embed/',
                'parameters': {
                    'data_dir': '(선택) 데이터 디렉토리 경로. 기본값은 "data"',
                    'file_types': '(선택) 처리할 파일 유형 목록. 기본값은 ["csv", "json", "rdf", "xml"]',
                    'force_reprocess': '(선택) 이미 처리된 파일도 다시 처리할지 여부. 기본값은 false'
                }
            }
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """모든 데이터 파일을 자동으로 임베딩합니다."""
        try:
            data_dir = request.data.get('data_dir', 'data')
            file_types = request.data.get('file_types', ['csv', 'json', 'rdf', 'xml'])
            force_reprocess = request.data.get('force_reprocess', False)
            
            # 결과 저장 변수
            results = {
                'total_files_found': 0,
                'new_files_processed': 0,
                'skipped_files': 0,
                'failed_files': 0,
                'total_documents_embedded': 0,
                'processing_time': 0,
                'file_details': []
            }
            
            # 처리할 파일 목록 생성
            all_files = []
            for file_type in file_types:
                file_pattern = os.path.join(data_dir, f"**/*.{file_type}")
                files = glob.glob(file_pattern, recursive=True)
                for file in files:
                    all_files.append((file, file_type))
            
            results['total_files_found'] = len(all_files)
            
            # 이미 처리된 파일 목록 가져오기
            processed_files = set(RAG_DB.objects.values_list('file_path', flat=True))
            
            # 시작 시간 기록
            start_time = time.time()
            
            # 파일 처리
            with tqdm(total=len(all_files), desc="📂 전체 파일 진행률") as pbar:
                # 초기 진행률 메시지 설정
                pbar.set_postfix_str(f"처리: 0개, 스킵: 0개")
                
                for file_path, file_type in all_files:
                    file_result = {
                        'file_path': file_path,
                        'file_type': file_type,
                        'status': '',
                        'documents_embedded': 0
                    }
                    
                    try:
                        # 이미 처리된 파일인지 확인
                        if file_path in processed_files and not force_reprocess:
                            file_result['status'] = 'skipped (already processed)'
                            results['skipped_files'] += 1
                            results['file_details'].append(file_result)
                            pbar.update(1)
                            # 스킵된 파일 표시
                            pbar.set_postfix_str(f"처리: {results['new_files_processed']}개, 스킵: {results['skipped_files']}개")
                            continue
                        
                        # force_reprocess=true이고 이미 처리된 파일인 경우, 기존 레코드 삭제
                        if file_path in processed_files and force_reprocess:
                            RAG_DB.objects.filter(file_path=file_path).delete()
                        
                        # 파일 확장자 확인
                        file_ext = os.path.splitext(file_path)[1].lower()
                        
                        # 파일 이름에서 건강 관련 키워드 확인
                        file_name = os.path.basename(file_path).lower()
                        health_keywords = ['health', 'medical', 'wellness', '건강', '의료', '웰니스', '산모', '임신', '출산', 'maternal', 'pregnancy']
                        is_health_related = any(keyword in file_name for keyword in health_keywords)
                        
                        if file_ext == '.csv':
                            # CSV 파일 처리
                            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()
                            
                            # CSV 파일 로드 및 메타데이터 추가
                            docs = RAGProcessor.load_csv_with_metadata(file_path)
                            if not docs:
                                raise ValueError("CSV 파일을 로드할 수 없습니다.")
                            
                            # 새 문서 필터링
                            new_docs = RAGProcessor.filter_new_documents(docs, existing_ids, file_path)
                            
                            # 문서 분할
                            splits = RAGProcessor.split_documents(new_docs)
                            
                            # 데이터 준비
                            texts, metadatas, ids = RAGProcessor.prepare_data_for_chroma(splits)
                            
                            # 임베딩 생성
                            embeddings = RAGProcessor.create_embeddings(texts)
                            
                            # Chroma DB 업데이트
                            RAGProcessor.update_chroma_db(
                                vectorstore, texts, embeddings, metadatas, ids, DB_DIR
                            )
                            
                            # 처리 완료 기록
                            RAG_DB.objects.create(file_name=os.path.basename(file_path), file_path=file_path)
                            
                            file_result['status'] = 'success'
                            file_result['documents_embedded'] = len(new_docs)
                            results['total_documents_embedded'] += len(new_docs)
                            
                        elif file_ext == '.json':
                            # JSON 파일 처리
                            with open(file_path, "r", encoding="utf-8") as f:
                                file_content = f.read()
                            
                            try:
                                conversation = json.loads(file_content)
                            except Exception as e:
                                raise ValueError(f"유효하지 않은 JSON 파일: {str(e)}")
                            
                            # 필수 키 체크: info와 utterances 필요
                            if not {"info", "utterances"}.issubset(conversation.keys()):
                                raise ValueError("JSON 파일은 info와 utterances 키를 포함해야 합니다.")
                            
                            # Chroma DB 초기화
                            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()
                            
                            # JSON 파일 처리
                            vectorstore, new_docs, count = RAGProcessor.process_conversation_json(
                                conversation, existing_ids, vectorstore
                            )
                            
                            # 처리 완료 기록
                            RAG_DB.objects.create(file_name=os.path.basename(file_path), file_path=file_path)
                            
                            file_result['status'] = 'success'
                            file_result['documents_embedded'] = new_docs
                            results['total_documents_embedded'] += new_docs
                            
                        elif file_ext in ['.rdf', '.xml', '.n-triples', '.nt']:
                            # RDF 파일 처리
                            # 건강 관련 파일인 경우 산모 건강 데이터 처리 방식 사용
                            if is_health_related:
                                print(f"건강 관련 데이터로 처리: {file_path}")
                                # n-triples 파일인 경우 직접 파싱 방식 사용
                                if file_ext in ['.n-triples', '.nt']:
                                    result = RAGProcessor.embed_maternal_health_data_from_ntriples(file_path, format='nt')
                                else:
                                    result = RAGProcessor.embed_maternal_health_data(file_path)
                            else:
                                # 일반 RDF 파일 처리
                                result = RAGProcessor.process_rdf_data(file_path)
                            
                            # 처리 완료 기록
                            RAG_DB.objects.create(file_name=os.path.basename(file_path), file_path=file_path)
                            
                            file_result['status'] = 'success'
                            file_result['documents_embedded'] = result.get('embedded_resources', 0)
                            results['total_documents_embedded'] += result.get('embedded_resources', 0)
                        
                        results['new_files_processed'] += 1
                        # 처리된 파일 수 표시
                        pbar.set_postfix_str(f"처리: {results['new_files_processed']}개, 스킵: {results['skipped_files']}개")
                        
                    except Exception as e:
                        file_result['status'] = 'failed'
                        file_result['error'] = str(e)
                        results['failed_files'] += 1
                        # 실패한 파일 표시
                        pbar.set_postfix_str(f"처리: {results['new_files_processed']}개, 스킵: {results['skipped_files']}개, 실패: {results['failed_files']}개")
                    
                    results['file_details'].append(file_result)
                    pbar.update(1)
            
            # 처리 시간 계산
            end_time = time.time()
            results['processing_time'] = round(end_time - start_time, 2)
            
            # 결과 요약 생성
            summary = {
                'message': '자동 임베딩 완료',
                'total_files_found': results['total_files_found'],
                'new_files_processed': results['new_files_processed'],
                'skipped_files': results['skipped_files'],
                'failed_files': results['failed_files'],
                'total_documents_embedded': results['total_documents_embedded'],
                'processing_time_seconds': results['processing_time'],
                'file_details': results['file_details']
            }
            
            return Response(summary, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RDFQueryView(APIView):
    """
    RDF 데이터에 직접 SPARQL 쿼리를 실행하는 API 뷰
    
    Endpoints:
        GET /rag/rdf-query/: API 사용 방법 반환
        POST /rag/rdf-query/: RDF 데이터에 SPARQL 쿼리 실행
    """
    parser_classes = (JSONParser,)
    permission_classes = []  # 인증 비활성화
    
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': 'RDF 쿼리 API',
            'usage': {
                'method': 'POST',
                'description': 'RDF 데이터에 SPARQL 쿼리를 실행합니다.',
                'endpoint': '/v1/rag/rdf-query/',
                'parameters': {
                    'query': '(필수) SPARQL 쿼리 문자열',
                    'rdf_file': '(선택) 쿼리할 RDF 파일 경로 (기본값: data/rdf/wellness.rdf)',
                    'format': '(선택) RDF 파일 형식 (기본값: xml)',
                    'resource_uri': '(선택) 특정 리소스에 대한 모든 정보를 조회할 경우 리소스 URI'
                },
                'examples': {
                    'basic_query': {
                        'query': 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10'
                    },
                    'resource_info': {
                        'resource_uri': 'http://www.wellness.ai/resource/29-222'
                    }
                }
            }
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """RDF 데이터에 SPARQL 쿼리를 실행합니다."""
        try:
            # 기본 파일 경로 및 형식 설정
            rdf_file = request.data.get('rdf_file', 'data/rdf/wellness.rdf')
            format = request.data.get('format', 'xml')
            
            # RDF 프로세서 초기화
            processor = RDFProcessor(rdf_file, format)
            
            # 리소스 URI가 제공된 경우 해당 리소스 정보 반환
            resource_uri = request.data.get('resource_uri')
            if resource_uri:
                # 리소스 정보 조회
                resource_info = processor.get_resource_info(resource_uri)
                
                # 라벨 정보 추가
                label = processor.get_label(resource_uri)
                
                # 결과를 보기 좋게 가공
                formatted_result = {
                    'uri': resource_uri,
                    'label': label,
                    'properties': {}
                }
                
                # 속성 정보 처리
                for pred, values in resource_info.items():
                    pred_label = processor.get_label(pred) or (pred.split('/')[-1] if pred else 'unknown')
                    formatted_values = []
                    
                    for value in values:
                        if isinstance(value, str) and value.startswith('http'):
                            value_label = processor.get_label(value)
                            formatted_values.append({
                                'uri': value,
                                'label': value_label
                            })
                        else:
                            formatted_values.append(value)
                    
                    formatted_result['properties'][pred_label] = formatted_values
                
                # 추가로 Turtle 형식의 결과도 제공
                g = rdflib.Graph()
                g.parse(rdf_file, format=format)
                
                subject = URIRef(resource_uri)
                subgraph = rdflib.Graph()
                for s, p, o in g.triples((subject, None, None)):
                    subgraph.add((s, p, o))
                
                turtle_format = subgraph.serialize(format="turtle")
                
                return Response({
                    'resource_info': formatted_result,
                    'turtle_format': turtle_format,
                    'triples_count': len(list(subgraph))
                }, status=status.HTTP_200_OK)
            
            # SPARQL 쿼리가 제공된 경우 쿼리 실행
            query = request.data.get('query')
            if not query:
                return Response({
                    'error': 'SPARQL 쿼리 또는 리소스 URI가 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 쿼리 실행
            results = processor.execute_query(query)
            
            # 결과 카운트 추가
            results_count = len(results)
            
            return Response({
                'results': results,
                'count': results_count,
                'query': query
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RDFAnalysisView(APIView):
    """
    RDF 쿼리 결과를 분석하고 활용하는 API 뷰
    
    Endpoints:
        GET /rag/rdf-analysis/: API 사용 방법 반환
        POST /rag/rdf-analysis/: RDF 데이터 분석 및 활용
    """
    parser_classes = (JSONParser,)
    permission_classes = []  # 인증 비활성화
    
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': 'RDF 데이터 분석 API',
            'usage': {
                'method': 'POST',
                'description': 'RDF 데이터를 분석하고 활용합니다.',
                'endpoint': '/v1/rag/rdf-analysis/',
                'parameters': {
                    'action': '(필수) 수행할 분석 작업 종류 (resource_relations, keyword_search, category_stats, resource_summary)',
                    'rdf_file': '(선택) 분석할 RDF 파일 경로 (기본값: data/rdf/wellness.n-triples)',
                    'format': '(선택) RDF 파일 형식 (기본값: nt)',
                    'resource_uri': '(조건부 필수) action이 resource_relations, resource_summary인 경우 필요한 리소스 URI',
                    'keyword': '(조건부 필수) action이 keyword_search인 경우 필요한 검색 키워드',
                    'category': '(조건부 필수) action이 category_stats인 경우 필요한 카테고리(타입) URI',
                    'depth': '(선택) 관계 탐색 깊이 (기본값: 1)'
                },
                'examples': {
                    'resource_relations': {
                        'action': 'resource_relations',
                        'resource_uri': 'http://www.wellness.ai/resource/02-016',
                        'depth': 2
                    },
                    'keyword_search': {
                        'action': 'keyword_search',
                        'keyword': '임신'
                    },
                    'category_stats': {
                        'action': 'category_stats',
                        'category': 'http://www.wellness.ai/schema/class/Disease'
                    },
                    'resource_summary': {
                        'action': 'resource_summary',
                        'resource_uri': 'http://www.wellness.ai/resource/02-016'
                    }
                }
            }
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """RDF 데이터를 분석하고 활용합니다."""
        try:
            # 기본 파라미터 설정
            action = request.data.get('action')
            rdf_file = request.data.get('rdf_file', 'data/rdf/wellness.n-triples')
            format = request.data.get('format', 'nt')
            
            if not action:
                return Response({
                    'error': '분석 작업 종류(action)를 지정해야 합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # RDF 프로세서 초기화
            processor = RDFProcessor(rdf_file, format)
            
            # 작업 종류에 따라 분석 수행
            if action == 'resource_relations':
                return self._analyze_resource_relations(request, processor)
            elif action == 'keyword_search':
                return self._analyze_keyword_search(request, processor)
            elif action == 'category_stats':
                return self._analyze_category_stats(request, processor)
            elif action == 'resource_summary':
                return self._analyze_resource_summary(request, processor)
            else:
                return Response({
                    'error': f'지원하지 않는 분석 작업입니다: {action}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            import traceback
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _analyze_resource_relations(self, request, processor):
        """리소스의 관계 네트워크를 분석합니다."""
        resource_uri = request.data.get('resource_uri')
        depth = int(request.data.get('depth', 1))
        
        if not resource_uri:
            return Response({
                'error': 'resource_uri가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 리소스 라벨 조회
        resource_label = processor.get_label(resource_uri) or resource_uri.split('/')[-1]
        
        # 관계 네트워크 구축
        network = self._build_relation_network(processor, resource_uri, depth)
        
        # 정렬된 관계 그룹 생성
        relation_groups = {}
        for relation in network:
            rel_type = relation['relation_type']
            if rel_type not in relation_groups:
                relation_groups[rel_type] = []
            relation_groups[rel_type].append(relation)
        
        return Response({
            'resource_uri': resource_uri,
            'resource_label': resource_label,
            'relations_count': len(network),
            'relation_groups': relation_groups,
            'depth': depth
        }, status=status.HTTP_200_OK)
    
    def _build_relation_network(self, processor, resource_uri, depth=1, visited=None):
        """리소스의 관계 네트워크를 재귀적으로 구축합니다."""
        if visited is None:
            visited = set()
        
        if resource_uri in visited or depth <= 0:
            return []
        
        visited.add(resource_uri)
        relations = []
        
        # 주어진 리소스가 주어인 트리플 탐색
        query = f"""
        SELECT ?p ?o WHERE {{
            <{resource_uri}> ?p ?o .
            FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            FILTER(?p != <http://www.wellness.ai/resource>)
        }}
        """
        print(f"[DEBUG] 쿼리 실행: {query}")
        
        # 직접 RDF 그래프에서 트리플 조회
        resource = rdflib.URIRef(resource_uri)
        
        # 트리플 직접 조회
        for s, p, o in processor.graph.triples((resource, None, None)):
            # type과 resource 속성은 제외
            if p == rdflib.RDF.type or str(p) == "http://www.wellness.ai/resource":
                continue
                
            pred = str(p)
            
            # URI인 경우에만 라벨 조회
            is_uri = isinstance(o, rdflib.URIRef)
            obj = str(o) if is_uri else o.value if isinstance(o, rdflib.Literal) else str(o)
            
            obj_label = processor.get_label(obj) if is_uri else obj
            pred_label = processor.get_label(pred) or (pred.split('/')[-1] if pred else 'unknown')
            
            print(f"[DEBUG] 라벨 정보: pred_label={pred_label}, obj_label={obj_label}, is_uri={is_uri}")
            
            relation = {
                'source': resource_uri,
                'source_label': processor.get_label(resource_uri) or resource_uri.split('/')[-1],
                'relation': pred,
                'relation_type': pred_label,
                'target': obj,
                'target_label': obj_label if is_uri else obj,
                'is_uri_target': is_uri
            }
            relations.append(relation)
            
            # 재귀적으로 관계 탐색 (URI인 경우에만)
            if is_uri and depth > 1:
                child_relations = self._build_relation_network(processor, obj, depth - 1, visited)
                relations.extend(child_relations)
        
        print(f"[DEBUG] 최종 관계 수: {len(relations)}")
        return relations
    
    def _analyze_keyword_search(self, request, processor):
        """키워드 검색 및 관련 리소스 분석"""
        keyword = request.data.get('keyword')
        
        if not keyword:
            return Response({
                'error': '검색 키워드(keyword)가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 라벨에 키워드가 포함된 리소스 검색
        query = f"""
        SELECT DISTINCT ?s ?label WHERE {{
            ?s <http://www.w3.org/2000/01/rdf-schema#label> ?label .
            FILTER(CONTAINS(LCASE(?label), "{keyword.lower()}"))
        }}
        """
        label_results = processor.execute_query(query)
        
        # 속성 값에 키워드가 포함된 리소스 검색
        query = f"""
        SELECT DISTINCT ?s ?p ?o WHERE {{
            ?s ?p ?o .
            FILTER(CONTAINS(LCASE(STR(?o)), "{keyword.lower()}"))
            FILTER(?p != <http://www.w3.org/2000/01/rdf-schema#label>)
            FILTER(ISURI(?s))
            FILTER(?p IS NOT NULL)
            FILTER(?o IS NOT NULL)
        }}
        """
        property_results = processor.execute_query(query)
        
        # 검색 결과 처리
        resources_by_label = []
        for result in label_results:
            resource_uri = result.get('s')
            label = result.get('label')
            
            # 리소스 유형 조회
            resource_type = self._get_resource_type(processor, resource_uri)
            
            resources_by_label.append({
                'uri': resource_uri,
                'label': label,
                'type': resource_type,
                'match_type': 'label'
            })
        
        resources_by_property = {}
        for result in property_results:
            resource_uri = result.get('s')
            pred = result.get('p')
            value = result.get('o')
            
            if resource_uri not in resources_by_property:
                # 리소스 라벨 조회
                label = processor.get_label(resource_uri)
                # 리소스 유형 조회
                resource_type = self._get_resource_type(processor, resource_uri)
                
                resources_by_property[resource_uri] = {
                    'uri': resource_uri,
                    'label': label,
                    'type': resource_type,
                    'match_type': 'property',
                    'matches': []
                }
            
            # 속성 라벨 조회
            pred_label = processor.get_label(pred) or (pred.split('/')[-1] if pred else 'unknown')
            
            resources_by_property[resource_uri]['matches'].append({
                'property': pred,
                'property_label': pred_label,
                'value': value
            })
        
        # 결과 병합 및 반환
        all_resources = list(resources_by_label)
        all_resources.extend(list(resources_by_property.values()))
        
        # 리소스 유형별 그룹화
        resource_groups = {}
        for resource in all_resources:
            # null 값 확인 및 처리
            if resource.get('uri') is None:
                continue
                
            res_type = resource.get('type', '기타')
            if res_type not in resource_groups:
                resource_groups[res_type] = []
            resource_groups[res_type].append(resource)
        
        return Response({
            'keyword': keyword,
            'total_results': len(all_resources),
            'label_matches': len(resources_by_label),
            'property_matches': len(resources_by_property),
            'resource_groups': resource_groups
        }, status=status.HTTP_200_OK)
    
    def _get_resource_type(self, processor, resource_uri):
        """리소스의 타입(클래스)을 조회합니다."""
        query = f"""
        SELECT ?type ?type_label WHERE {{
            <{resource_uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type .
            OPTIONAL {{ ?type <http://www.w3.org/2000/01/rdf-schema#label> ?type_label }}
        }}
        """
        results = processor.execute_query(query)
        
        if results:
            type_uri = results[0].get('type')
            type_label = results[0].get('type_label')
            
            if type_label:
                return type_label
            elif type_uri:
                return type_uri.split('/')[-1]
        
        return '기타'
    
    def _analyze_category_stats(self, request, processor):
        """카테고리(클래스)별 통계 분석"""
        category = request.data.get('category')
        
        if not category:
            # 모든 클래스의 통계 제공
            query = """
            SELECT ?type (COUNT(?s) as ?count) WHERE {
                ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type .
            }
            GROUP BY ?type
            ORDER BY DESC(?count)
            """
            results = processor.execute_query(query)
            
            category_stats = []
            for result in results:
                type_uri = result.get('type')
                count = result.get('count')
                
                # 타입 라벨 조회
                type_label = processor.get_label(type_uri) or type_uri.split('/')[-1]
                
                category_stats.append({
                    'uri': type_uri,
                    'label': type_label,
                    'count': count
                })
            
            return Response({
                'category_stats': category_stats,
                'total_categories': len(category_stats)
            }, status=status.HTTP_200_OK)
        else:
            # 특정 클래스의 통계 제공
            # 해당 클래스의 인스턴스 수 계산
            query = f"""
            SELECT (COUNT(?s) as ?count) WHERE {{
                ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{category}> .
            }}
            """
            count_results = processor.execute_query(query)
            instance_count = count_results[0].get('count', 0) if count_results else 0
            
            # 속성별 사용 빈도 계산
            query = f"""
            SELECT ?p (COUNT(?p) as ?count) WHERE {{
                ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{category}> .
                ?s ?p ?o .
                FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            }}
            GROUP BY ?p
            ORDER BY DESC(?count)
            """
            property_results = processor.execute_query(query)
            
            property_stats = []
            for result in property_results:
                prop_uri = result.get('p')
                count = result.get('count')
                
                # 속성 라벨 조회
                prop_label = processor.get_label(prop_uri) or prop_uri.split('/')[-1]
                
                property_stats.append({
                    'uri': prop_uri,
                    'label': prop_label,
                    'count': count
                })
            
            # 카테고리 라벨 조회
            category_label = processor.get_label(category) or category.split('/')[-1]
            
            return Response({
                'category_uri': category,
                'category_label': category_label,
                'instance_count': instance_count,
                'property_stats': property_stats
            }, status=status.HTTP_200_OK)
    
    def _analyze_resource_summary(self, request, processor):
        """리소스 정보를 요약하여 제공"""
        resource_uri = request.data.get('resource_uri')
        
        if not resource_uri:
            return Response({
                'error': 'resource_uri가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 리소스 기본 정보 조회
        resource_info = processor.get_resource_info(resource_uri)
        
        # 리소스 라벨 조회
        resource_label = processor.get_label(resource_uri) or resource_uri.split('/')[-1]
        
        # 리소스 타입 조회
        resource_type = self._get_resource_type(processor, resource_uri)
        
        # 중요 속성 분류 (예: 정의, 증상, 합병증 등)
        summary = {
            'uri': resource_uri,
            'label': resource_label,
            'type': resource_type,
            'definitions': [],
            'symptoms': [],
            'causes': [],
            'complications': [],
            'treatments': [],
            'related_resources': [],
            'other_properties': {}
        }
        
        # 속성 분류 진행
        for pred, values in resource_info.items():
            pred_label = processor.get_label(pred) or (pred.split('/')[-1] if pred else 'unknown')
            
            if values is None or len(values) == 0:
                continue
                
            # 속성에 따라 적절한 카테고리로 분류
            if 'definition' in pred.lower() or '정의' in pred_label:
                for value in values:
                    if value is not None:
                        summary['definitions'].append(value)
            elif 'symptom' in pred.lower() or '증상' in pred_label:
                for value in values:
                    if value is None:
                        continue
                    if isinstance(value, str) and value.startswith('http'):
                        # URI인 경우 라벨 조회
                        value_label = processor.get_label(value)
                        summary['symptoms'].append({
                            'uri': value,
                            'label': value_label
                        })
                    else:
                        summary['symptoms'].append(value)
            elif 'cause' in pred.lower() or '원인' in pred_label:
                for value in values:
                    if isinstance(value, str) and value.startswith('http'):
                        value_label = processor.get_label(value)
                        summary['causes'].append({
                            'uri': value,
                            'label': value_label
                        })
                    else:
                        summary['causes'].append(value)
            elif 'complication' in pred.lower() or '합병증' in pred_label:
                for value in values:
                    if isinstance(value, str) and value.startswith('http'):
                        value_label = processor.get_label(value)
                        summary['complications'].append({
                            'uri': value,
                            'label': value_label
                        })
                    else:
                        summary['complications'].append(value)
            elif 'treatment' in pred.lower() or '치료' in pred_label:
                for value in values:
                    if isinstance(value, str) and value.startswith('http'):
                        value_label = processor.get_label(value)
                        summary['treatments'].append({
                            'uri': value,
                            'label': value_label
                        })
                    else:
                        summary['treatments'].append(value)
            elif pred.endswith('label') or pred_label == 'label':
                # 이미 라벨 정보는 따로 처리했으므로 스킵
                continue
            elif isinstance(values[0], str) and values[0].startswith('http'):
                # URI인 경우 관련 리소스로 분류
                for value in values:
                    value_label = processor.get_label(value)
                    summary['related_resources'].append({
                        'property': pred,
                        'property_label': pred_label,
                        'uri': value,
                        'label': value_label
                    })
            else:
                # 그 외 속성은 기타 속성으로 분류
                summary['other_properties'][pred_label] = values
        
        # 요약 텍스트 생성
        summary_text = self._generate_summary_text(summary)
        
        # 결과 반환
        return Response({
            'resource_uri': resource_uri,
            'resource_label': resource_label,
            'resource_type': resource_type,
            'summary': summary,
            'summary_text': summary_text
        }, status=status.HTTP_200_OK)
    
    def _generate_summary_text(self, summary):
        """요약 정보를 바탕으로 자연어 요약 텍스트 생성"""
        label = summary.get('label', '')
        type_label = summary.get('type', '')
        
        text_parts = [f"{label}은(는) {type_label}입니다."]
        
        # 정의 추가
        if summary.get('definitions'):
            text_parts.append(f"정의: {summary['definitions'][0]}")
        
        # 증상 추가
        if summary.get('symptoms'):
            symptoms_text = []
            for symptom in summary['symptoms'][:5]:  # 최대 5개까지만 표시
                if isinstance(symptom, dict):
                    symptoms_text.append(symptom.get('label', ''))
                else:
                    symptoms_text.append(symptom)
            
            if symptoms_text:
                text_parts.append(f"주요 증상: {', '.join(symptoms_text)}")
        
        # 원인 추가
        if summary.get('causes'):
            causes_text = []
            for cause in summary['causes'][:3]:  # 최대 3개까지만 표시
                if isinstance(cause, dict):
                    causes_text.append(cause.get('label', ''))
                else:
                    causes_text.append(cause)
            
            if causes_text:
                text_parts.append(f"원인: {', '.join(causes_text)}")
        
        # 합병증 추가
        if summary.get('complications'):
            complications_text = []
            for complication in summary['complications'][:3]:
                if isinstance(complication, dict):
                    complications_text.append(complication.get('label', ''))
                else:
                    complications_text.append(complication)
            
            if complications_text:
                text_parts.append(f"관련 합병증: {', '.join(complications_text)}")
        
        # 치료법 추가
        if summary.get('treatments'):
            treatments_text = []
            for treatment in summary['treatments'][:3]:
                if isinstance(treatment, dict):
                    treatments_text.append(treatment.get('label', ''))
                else:
                    treatments_text.append(treatment)
            
            if treatments_text:
                text_parts.append(f"치료법: {', '.join(treatments_text)}")
        
        return " ".join(text_parts)
