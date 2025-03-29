# 🌙 누리달: AI 기반 산전 관리 시스템 

![누리달](https://postfiles.pstatic.net/MjAyNTAzMjlfMTcw/MDAxNzQzMjIyMjUyNzg5.5wjLzGK03CsYpPl3XCMqmZvGJ0jSMo3bsRzNdwoHErAg.LqYbKBRG9KmA6b9k8qcpdPrAybgqNs-zlrZi2oJS5Igg.GIF/%EB%88%84%EB%88%84%EB%A6%AC%EB%A6%AC%EB%8B%AC%EB%8B%AC.gif?type=w3840)

[➡️ 누리달 홈페이지 바로가기](https://www.nooridal.com/)





## 


## 프로젝트 개요

>대한민국의 일부 지역, 특히 **서울 이외의 소도시에서는 산부인과 의료 접근성이 낮아** 임산부들이 적절한 산전 및 산후 관리를 받기 어려운 현실입니다.  
또한, **미성년 임산부들은 사회적 편견과 경제적 어려움**으로 인해 필요한 의료 지원과 상담을 충분히 받지 못하고 있습니다.

>누리달은 이러한 문제를 해결하고자 **AI 기반 산전 관리 시스템**을 개발하여,  
**의료 정보 제공, 맞춤 건강 관리, 정부 지원 정책 안내**를 통해 **임산부와 신생아의 건강을 증진**하는 것을 목표로 합니다.    



## 주요 목표

>1. **의료 접근성 향상**
> - AI 에이전트를 활용한 **철저하게 검증된 맞춤형 의료 정보 제공**
> - 신뢰할 수 있는 건강 관리 정보로 **임산부의 모성 건강 증진**

>2.  **정부 지원 정책 제공**
>
>- **임산부를 위한 지원 정책**을 쉽고 간편하게 검색
>   - 거주 지역 기반으로 **맞춤형 정책 정보 추천**

>3. **개인 맞춤 건강 관리**
>- **AI 분석을 통한 임산부 개개인의 건강 상태 관리**
>- 정기적인 건강 체크 및 **맞춤형 케어 솔루션 제공**



## 기대 효과

>"누리달은 단순한 AI 기반 시스템이 아닌, **대한민국에서 태어나는 소중한 생명을 지키는 데 기여하는 서비스**가 되고자 합니다."


>- **의료 정보 접근성 개선**으로 임산부의 건강 증진
>- **정부 지원 정보 제공**을 통한 실질적 지원 확대
>- **AI 맞춤 케어**로 모성 사망률 감소에 기여

<br>

## 🔗 기술 스택

- 웹 서버: Django + Gunicorn + Unicorn + Nginx
- 비동기 작업: Celery + Celery Beat
- 메시지 브로커: Redis
- 데이터베이스: PostgreSQL
- 배포: Docker, Docker Compose, AWS Elastic Beanstalk


---
## ⚙️ 로컬 개발 환경 설정

### 사전 요구사항

- Python 3.12 설치
- python3 -m venv .venv
- pip install -r requirements.txt

### 환경 변수 설정

- `.env.example` 파일의 내용을 `.env` 파일을 생성 후 복사
- `.env` 파일의 환경 변수 값을 수정

### 로컬 실행 방법

- python manage.py runserver
- 샐러리 추가
- 레디스 추가

---

