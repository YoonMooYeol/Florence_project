import requests
from bs4 import BeautifulSoup
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class PregnancyCounselCrawler:
    def __init__(self):
        self.base_url = "https://www.childcare.go.kr"
        self.data_dir = Path('crawled_data')
        self.data_dir.mkdir(exist_ok=True)
        
        # Selenium 웹드라이버 초기화
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # 헤드리스 모드로 실행
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)

    def get_counsel_menu(self) -> Dict[str, Dict[str, List[int]]]:
        """임신 상담 메뉴 구조를 반환합니다."""
        return {
            '자주하는 질문': {
                '산부인과 질문': [472],
                '난임 질문': [473]
            }
        }

    def extract_qa_content(self, content: str) -> Optional[Dict[str, str]]:
        """Q&A 텍스트에서 질문과 답변을 분리합니다."""
        try:
            # Q., A. 또는 Q>, A> 형식 모두 처리
            if 'A.' in content:
                parts = content.split('A.')
                q_marker = 'Q.'
            elif 'A>' in content:
                parts = content.split('A>')
                q_marker = 'Q>'
            else:
                return None
            
            if len(parts) != 2:
                return None
            
            question = parts[0].replace(q_marker, '').strip()
            answer = parts[1].strip()
            
            return {
                'question': question,
                'answer': answer
            }
        except Exception as e:
            print(f"Error extracting Q&A: {str(e)}")
            return None

    def crawl_counsel_page(self, menu_no: int) -> List[Dict]:
        """상담 페이지의 Q&A 내용을 크롤링합니다."""
        url = f"{self.base_url}/?menuno={menu_no}"
        qa_list = []
        
        try:
            self.driver.get(url)
            time.sleep(2)
            
            page_num = 1
            while True:
                try:
                    # dataForm 내의 dl 요소가 로드될 때까지 대기
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#dataForm > dl')))
                    
                    # dl 요소 찾기
                    dl_element = self.driver.find_element(By.CSS_SELECTOR, '#dataForm > dl')
                    
                    # 모든 dt와 dd 요소 가져오기
                    elements = dl_element.find_elements(By.CSS_SELECTOR, 'dt, dd')
                    
                    # dt와 dd를 쌍으로 처리
                    for i in range(0, len(elements), 2):
                        try:
                            if i + 1 >= len(elements):
                                break
                            
                            dt = elements[i]
                            dd = elements[i + 1]
                            
                            # 질문 요약 가져오기
                            summary_text = dt.text.strip()
                            print(f"질문 요약: {summary_text}")
                            
                            # 질문 클릭하여 답변 표시
                            dt.click()
                            time.sleep(0.5)
                            
                            # 답변 내용 가져오기
                            spans = dd.find_elements(By.CSS_SELECTOR, 'span')
                            content = '\n'.join([span.text.strip() for span in spans if span.text.strip()])
                            print(f"내용 길이: {len(content)}")
                            
                            if content:
                                qa_dict = self.extract_qa_content(content)
                                if qa_dict:
                                    # 원하는 순서로 새로운 딕셔너리 생성
                                    ordered_qa_dict = {
                                        'summary': summary_text,
                                        'question': qa_dict['question'],
                                        'answer': qa_dict['answer']
                                    }
                                    qa_list.append(ordered_qa_dict)
                                    print(f"Q&A 추출 성공: {summary_text[:30]}...")
                                    print(f"내용 길이: {len(content)}")
                        
                        except Exception as e:
                            print(f"항목 처리 중 에러: {str(e)}")
                            continue
                    
                    # 다음 페이지로 이동
                    page_num += 1
                    next_page_selector = f"#contents > div > div > a:nth-child({page_num + 2})"
                    try:
                        next_page = self.driver.find_element(By.CSS_SELECTOR, next_page_selector)
                        if 'active' in next_page.get_attribute('class'):
                            print("마지막 페이지 도달")
                            break
                        next_page.click()
                        print(f"{page_num}페이지로 이동")
                        time.sleep(2)
                    except NoSuchElementException:
                        print("다음 페이지 없음")
                        break
                    
                except TimeoutException:
                    print("페이지 로딩 시간 초과")
                    break
            
            return qa_list
            
        except Exception as e:
            print(f"크롤링 중 에러 발생: {str(e)}")
            return []

    def save_data(self, data: dict, filename: str):
        """크롤링한 데이터를 JSON 파일로 저장합니다."""
        file_path = self.data_dir / f"{filename}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def crawl_all_counsel(self):
        """모든 상담 페이지를 크롤링합니다."""
        try:
            counsel_data = {}
            menu_structure = self.get_counsel_menu()

            for main_category, sub_categories in menu_structure.items():
                print(f"크롤링 중: {main_category}")
                main_category_data = {}
                
                for sub_category, menu_numbers in sub_categories.items():
                    print(f"  - {sub_category} 크롤링 중...")
                    sub_category_data = []
                    
                    for menu_no in menu_numbers:
                        qa_list = self.crawl_counsel_page(menu_no)
                        if qa_list:
                            sub_category_data.extend(qa_list)
                        time.sleep(1.5)
                    
                    main_category_data[sub_category] = sub_category_data
                    # 중간 데이터 저장
                    counsel_data[main_category] = main_category_data
                    self.save_data(counsel_data, '아이사랑_상담')
            
            print("크롤링 완료!")
            return counsel_data
        finally:
            self.driver.quit()  # 브라우저 종료

def main():
    crawler = PregnancyCounselCrawler()
    crawler.crawl_all_counsel()

if __name__ == "__main__":
    main()