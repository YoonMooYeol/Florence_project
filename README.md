# 👶🏻 Florence Project _ 누리달

<br>

![누리달](static/nooridal_cover.gif "누리달")

[➡️ 누리달 홈페이지 바로가기](https://www.nooridal.com/)



# 💡목차

---

### 1. [프로젝트 소개](#프로젝트-소개)
### 2. [기술 스택](#기술-스택)
### 3. [설치 및 설정](#설치-및-설정)
### 4. [실행 방법](#실행-방법)
### 5. [프로젝트 구조](#프로젝트-구조)
### 6. [Process Flow](#process-flow)
### 7. [Service Architecture](#service-architecture)
### 8. [ERD (Entity Relationship Diagram)](#erd-entity-relationship-diagram)
### 9. [GitHub Link](#github-link)
### 10. [누리달만의 협업방식](#누리달만의-협업방식)
### 11. [문제 해결](#문제-해결)

<br>

## 💁🏻‍♀️ 프로젝트 소개

---

## 🌙 누리달: AI 기반 산전 관리 시스템


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

---

- 웹 서버: Django + Gunicorn + Nginx
- 비동기 작업: Celery + Celery Beat
- 메시지 브로커: Redis
- 데이터베이스: PostgreSQL
- 배포: Docker, Docker Compose, AWS Elastic Beanstalk


## ⚙️ 로컬 개발 환경 설정

---

### 사전 요구사항

- Docker 및 Docker Compose
- Python 3.12 이상 설치

### 환경 변수 설정

1. `.env.example` 파일을 `.env`로 복사
2. `.env` 파일의 환경 변수 값을 적절히 수정

### 로컬 실행 방법

```bash
# Docker Compose로 모든 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```


## 📂 프로젝트 구조

---

```
Florence_project/
├── backend/                  # 백엔드 디렉토리
│   ├── config/               # 프로젝트 설정
│   ├── api/                  # API 앱
│   ├── users/                # 사용자 관리 앱
│   ├── ai_services/          # AI 관련 서비스
│   └── manage.py             # Django 관리 스크립트
├── frontend/                 # 프론트엔드 디렉토리
│   ├── public/               # 정적 파일
│   ├── src/                  # Vue 소스 코드
│   │   ├── assets/           # 이미지, 폰트 등
│   │   ├── components/       # Vue 컴포넌트
│   │   ├── views/            # 페이지 컴포넌트
│   │   ├── router/           # Vue Router 설정
│   │   ├── store/            # Vuex/Pinia 상태 관리
│   │   ├── services/         # API 호출 서비스
│   │   ├── App.vue           # 루트 컴포넌트
│   │   └── main.js           # 진입점
│   └── package.json          # npm 설정
├── .env                      # 환경 변수
├── .gitignore                # Git 제외 파일
└── requirements.txt          # Python 의존성
```

## 🌊 Process Flow

---
### 1️⃣ 전체 플로우
![누리달](static/service_flow.png "process-flow")  

---

### 2️⃣ AI agent 플로우
![누리달](static/ai_agent_flow.png "process-flow")


## 🦾 Service Architecture

---
![누리달](static/service_architecture.png "service-architecture")  


## 💾 ERD (Entity Relationship Diagram)

---
![누리달](static/erd.png "ERD")  


## 🔗 GitHub Link

---
## [nooridal-FE](https://github.com/YoonMooYeol/Florence_project_FE.git)  
## [nooridal-BE](https://github.com/YoonMooYeol/Florence_project.git)  





## 👥 협업방식

--- 

> ### ✅ **프로토 타입 제작**
> 원하는 기능이 있다면 기능 추가 전 프로토타입을 제작하고, 튜터 및 팀원들과 사용성과 필요성을 검토한 후 도입 여부 결정하기
>### ✅ **빠르고 적극적인 피드백** 
>개발 진행 중 발생하는 문제나 아이디어에 대해 빠르게 공유하고, 즉각적인 피드백을 주고받아 개선점을 빠르게 반영하기
>### ✅ **정기적인 회의**
>회의 시간을 정해서 (아침, 저녁) 아침에는 할 일에 대해 논의하고 저녁에는 체크하는 시간 갖기
>### ✅ **원활한 일정 관리**
>각자 주요 역할과 업무를 정하고, 팀원들과 주간 혹은 격주 단위로 진행 상황을 점검하며 유연하게 일정 조정하며 업무 효율을 극대화 하기
>### ✅ **문서화 작업**
>SA문서를 하루 단위로 만들어서 버전 관리
>### ✅ **버전 관리 시스템 활용**
>Git을 활용해 각자 브랜치를 생성해 코드 버전을 관리하고, 협업 시 충돌을 방지하기

## 🫧 문제 해결

---
### 일반적인 문제

1. 데이터베이스 연결 오류 - 보안 그룹 및 네트워크 설정 확인
2. 정적 파일 접근 불가 - collectstatic 명령 실행 및 S3 버킷 권한 확인

### 지원 및 문의

문제가 발생할 경우 프로젝트 관리자에게 문의하세요.

<br>


