import json
from pathlib import Path

def convert_counsel_to_markdown():
    # 파일 경로 설정
    data_dir = Path('crawled_data')
    json_file = data_dir / '아이사랑_상담.json'
    md_file = data_dir / '아이사랑_상담.md'
    
    # JSON 파일 읽기
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 마크다운으로 변환하여 저장
    with open(md_file, 'w', encoding='utf-8') as f:
        for main_category, sub_categories in data.items():
            # 메인 카테고리
            f.write(f"# {main_category}\n\n")
            
            for sub_category, qa_list in sub_categories.items():
                # 서브 카테고리
                f.write(f"## {sub_category}\n\n")
                
                for qa in qa_list:
                    # 질문 요약
                    f.write(f"### {qa['summary']}\n\n")
                    
                    # 질문 내용
                    f.write("#### 질문\n")
                    f.write(f"{qa['question']}\n\n")
                    
                    # 답변 내용
                    f.write("#### 답변\n")
                    f.write(f"{qa['answer']}\n\n")
                    
                    # 구분선
                    f.write("---\n\n")

def convert_info_to_markdown():
    """임신 정보 데이터를 마크다운으로 변환"""
    data_dir = Path('crawled_data')
    json_file = data_dir / '아이사랑_정보.json'
    md_file = data_dir / '아이사랑_정보.md'
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    with open(md_file, 'w', encoding='utf-8') as f:
        # 최상위 제목: 문서 전체 제목
        f.write("# 아이사랑 임신 정보\n\n")
        
        for main_category, sub_categories in data.items():
            # 메인 카테고리 (예: 임신계획)
            f.write(f"## {main_category}\n\n")
            
            for sub_category, articles in sub_categories.items():
                # 서브 카테고리 (예: 임신준비)
                f.write(f"### {sub_category}\n\n")
                
                for article in articles:
                    # 각 문서의 제목
                    f.write(f"#### {article['title']}\n\n")
                    
                    # 문서 내용의 헤더 레벨을 한 단계 더 깊게 조정
                    if article['content']:
                        # 기존 헤더를 한 단계 더 깊게 조정 (##-> #####, ###-> ######)
                        content = article['content'].replace('\n## ', '\n##### ').replace('\n### ', '\n###### ')
                        f.write(f"{content}\n\n")
                    
                    # 출처 정보
                    f.write(f"**출처:** {article['url']}\n\n")
                    
                    # 구분선
                    f.write("---\n\n")

def main():
    print("마크다운 변환을 시작합니다...")
    
    try:
        convert_counsel_to_markdown()
        print("상담 데이터 변환 완료")
    except Exception as e:
        print(f"상담 데이터 변환 중 오류 발생: {str(e)}")
    
    try:
        convert_info_to_markdown()
        print("임신 정보 데이터 변환 완료")
    except Exception as e:
        print(f"임신 정보 데이터 변환 중 오류 발생: {str(e)}")
    
    print("변환이 완료되었습니다.")

if __name__ == "__main__":
    main() 