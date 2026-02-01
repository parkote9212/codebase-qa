# Codebase Q&A

<p align="center">
  <strong>로컬 LLM 기반 코드베이스 질의응답 시스템</strong><br>
  RAG(Retrieval-Augmented Generation) 파이프라인으로 개인 프로젝트를 분석하고 자연어로 질문에 답변합니다.
</p>

---

## 📌 주요 특징

### 💡 왜 Codebase Q&A인가?

| 비교 항목 | 웹 LLM | MCP | **Codebase Q&A** |
|---------|--------|-----|------------------|
| **로컬 파일 접근** | 브라우저 제한 | 가능 | ✅ **로컬 경로 직접 인덱싱** |
| **토큰 효율성** | 매번 전체 전송 | 매 요청마다 파일 읽기 | ✅ **한 번 임베딩 후 검색만** |
| **상태 지속성** | 세션 제한 | 매 요청마다 리소드 | ✅ **ChromaDB 영구 저장** |
| **프라이버시** | 외부 API 전송 | 서버 의존 | ✅ **완전 로컬 처리** |
| **비용** | API 사용료 | API 사용료 | ✅ **무료 (Ollama 사용)** |

### 🎯 핵심 장점

- **📦 영구 인덱싱**: ChromaDB에 벡터 저장 → 재시작해도 유지
- **🔍 똑똑한 검색**: 질문과 유사한 코드 청크만 LLM에 전달
- **💰 토큰 절약**: 전체 파일 재전송 없이 관련 코드만 검색
- **🏠 완전 로컬**: Ollama + ChromaDB로 코드 외부 유출 없음
- **🔌 API 교체 가능**: OpenAI/Anthropic/Gemini로 LLM 변경 가능

---

## 🚀 빠른 시작

### 사전 요구사항

