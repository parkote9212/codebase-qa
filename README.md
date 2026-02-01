# Codebase Q&A

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.5-green?style=flat-square&logo=vue.js" alt="Vue">
  <img src="https://img.shields.io/badge/FastAPI-0.109-teal?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/ChromaDB-0.4-orange?style=flat-square" alt="ChromaDB">
</p>

코드베이스에 대해 질문하고 AI가 답변하는 **RAG 기반 Q&A 시스템**

로컬 LLM(Ollama)과 벡터 데이터베이스(ChromaDB)를 활용하여 개인 코드베이스를 분석하고 자연어로 질문에 답변합니다.

---

## 웹 LLM / MCP 대비 왜 쓰나요?

| 구분 | 웹 LLM | MCP (요청마다 읽기) | **Codebase Q&A** |
|------|--------|---------------------|-------------------|
| **로컬 파일 접근** | 브라우저 제한으로 읽기 어렵거나 불가 | 가능 | ✅ 로컬 경로 지정 후 인덱싱 |
| **토큰 소비** | 질문마다 컨텍스트 전송 | **요청할 때마다 파일을 읽어** 토큰 소비 큼 | ✅ **한 번 마운트·임베딩 후 유지** → 질의 시 검색만 하므로 토큰 절약 |
| **상태 유지** | 세션/컨텍스트 제한 | 매 요청마다 리소스 로드 | ✅ **인덱스·임베딩을 디스크에 유지** (ChromaDB), 재시작해도 유지 |

- **마운트/임베딩 상태 유지**: 프로젝트를 한 번 인덱싱하면 ChromaDB에 벡터로 저장됩니다. 이후 질문할 때마다 파일을 다시 읽지 않고, 검색된 청크만 LLM에 넘기므로 **토큰 사용이 적고 응답이 안정적**입니다.
- **프로젝트 단위로 읽기**: 파일을 일일이 올리는 게 아니라 **프로젝트 폴더 경로만 지정**하면 해당 디렉터리를 스캔·파싱해 한 번에 인덱싱합니다. 여러 프로젝트를 등록해 두고 필요할 때마다 질의할 수 있습니다.
- **로컬 우선**: Ollama + 로컬 ChromaDB로 코드가 외부로 나가지 않고, 로컬 파일 시스템을 그대로 경로로 지정해 쓸 수 있습니다.

> **더 강력한 성능을 원하시면 API를 교체하세요.** 기본은 로컬 Ollama입니다. 백엔드의 LLM 호출부(`services/llm.py`, `rag_chain.py`)를 OpenAI, Anthropic, Gemini 등 다른 API로 바꾸면 더 큰 모델로 동일한 RAG 파이프라인을 사용할 수 있습니다.

## 스크린샷

```
┌─────────────────────────────────────────────────────────────┐
│  Codebase Q&A          │  ● Ollama connected (qwen2.5:3b)  │
├─────────────────────────────────────────────────────────────┤
│  PROJECTS              │                                    │
│  ✓ BizSync   450 chunks│  User: JWT 인증 어떻게 구현했어?   │
│  ✓ fitneeds  230 chunks│                                    │
│  ○ side-proj           │  Assistant:                        │
│                        │  JWT 인증은 `JwtTokenProvider`     │
│  [+ Add Project]       │  클래스에서 처리합니다...          │
│                        │                                    │
│  [Clear Chat]          │  ┌──────────────────────────┐      │
│                        │  │ java                Copy │      │
│                        │  │ @Component              │      │
│                        │  │ public class JwtToken...│      │
│                        │  └──────────────────────────┘      │
│                        │                                    │
│                        │  📎 Sources (2) ▼                  │
├─────────────────────────────────────────────────────────────┤
│  [코드에 대해 질문하세요...                        ] [전송] │
└─────────────────────────────────────────────────────────────┘
```

## 주요 기능

### 인덱싱·질의
- 🔍 **코드 인덱싱**: Java, Python, Vue, JavaScript 파일 자동 파싱 → **한 번 인덱싱 후 ChromaDB에 유지**
- 🤖 **RAG 질의**: 벡터 검색 + LLM으로 코드 기반 답변 생성 (요청마다 파일 재읽기 없음)
- 📊 **진행률 표시**: 인덱싱 진행 상태 실시간 확인

### 채팅·내보내기
- 📥 **글 내려받기**: 대화 전체를 **마크다운(.md) 파일로 다운로드** 또는 **클립보드에 복사**
- 💬 **채팅 세션 나누기**: 세션 여러 개 생성·전환·이름 변경·삭제 (주제별로 대화 분리)

### UI·기타
- 🌙 **다크/라이트 모드**: Pinia로 테마 유지 (localStorage)
- 📋 **복사 기능**: 코드 블록 및 메시지 원클릭 복사
- 💾 **로그 저장**: 질문/답변 자동 기록 (`data/query_logs.jsonl`)

## 기술 스택

### Backend
- **FastAPI** - 고성능 Python 웹 프레임워크
- **ChromaDB** - 벡터 데이터베이스
- **sentence-transformers** - 텍스트 임베딩 (all-MiniLM-L6-v2)
- **Ollama** - 로컬 LLM 서버 (qwen2.5:3b)
- **pydantic-settings** - 설정/환경 변수

### Frontend
- **Vue 3** - Composition API + script setup
- **Pinia** - 상태 관리 (채팅·세션·테마)
- **Tailwind CSS v4** - 유틸리티 기반 스타일링 (@tailwindcss/postcss)
- **highlight.js** - 코드 신택스 하이라이팅
- **Vite** - 빌드 도구

