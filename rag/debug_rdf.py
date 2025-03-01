"""
RDF 데이터 처리를 디버깅하기 위한 스크립트
"""
import os
import sys
import django

# Django 설정 로드
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rag.method import RAGProcessor, RDFProcessor

def debug_rdf_processing():
    """RDF 데이터 처리 과정을 디버깅"""
    rdf_file_path = "data/rdf/wellness.rdf"
    
    print(f"=== RDF 파일 디버깅 시작: {rdf_file_path} ===")
    
    # RDF 파일이 존재하는지 확인
    if not os.path.exists(rdf_file_path):
        print(f"❌ RDF 파일이 존재하지 않습니다: {rdf_file_path}")
        return
    
    print(f"✅ RDF 파일 크기: {os.path.getsize(rdf_file_path)} 바이트")
    
    try:
        # RDF 프로세서 초기화
        processor = RDFProcessor(rdf_file_path, format="xml")
        
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
        
        print(f"\n=== SPARQL 쿼리 실행 중... ===")
        print(f"쿼리: {pregnancy_resources_query}")
        
        # 임신 관련 리소스 조회
        resource_results = processor.execute_query(pregnancy_resources_query)
        print(f"\n🔢 임신 관련 리소스 발견: {len(resource_results)}개")
        
        # 결과의 키 이름 확인
        if resource_results:
            print(f"\n=== 첫 번째 결과의 키 이름 확인 ===")
            first_result = resource_results[0]
            print(f"키 목록: {list(first_result.keys())}")
            print(f"첫 번째 결과: {first_result}")
        
        # 리소스 URI 추출 (키 이름에 따라 조정)
        if resource_results and 's' in first_result:
            resource_uris = [result["s"] for result in resource_results]
            resource_key = "s"
        elif resource_results and 'resource' in first_result:
            resource_uris = [result["resource"] for result in resource_results]
            resource_key = "resource"
        else:
            print("⚠️ 리소스 URI를 포함하는 키를 찾을 수 없습니다")
            if resource_results:
                resource_uris = []
                resource_key = None
                for result in resource_results:
                    for key, value in result.items():
                        if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
                            resource_uris.append(value)
                            if not resource_key:
                                resource_key = key
                print(f"URI로 보이는 값을 가진 키 찾음: {resource_key}")
                print(f"발견된 URI 수: {len(resource_uris)}")
            else:
                resource_uris = []
                resource_key = None
        
        # 샘플 리소스 출력
        print(f"\n=== 샘플 리소스 URI (최대 5개) ===")
        for i, uri in enumerate(resource_uris[:5]):
            print(f"{i+1}. {uri}")
        
        # 첫 번째 리소스에 대한 정보 출력
        if resource_uris:
            first_uri = resource_uris[0]
            print(f"\n=== 첫 번째 리소스 정보: {first_uri} ===")
            
            # 리소스 정보 가져오기
            resource_info = processor.get_resource_info(first_uri)
            
            # 리소스 레이블 가져오기
            if resource_key and resource_results:
                label_key = "label" if "label" in resource_results[0] else None
                label = None
                if label_key:
                    result_with_uri = next((result for result in resource_results if result.get(resource_key) == first_uri), None)
                    if result_with_uri:
                        label = result_with_uri.get(label_key)
                
                if label is None:
                    label = processor.get_label(first_uri)
            else:
                label = processor.get_label(first_uri)
            
            print(f"레이블: {label or '없음'}")
            print(f"속성 수: {len(resource_info)}")
            
            # 속성 정보 출력
            for prop_key, values in resource_info.items():
                values_str = ", ".join(str(v) for v in values)
                print(f"  - {prop_key}: {values_str}")
            
            # 텍스트 생성 테스트
            print(f"\n=== 텍스트 생성 테스트 ===")
            
            # 중요 속성 목록 사용
            important_props = RAGProcessor.IMPORTANT_PROPERTIES
            
            # 중요 속성 관련 메타데이터 추출
            important_attrs = {}
            
            # 텍스트 생성
            text_parts = [f"주제: {label or first_uri}"]
            
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
            
            print(f"생성된 텍스트 (길이: {len(text)}자):")
            print(text)
            
            # 텍스트 길이 확인
            if len(text) < 50:
                print(f"⚠️ 텍스트가 너무 짧습니다 ({len(text)}자)")
        
        # 모든 리소스 처리 시도
        print(f"\n=== 모든 리소스 처리 시도 ===")
        
        texts = []
        metadatas = []
        ids = []
        
        processed_resources = 0
        total_text_parts = 0
        
        for i, uri in enumerate(resource_uris):
            try:
                # 리소스 정보 가져오기
                resource_info = processor.get_resource_info(uri)
                
                # 리소스에 속성이 없는 경우 건너뛰기
                if not resource_info:
                    print(f"⚠️ 리소스에 속성이 없음: {uri}")
                    continue
                
                # 리소스 레이블 가져오기
                if resource_key and label_key and resource_results:
                    result_with_uri = next((result for result in resource_results if result.get(resource_key) == uri), None)
                    label = result_with_uri.get(label_key) if result_with_uri else None
                    if label is None:
                        label = processor.get_label(uri)
                else:
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
                
                # 최종 텍스트 생성
                text = "\n".join(text_parts)
                
                # 텍스트 길이 확인
                if len(text) < 50:
                    print(f"⚠️ 텍스트가 너무 짧음 ({len(text)}자): {uri}")
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
                
                # 진행 상황 표시
                if (i + 1) % 10 == 0 or i == len(resource_uris) - 1:
                    print(f"진행 상황: {i + 1}/{len(resource_uris)} ({processed_resources}개 처리됨)")
            
            except Exception as e:
                print(f"❌ 리소스 처리 중 오류 발생: {uri} - {str(e)}")
                continue
        
        # 결과 요약
        print(f"\n=== 처리 결과 요약 ===")
        print(f"총 리소스 수: {len(resource_uris)}개")
        print(f"처리된 리소스 수: {processed_resources}개")
        print(f"생성된 텍스트 수: {len(texts)}개")
        
        if processed_resources > 0:
            print(f"평균 텍스트 부분 수: {total_text_parts / processed_resources:.2f}")
        
        if texts:
            print(f"평균 텍스트 길이: {sum(len(t) for t in texts) / len(texts):.2f}자")
        
        print(f"\n=== 디버깅 완료 ===")
        
    except Exception as e:
        print(f"❌ 디버깅 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_rdf_processing() 