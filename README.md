# Smart Planner (SkyPlanner AI Agent)

SkyPlanner AI Agent - 날씨 및 일정 계획 도우미.

## 프로젝트 구조

- `app/api`: 백엔드 API (FastAPI)
- `app/ui`: 프론트엔드 UI (Streamlit)
- `infra`: 인프라 설정 (Docker Compose)

## 시작하기

### 필수 요구사항

- Python >= 3.11
- Docker
- Poetry (권장) 또는 pip

### 환경 설정

이 프로젝트는 여러 API 키가 필요합니다. 예제 환경 파일을 복사하여 키를 입력하세요:

```bash
cp .env.example .env
```

`.env` 파일을 열고 다음 항목을 설정하세요:

- **Anthropic API**: `ANTHROPIC_API_KEY`
- **Google Calendar API**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (OAuth 설정을 위한 `credentials.json` 및 `token.json` 필요)
- **OpenWeatherMap API**: `OPENWEATHERMAP_API_KEY`
- **Tavily Search API**: `TAVILY_API_KEY`
- **DynamoDB**: 기본적으로 로컬 설정이 제공됩니다.

### 인프라 (DynamoDB Local)

Docker Compose를 사용하여 DynamoDB Local을 실행합니다:

```bash
docker-compose -f infra/docker-compose.yml up -d
```

이 명령은 8000번 포트에서 DynamoDB Local을 시작합니다.

## 애플리케이션 실행

### 백엔드 API (Uvicorn)

FastAPI 백엔드 서버를 시작합니다:

```bash
uvicorn app.api.main:app --reload --port 8080
```

API는 `http://localhost:8080`에서 사용할 수 있습니다.
API 문서: `http://localhost:8080/docs`

### 프론트엔드 UI (Streamlit)

Streamlit 사용자 인터페이스를 시작합니다:

```bash
streamlit run app/ui/app.py
```

브라우저에서 UI에 접속할 수 있습니다 (`http://localhost:8501`).
