# # 아이사랑 웹사이트 크롤링

# import requests
# from bs4 import BeautifulSoup
# import time
# import json
# from pathlib import Path
# from typing import Dict, List

# class ChildcareCrawler:
#     def __init__(self):
#         self.base_url = "https://www.childcare.go.kr"
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }
#         # 크롤링한 데이터를 저장할 디렉토리 생성
#         self.data_dir = Path('crawled_data')
#         self.data_dir.mkdir(exist_ok=True)

#     def get_pregnancy_menu(self) -> Dict[str, Dict[str, List[int]]]:
#         """임신 탭의 하위 메뉴 구조와 URL 번호를 반환합니다."""
#         pregnancy_structure = {
#             '임신계획': {
#                 '임신준비': list(range(344, 353)),  # 344~352
#                 '임신하기': list(range(353, 357)),  # 353~356
#                 '임신확인': [357, 358]  # 357~358
#             },
#             '임신 중 잘지내기': ['임신초기(3~13주)', '임신중기(14~27주)', '임신후기(28~40주)'],
#             '고위험임신': ['고위험 임신이란', '정부지정 난임 시술기관'],
#             '유산': ['유산이란', '자연유산', '유산 후 관리'],
#             '난임': ['난임이란', '난임 검사', '대표적 난임치료'],
#             '임신 상담': [],
#             '근로자 지원제도': [],
#             '임산부 신고': []
#         }
#         return pregnancy_structure

#     def crawl_page(self, menu_no: int) -> dict:
#         """페이지의 내용을 크롤링합니다."""
#         url = f"{self.base_url}/?menuno={menu_no}"
#         try:
#             response = requests.get(url, headers=self.headers)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, 'html.parser')
            
#             # 페이지 제목 추출
#             title = soup.find('h3')
#             title_text = title.get_text(strip=True) if title else None
            
#             # 본문 내용 추출
#             content = soup.find('div', class_='contents')
#             content_text = content.get_text(strip=True) if content else None
            
#             return {
#                 'title': title_text,
#                 'content': content_text,
#                 'url': url
#             }
#         except Exception as e:
#             print(f"Error crawling menuno={menu_no}: {str(e)}")
#             return None

#     def save_data(self, data: dict, filename: str):
#         """크롤링한 데이터를 JSON 파일로 저장합니다."""
#         file_path = self.data_dir / f"{filename}.json"
#         with open(file_path, 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=2)

#     def crawl_pregnancy_content(self):
#         """임신 관련 모든 페이지를 크롤링합니다."""
#         pregnancy_data = {}
#         menu_structure = self.get_pregnancy_menu()

#         for main_category, sub_categories in menu_structure.items():
#             print(f"크롤링 중: {main_category}")
#             main_category_data = {}
            
#             for sub_category, menu_numbers in sub_categories.items():
#                 print(f"  - {sub_category} 크롤링 중...")
#                 sub_category_data = []
                
#                 for menu_no in menu_numbers:
#                     content = self.crawl_page(menu_no)
#                     if content:
#                         sub_category_data.append(content)
#                     # 서버 부하 방지를 위한 딜레이
#                     time.sleep(1)
                
#                 main_category_data[sub_category] = sub_category_data
            
#             pregnancy_data[main_category] = main_category_data
#             # 중간 데이터 저장
#             self.save_data(pregnancy_data, 'pregnancy_content')
        
#         # 데이터 저장
#         self.save_data(pregnancy_data, 'pregnancy_content')
#         print("크롤링 완료!")
#         return pregnancy_data

# def main():
#     crawler = ChildcareCrawler()
#     crawler.crawl_pregnancy_content()

# if __name__ == "__main__":
#     main()