- **Python 3.11+** (3.12 권장, 3.14는 미지원)
- **Node.js 18+**
- **[Ollama](https://ollama.ai/)** 설치

### 1️⃣ Ollama 설정

```bash
# Ollama 서버 시작
ollama serve

# 모델 다운로드 (다른 터미널에서)
ollama pull qwen2.5:3b
```

<details>
<summary>💡 다른 모델 사용하기</summary>

```bash
# 더 강력한 모델 (메모리 8GB 이상 권장)
ollama pull llama3.2:3b
ollama pull mistral:7b

# 경량 모델 (메모리 4GB 이하)
ollama pull phi3:mini
```
</details>

### 2️⃣ 백엔드 실행

```bash
cd backend

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload --port 8000
```

<details>
<summary>⚙️ 환경 변수 설정 (선택사항)</summary>

`.env` 파일을 `backend/` 디렉토리에 생성:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
CODE_BASE_PATH=/Users/gcpark/code
ALLOWED_BROWSE_PATHS=/Users/gcpark/code,/Volumes/DEV_DATA/code
CORS_ORIGINS=http://localhost:5173
```
</details>

### 3️⃣ 프론트엔드 실행

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 4️⃣ 브라우저 접속

🌐 **http://localhost:5173**

---

## 🎬 사용 방법

### 1. 프로젝트 인덱싱

```
📁 사이드바 → [+ Add Project] 클릭
📝 프로젝트 경로 입력: /Users/gcpark/code/my-project
▶️  인덱싱 시작
⏳ 진행률: 파일 스캔 → 임베딩 → 저장
✅ 완료!
```

> **💡 Tip**: 프로젝트명을 지정하지 않으면 폴더명을 자동으로 사용합니다.

### 2. 질문하기

**예시 질문들:**

```
💬 "JWT 인증 로직 어떻게 구현했어?"
💬 "Redis 캐싱은 어디서 사용해?"
💬 "WebSocket 연결 코드 보여줘"
💬 "User 엔티티 구조 설명해줘"
💬 "비관적 락은 왜 사용했어?"
```

### 3. 답변 활용

- **📎 Sources**: 참조된 코드 파일 확인
- **📋 복사**: 메시지/코드 블록 클립보드 복사
- **🗑️ Clear Chat**: 현재 대화만 초기화

### 4. 대화 관리

**📥 내보내기 (헤더 메뉴)**
- 📄 클립보드에 복사 (Markdown)
- 💾 파일 다운로드 (`conversation_YYYY-MM-DD.md`)

**💬 세션 관리 (우측 패널)**
- ➕ 새 대화 생성
- 🔄 세션 전환
- ✏️ 이름 변경
- 🗑️ 세션 삭제

---

## 🏗️ 아키텍처

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ ChatView     │  │ Sidebar      │  │ SessionPanel │  │
│  │ (Pinia Store)│  │ (Projects)   │  │ (Sessions)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                       API (REST + SSE)
                            │
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Code Parser  │→│ Embedder     │→│ ChromaDB     │  │
│  │ (AST)        │  │ (MiniLM-L6)  │  │ (Vectors)    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                           ↓                              │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │ Retriever    │→│ RAG Chain    │→ Ollama (qwen2.5)  │
│  │ (Search)     │  │ (Prompt)     │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### RAG 파이프라인

```
1. 📁 Index Phase (한 번만)
   Code Files → AST Parser → Chunks → Embedder → ChromaDB

2. 🔍 Query Phase (매번)
   Question → Embedder → Vector Search → Top-K Chunks
                                              ↓
   Question + Chunks → LLM Prompt → Ollama → Answer
```

### 프로젝트 구조

```
codebase-qa/
├── backend/
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── config.py               # 환경 설정 (Pydantic)
│   ├── schemas.py              # API 스키마 정의
│   ├── services/
│   │   ├── embedder.py         # 텍스트 임베딩 (sentence-transformers)
│   │   ├── retriever.py        # 벡터 검색 (ChromaDB)
│   │   ├── llm.py              # Ollama 클라이언트
│   │   └── rag_chain.py        # RAG 파이프라인 오케스트레이션
│   └── utils/
│       └── code_parser.py      # 코드 파싱 및 청킹 (AST)
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios API 서비스
│   │   ├── components/         # Vue 컴포넌트
│   │   │   ├── ChatInput.vue
│   │   │   ├── ChatMessage.vue
│   │   │   ├── CodeBlock.vue
│   │   │   ├── Sidebar.vue
│   │   │   └── SessionPanel.vue
│   │   ├── stores/             # Pinia 스토어
│   │   │   ├── chat.js         # 채팅 상태 관리
│   │   │   └── theme.js        # 테마 상태 관리
│   │   └── views/
│   │       └── ChatView.vue    # 메인 뷰
│   ├── postcss.config.mjs      # Tailwind v4 설정
│   └── package.json
├── data/
│   ├── chroma_db/              # 벡터 DB (영구 저장)
│   └── query_logs.jsonl        # 질문/답변 로그
└── README.md
```

---

## 🛠️ 기술 스택

### Backend

| 기술 | 용도 | 버전 |
|-----|------|-----|
| **FastAPI** | RESTful API 프레임워크 | 0.109+ |
| **ChromaDB** | 벡터 데이터베이스 | 0.4+ |
| **sentence-transformers** | 텍스트 임베딩 | latest |
| **Ollama** | 로컬 LLM 서버 | latest |
| **pydantic-settings** | 설정 관리 | 2.0+ |
| **sse-starlette** | Server-Sent Events | latest |

### Frontend

| 기술 | 용도 | 버전 |
|-----|------|-----|
| **Vue 3** | UI 프레임워크 | 3.5+ |
| **Pinia** | 상태 관리 | 3.0+ |
| **Tailwind CSS v4** | 스타일링 | 4.0+ |
| **highlight.js** | 코드 하이라이팅 | 11.11+ |
| **Vite** | 빌드 도구 | 7.2+ |
| **axios** | HTTP 클라이언트 | 1.13+ |

---

## 📚 API 문서

### 핵심 엔드포인트

#### 🔍 인덱싱

```http
POST /api/index
Content-Type: application/json

{
  "code_path": "/Users/gcpark/code/my-project",
  "project_name": "MyProject",  // 선택사항
  "force": false                 // true: 재인덱싱
}
```

**응답:**
```json
{
  "status": "success",
  "project": "MyProject",
  "indexed_files": 45,
  "chunks": 312,
  "message": "인덱싱 완료: 45개 파일, 312개 청크"
}
```

#### 💬 질의

```http
POST /api/query
Content-Type: application/json

{
  "question": "JWT 인증은 어떻게 구현했어?",
  "top_k": 5  // 검색할 청크 수 (1-20)
}
```

**응답:**
```json
{
  "answer": "JWT 인증은 `JwtTokenProvider` 클래스에서...",
  "sources": [
    {
      "file": "security/JwtTokenProvider.java",
      "project": "BizSync",
      "chunk_type": "class",
      "name": "JwtTokenProvider",
      "snippet": "@Component public class...",
      "distance": 0.23
    }
  ],
  "model": "qwen2.5:3b"
}
```

#### 📡 스트리밍 질의

```http
POST /api/query/stream
Content-Type: application/json

{
  "question": "WebSocket 연결 로직 설명해줘",
  "top_k": 5
}
```

**SSE 이벤트:**
```
event: message
data: WebSocket은

event: message
data:  STOMP 프로토콜을...

event: done
data: [DONE]
```

### 전체 API 목록

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/health` | 헬스체크 |
| GET | `/api/status` | Ollama 연결 및 인덱스 현황 |
| GET | `/api/browse` | 디렉토리 탐색 |
| POST | `/api/index` | 코드 인덱싱 |
| GET | `/api/index/progress` | 인덱싱 진행률 |
| POST | `/api/index/cancel` | 인덱싱 취소 |
| DELETE | `/api/index/{project}` | 프로젝트 삭제 |
| POST | `/api/query` | RAG 질의 |
| POST | `/api/query/stream` | 스트리밍 질의 |
| GET | `/api/models` | Ollama 모델 목록 |
| POST | `/api/models/switch` | 모델 변경 |

📖 **Swagger UI**: http://localhost:8000/docs

---

## 🔧 고급 설정

### 지원 언어 확장

현재 지원: Python, Java, Vue, JavaScript

**새 언어 추가:**

1. `backend/utils/code_parser.py`에 파서 추가
2. AST 기반 청킹 로직 구현
3. `SUPPORTED_EXTENSIONS`에 확장자 등록

### LLM 모델 변경

**API로 동적 변경:**
```bash
curl -X POST http://localhost:8000/api/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:3b"}'
```

**환경변수로 기본값 변경:**
```env
OLLAMA_MODEL=mistral:7b
```

### 외부 LLM API 사용

**OpenAI로 교체:**

`backend/services/llm.py` 수정:
```python
import openai

class LLM:
    def __init__(self):
        self.client = openai.Client(api_key="YOUR_API_KEY")

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
```

---

## 🧪 개발 가이드

### 백엔드 테스트

```bash
cd backend

# 전체 RAG 파이프라인 테스트 (인덱싱 + 질의)
python test_rag.py --index

# 검색만 테스트 (인덱싱 스킵)
python test_rag.py --search

# 특정 프로젝트 테스트
python test_rag.py --project BizSync
```

### 로그 확인

```bash
# 질의 로그 확인
tail -f data/query_logs.jsonl | jq '.'

# 최근 10개 질문
tail -n 10 data/query_logs.jsonl | jq '.question'
```

### 디버깅

**ChromaDB 데이터 확인:**
```python
from services.retriever import Retriever

retriever = Retriever()
stats = retriever.get_project_stats()
print(stats)
```

**임베딩 벡터 확인:**
```python
from services.embedder import Embedder

embedder = Embedder()
vector = embedder.embed("Sample text")
print(f"Dimension: {len(vector)}")  # 384
```

---

## 📊 성능 최적화

### 인덱싱 속도

- **배치 크기 조정**: `main.py`의 `embed_batch_size` (기본: 32)
- **병렬 처리**: 파일 파싱을 멀티프로세싱으로 변경 가능

### 검색 정확도

- **top_k 조정**: 5-10 권장 (너무 많으면 노이즈 증가)
- **임베딩 모델 변경**: `all-MiniLM-L6-v2` → `all-mpnet-base-v2` (더 정확, 느림)

### 메모리 사용량

- **청크 크기**: `code_parser.py`의 최대 라인 수 조정
- **ChromaDB 최적화**: `.env`에 `CHROMA_DB_IMPL=duckdb+parquet`

---

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 라이선스

MIT License - 자유롭게 사용하세요!

---

## 🙏 감사의 글

이 프로젝트는 다음 오픈소스를 활용합니다:

- [FastAPI](https://fastapi.tiangolo.com/) - 현대적인 Python 웹 프레임워크
- [Vue 3](https://vuejs.org/) - 진보된 프론트엔드 프레임워크
- [ChromaDB](https://www.trychroma.com/) - AI-native 벡터 데이터베이스
- [Ollama](https://ollama.ai/) - 로컬 LLM 실행 플랫폼
- [sentence-transformers](https://www.sbert.net/) - 최신 텍스트 임베딩

---

## 💬 문의 및 지원

- 🐛 **버그 리포트**: [GitHub Issues](https://github.com/parkote9212/codebase-qa/issues)
- 💡 **기능 제안**: [GitHub Discussions](https://github.com/parkote9212/codebase-qa/discussions)
- 📧 **이메일**: parkote9212@gmail.com

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/parkote9212">G.C.Park</a>
</p>