## 프로젝트 구조

```
codebase-qa/
├── backend/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── config.py            # 설정 (pydantic-settings)
│   ├── schemas.py           # Pydantic 스키마
│   ├── services/
│   │   ├── embedder.py      # 임베딩 서비스
│   │   ├── retriever.py     # 벡터 검색
│   │   ├── llm.py           # Ollama 클라이언트
│   │   └── rag_chain.py     # RAG 파이프라인
│   └── utils/
│       └── code_parser.py   # 코드 파싱/청킹
├── frontend/
│   ├── src/
│   │   ├── api/             # API 서비스 (index.js)
│   │   ├── components/      # ChatInput, ChatMessage, CodeBlock, Sidebar, SessionPanel 등
│   │   ├── stores/          # Pinia (chat, theme)
│   │   └── views/           # ChatView
│   ├── postcss.config.mjs   # Tailwind v4 PostCSS
│   └── package.json
├── data/
│   ├── chroma_db/           # 벡터 저장소 (인덱싱 결과)
│   └── query_logs.jsonl     # 질문/답변 로그
└── README.md
```

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.ai/) 설치

### 1. Ollama 설정

```bash
# Ollama 서버 시작
ollama serve

# 모델 다운로드 (다른 터미널에서)
ollama pull qwen2.5:3b
```

### 2. 백엔드 실행

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

> Python 3.12 권장 (3.14는 ChromaDB/onnxruntime 미지원). 가상환경 사용 권장.

### 3. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

### 4. 브라우저 접속

http://localhost:5173

## 사용 방법

### 1. 프로젝트 인덱싱

1. 사이드바 하단 **"+ Add Project"** 클릭
2. 코드 경로 입력 (기본 예: `/Users/gcpark/code/프로젝트명`). **프로젝트명**은 선택 사항(미입력 시 폴더명 사용)
3. **"인덱싱 시작"** 클릭
4. 진행률 확인 (파일 스캔 → 임베딩 → 저장). 중간에 **인덱싱 취소** 가능

### 2. 질문하기

```
예시 질문:
- "JWT 인증 로직 설명해줘"
- "Redis 캐싱은 어디서 사용해?"
- "WebSocket 연결 코드 보여줘"
- "User 엔티티 구조 설명해줘"
```

### 3. 답변 활용

- **Sources**: 참조된 소스 코드 파일 확인
- **복사**: 메시지나 코드 블록 복사
- **Clear Chat**: 현재 세션 대화만 초기화

### 4. 글 내려받기

- 헤더 **내보내기(▼)** 메뉴에서:
  - **클립보드에 복사**: 현재 대화 전체를 마크다운으로 복사
  - **마크다운 다운로드**: `.md` 파일로 저장 (`conversation_YYYY-MM-DD.md`)

### 5. 채팅 세션 나누기

- 오른쪽 **채팅 세션** 패널에서:
  - **새 대화**: 새 세션 생성
  - 세션 클릭: 해당 세션으로 전환
  - 이름 클릭 후 수정: 세션 이름 변경
  - 휴지통: 세션 삭제 (메시지는 해당 세션만 삭제)

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/health` | 헬스체크 |
| GET | `/api/status` | 시스템 상태 |
| GET | `/api/browse` | 디렉토리 목록 조회 (path 쿼리) |
| POST | `/api/index` | 코드 인덱싱 (code_path, project_name 선택, force) |
| GET | `/api/index/progress` | 인덱싱 진행률 |
| POST | `/api/index/cancel` | 인덱싱 취소 |
| DELETE | `/api/index/{project_name}` | 인덱스 삭제 |
| POST | `/api/query` | RAG 질의 |
| POST | `/api/query/stream` | 스트리밍 질의 |
| GET | `/api/models` | 모델 목록 |
| POST | `/api/models/switch` | 모델 변경 |

## 지원 언어

| 언어 | 확장자 | 청킹 단위 |
|------|--------|----------|
| Python | `.py` | 함수, 클래스 (AST) |
| Java | `.java` | 클래스, 인터페이스 |
| Vue | `.vue` | script, template |
| JavaScript | `.js` | 함수, 클래스 |

## 설정

### 환경 변수 (backend `.env`)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | `qwen2.5:3b` | 기본 LLM 모델 |
| `CODE_BASE_PATH` | `/Volumes/DEV_DATA/code` | 코드베이스 기본 경로 |
| `ALLOWED_BROWSE_PATHS` | (설정 참고) | 브라우저에서 허용할 경로 (쉼표 구분) |
| `CORS_ORIGINS` | `http://localhost:5173` | CORS 허용 오리진 |

### 모델 변경

다른 Ollama 모델 사용:

```bash
# 모델 다운로드
ollama pull llama3.2:3b

# API로 변경
curl -X POST http://localhost:8000/api/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:3b"}'
```

## 개발

### 백엔드 테스트

```bash
cd backend

# 인덱싱 + RAG 테스트
python test_rag.py --index

# 검색만 테스트
python test_rag.py --search
```

### 코드 스타일

- **Backend**: Python (타입 힌트, 한글 주석)
- **Frontend**: Vue 3 Composition API + script setup
- **API**: snake_case 응답

## 라이선스

MIT License

## 참고

- [FastAPI 문서](https://fastapi.tiangolo.com/)
- [Vue 3 문서](https://vuejs.org/)
- [ChromaDB 문서](https://docs.trychroma.com/)
- [Ollama 문서](https://ollama.ai/)
