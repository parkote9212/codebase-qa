# Codebase QA Backend

FastAPI 기반 코드베이스 RAG Q&A 백엔드 서버

## 기술 스택

- **Framework**: FastAPI 0.109
- **Vector DB**: ChromaDB 0.4
- **Embedding**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: Ollama (qwen2.5:3b)
- **HTTP Client**: httpx

## 디렉토리 구조

```
backend/
├── main.py                 # FastAPI 엔트리포인트
├── schemas.py              # Pydantic 요청/응답 스키마
├── requirements.txt        # Python 의존성
├── test_rag.py             # RAG 테스트 스크립트
├── services/
│   ├── __init__.py
│   ├── embedder.py         # sentence-transformers 임베딩
│   ├── retriever.py        # ChromaDB 벡터 검색
│   ├── llm.py              # Ollama REST API 클라이언트
│   └── rag_chain.py        # RAG 파이프라인
└── utils/
    ├── __init__.py
    └── code_parser.py      # 코드 파싱 및 청킹
```

## 설치 및 실행

### 1. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. Ollama 실행

```bash
# Ollama 설치 후
ollama serve

# 모델 다운로드 (다른 터미널에서)
ollama pull qwen2.5:3b
```

### 3. 서버 실행

```bash
# 개발 모드 (자동 리로드)
uvicorn main:app --reload --port 8000

# 또는
python main.py
```

## API 엔드포인트

### 헬스체크

```
GET /api/health
```

### 인덱싱

```
POST /api/index
```

코드베이스를 파싱하고 벡터 DB에 저장

**Request Body:**
```json
{
  "code_path": "/Volumes/DEV_DATA/code/BizSync",
  "force": false
}
```

**Response:**
```json
{
  "status": "success",
  "project": "BizSync",
  "indexed_files": 127,
  "chunks": 450,
  "message": "인덱싱 완료: 127개 파일, 450개 청크"
}
```

### 인덱싱 진행률

```
GET /api/index/progress
```

**Response:**
```json
{
  "is_indexing": true,
  "project": "BizSync",
  "current": 45,
  "total": 120,
  "percent": 37,
  "stage": "embedding"
}
```

### 질의

```
POST /api/query
```

RAG 파이프라인으로 질문에 답변

**Request Body:**
```json
{
  "question": "JWT 인증 로직 설명해줘",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "JWT 인증은 JwtTokenProvider 클래스에서...",
  "sources": [
    {
      "file": "/path/to/JwtTokenProvider.java",
      "project": "BizSync",
      "chunk_type": "class",
      "name": "JwtTokenProvider",
      "snippet": "...",
      "distance": 0.234
    }
  ],
  "model": "qwen2.5:3b"
}
```

### 스트리밍 질의

```
POST /api/query/stream
```

SSE(Server-Sent Events)로 답변 스트리밍

### 시스템 상태

```
GET /api/status
```

**Response:**
```json
{
  "ollama_connected": true,
  "ollama_model": "qwen2.5:3b",
  "total_chunks": 680,
  "projects": [
    {
      "project": "BizSync",
      "chunks": 450,
      "languages": {"java": 320, "vue": 80, "js": 50}
    }
  ]
}
```

### 모델 관리

```
GET /api/models          # 사용 가능한 모델 목록
POST /api/models/switch  # 모델 변경
```

### 인덱스 삭제

```
DELETE /api/index/{project_name}
```

## 코드 파서

### 지원 언어

| 확장자 | 언어 | 청킹 단위 |
|--------|------|----------|
| `.py` | Python | 함수, 클래스 (AST 파싱) |
| `.java` | Java | 클래스, 인터페이스, enum |
| `.vue` | Vue | script, template 섹션 |
| `.js` | JavaScript | 함수, 클래스 |

### 메타데이터

각 청크에 포함되는 메타데이터:

- `filepath`: 파일 경로
- `language`: 프로그래밍 언어
- `project`: 프로젝트명
- `chunk_type`: function, class, method, script, template 등
- `name`: 함수/클래스 이름
- `start_line`, `end_line`: 코드 위치

## 로깅

질문/답변은 `data/query_logs.jsonl`에 자동 저장됩니다:

```json
{"timestamp": "2024-01-15T10:30:00", "question": "...", "answer": "...", "model": "qwen2.5:3b"}
```

## 테스트

```bash
# 인덱싱 + RAG 테스트
python test_rag.py --index

# 검색만 테스트 (LLM 없이)
python test_rag.py --search

# 스트리밍 테스트
python test_rag.py --stream
```

## 환경 설정

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CODE_BASE_PATH` | `/Volumes/DEV_DATA/code` | 코드베이스 기본 경로 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 URL |
| `DEFAULT_MODEL` | `qwen2.5:3b` | 기본 LLM 모델 |
