# 아이사랑 웹사이트 크롤링

import requests
from bs4 import BeautifulSoup
import time
import json
from pathlib import Path
from typing import Dict, List

class ChildcareCrawler:
    def __init__(self):
        self.base_url = "https://www.childcare.go.kr"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 크롤링한 데이터를 저장할 디렉토리 생성
        self.data_dir = Path('crawled_data')
        self.data_dir.mkdir(exist_ok=True)

    def get_pregnancy_menu(self) -> Dict[str, Dict[str, List[int]]]:
        """임신 탭의 하위 메뉴 구조와 URL 번호를 반환합니다."""
        pregnancy_structure = {
            '임신계획': {
                '임신준비': list(range(344, 353)),  # 344~352
                '임신하기': list(range(353, 357)),  # 353~356
                '임신확인': [357, 358]  # 357~358
            },
            '임신 중 잘지내기': {
                '임신초기(3~13주)': [359, 361, 363, 364, 365, 366],
                '임신중기(14~27주)': list(range(367, 373)),
                '임신후기(28~40주)': list(range(373, 379))
            },
            '고위험임신': {
                '고위험 임신이란': [11]
            },
            '유산': {
                '유산이란': [122],
                '자연유산': [260],
                '유산 후 관리': [261]
            },
            '난임': {
                '난임이란': [262],
                '난임 검사': [263],
                '대표적 난임치료': [264]
            },
            # 추후 크롤링 필요
            # '임신 상담': {
            #  '자주하는 질문': [472, 473]
            #  }
        }
        return pregnancy_structure

    def crawl_page(self, menu_no: int) -> dict:
        """페이지의 내용을 크롤링합니다."""
        url = f"{self.base_url}/?menuno={menu_no}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 페이지 제목 추출 (탭 메뉴의 현재 선택된 항목)
            title = soup.select_one('#contents > ul.tab > li.on > a')
            title_text = title.get_text(strip=True) if title else None
            
            # 본문 내용 추출
            content_elements = []
            
            # 1. 일반 콘텐츠 영역 처리
            content_area = soup.select('#contents > *:not(ul.tab)')
            
            for element in content_area:
                if element.name in ['h4', 'h5', 'p'] or (element.name == 'ul' and 'tab' not in element.get('class', [])):
                    if element.name == 'ul':
                        # ul 내의 li 태그들을 처리
                        for li in element.find_all('li'):
                            text = li.get_text(strip=True)
                            if text:
                                content_elements.append(f"- {text}")
                    else:
                        text = element.get_text(strip=True)
                        if text:  # 빈 텍스트가 아닌 경우만 포함
                            if element.name == 'h4':
                                content_elements.append(f"\n## {text}\n")
                            elif element.name == 'h5':
                                content_elements.append(f"\n### {text}\n")
                            else:
                                content_elements.append(text)
            
            # 2. 내부 탭(tab_con_inner) 콘텐츠 처리
            for tab_num in range(1, 10):  # 충분히 큰 범위로 탭 검색
                tab_content = soup.select(f'#b_tab-{tab_num} > *')
                if not tab_content:  # 해당 탭이 없으면 중단
                    break
                
                # 탭 제목 찾기
                tab_title = soup.select_one(f'#contents .tab_con_inner > ul > li:nth-child({tab_num}) > a')
                if tab_title:
                    content_elements.append(f"\n## {tab_title.get_text(strip=True)}\n")
                
                for element in tab_content:
                    if element.name in ['h4', 'h5', 'p', 'ul']:
                        if element.name == 'ul':
                            for li in element.find_all('li'):
                                text = li.get_text(strip=True)
                                if text:
                                    content_elements.append(f"- {text}")
                        else:
                            text = element.get_text(strip=True)
                            if text:
                                if element.name == 'h4':
                                    content_elements.append(f"\n## {text}\n")
                                elif element.name == 'h5':
                                    content_elements.append(f"\n### {text}\n")
                                else:
                                    content_elements.append(text)
            
            # 수집된 내용을 하나의 문자열로 결합
            content_text = '\n'.join(content_elements) if content_elements else None
            
            return {
                'title': title_text or self.current_sub_category,  # title이 없으면 sub_category 사용
                'content': content_text,
                'url': url
            }
        except Exception as e:
            print(f"Error crawling menuno={menu_no}: {str(e)}")
            return None

    def save_data(self, data: dict, filename: str):
        """크롤링한 데이터를 JSON 파일로 저장합니다."""
        file_path = self.data_dir / f"{filename}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def crawl_pregnancy_content(self):
        """임신 관련 모든 페이지를 크롤링합니다."""
        pregnancy_data = {}
        menu_structure = self.get_pregnancy_menu()

        for main_category, sub_categories in menu_structure.items():
            print(f"크롤링 중: {main_category}")
            main_category_data = {}
            
            for sub_category, menu_numbers in sub_categories.items():
                print(f"  - {sub_category} 크롤링 중...")
                sub_category_data = []
                
                # sub_category를 현재 크롤링 중인 하위 카테고리로 설정
                self.current_sub_category = sub_category
                
                for menu_no in menu_numbers:
                    content = self.crawl_page(menu_no)
                    if content:
                        sub_category_data.append(content)
                    time.sleep(1.5)
                
                main_category_data[sub_category] = sub_category_data
                # 중간 데이터 저장
                self.save_data(pregnancy_data, 'pregnancy_content')
            
            pregnancy_data[main_category] = main_category_data
        
        # 최종 데이터 저장
        self.save_data(pregnancy_data, 'pregnancy_content')
        print("크롤링 완료!")
        return pregnancy_data

def main():
    crawler = ChildcareCrawler()
    crawler.crawl_pregnancy_content()

if __name__ == "__main__":
    main()