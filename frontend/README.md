# Codebase QA Frontend

Vue 3 기반 코드베이스 Q&A 프론트엔드 애플리케이션

## 기술 스택

- **Framework**: Vue 3.5 (Composition API)
- **State Management**: Pinia 3
- **Router**: Vue Router 5
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS 4
- **Syntax Highlighting**: highlight.js
- **Build Tool**: Vite 7

## 디렉토리 구조

```
frontend/
├── src/
│   ├── api/
│   │   └── index.js          # API 서비스 (axios)
│   ├── components/
│   │   ├── ChatInput.vue     # 메시지 입력창
│   │   ├── ChatMessage.vue   # 채팅 메시지 표시
│   │   ├── CodeBlock.vue     # 코드 블록 (하이라이팅)
│   │   └── Sidebar.vue       # 사이드바 (프로젝트 목록)
│   ├── stores/
│   │   └── chat.js           # Pinia 스토어
│   ├── views/
│   │   └── ChatView.vue      # 메인 채팅 페이지
│   ├── App.vue               # 루트 컴포넌트
│   ├── main.js               # 엔트리포인트
│   └── style.css             # 전역 스타일
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 설치 및 실행

### 1. 의존성 설치

```bash
cd frontend
npm install
```

### 2. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 http://localhost:5173 접속

### 3. 프로덕션 빌드

```bash
npm run build
npm run preview  # 빌드 결과 미리보기
```

## 주요 컴포넌트

### ChatView.vue

메인 채팅 인터페이스 페이지

**기능:**
- 상단 헤더: Ollama 연결 상태, 다크모드 토글
- 메시지 영역: 사용자/AI 대화 표시
- 하단 입력창: 질문 입력

### Sidebar.vue

프로젝트 관리 사이드바

**기능:**
- 인덱싱된 프로젝트 목록 (체크 표시)
- 미인덱싱 프로젝트 클릭 시 인덱싱
- "Clear Chat" 버튼
- "Add Project" 버튼 → 인덱싱 모달
- 인덱싱 진행률 프로그레스바

### ChatMessage.vue

채팅 메시지 컴포넌트

**기능:**
- User 메시지: 오른쪽 정렬, 파란 배경
- Assistant 메시지: 왼쪽 정렬, 아이콘 + 라벨
- 코드 블록 자동 파싱 및 하이라이팅
- **bold** 텍스트 파싱
- Sources 접기/펼치기
- 메시지 복사 버튼

### ChatInput.vue

메시지 입력 컴포넌트

**기능:**
- textarea 여러 줄 입력
- Enter: 전송
- Shift+Enter: 줄바꿈
- 자동 높이 조절
- 마운트 시 자동 포커스

### CodeBlock.vue

코드 블록 컴포넌트

**기능:**
- highlight.js 자동 언어 감지
- 복사 버튼
- 언어 표시

## Pinia Store (chat.js)

### State

```javascript
{
  messages: [],           // 채팅 메시지 배열
  isLoading: false,       // 로딩 상태
  indexedProjects: [],    // 인덱싱된 프로젝트 목록
  systemStatus: {         // 시스템 상태
    ollama_connected: false,
    ollama_model: '',
    total_chunks: 0,
  },
  indexProgress: {        // 인덱싱 진행률
    is_indexing: false,
    project: null,
    current: 0,
    total: 0,
    percent: 0,
    stage: '',
  },
  availableModels: [],    // 사용 가능한 모델 목록
  isDarkMode: true,       // 다크모드 상태
}
```

### Actions

| Action | 설명 |
|--------|------|
| `sendMessage(content)` | 메시지 전송 및 AI 응답 받기 |
| `fetchStatus()` | 시스템 상태 조회 |
| `fetchIndexProgress()` | 인덱싱 진행률 조회 |
| `indexProject(path, force)` | 프로젝트 인덱싱 |
| `removeProject(name)` | 프로젝트 삭제 |
| `fetchModels()` | 모델 목록 조회 |
| `changeModel(name)` | 모델 변경 |
| `clearMessages()` | 대화 초기화 |
| `toggleDarkMode()` | 다크모드 토글 |
| `initDarkMode()` | 다크모드 초기화 (localStorage) |

## API 서비스 (api/index.js)

### 함수 목록

```javascript
// 시스템
getStatus()              // 시스템 상태 조회
healthCheck()            // 헬스체크

// 인덱싱
indexCode(path, force)   // 코드베이스 인덱싱
getIndexProgress()       // 인덱싱 진행률 조회
deleteIndex(project)     // 프로젝트 삭제

// 질의
queryCode(question, topK)           // RAG 질의
queryCodeStream(question, topK, callbacks)  // SSE 스트리밍 질의

// 모델
getModels()              // 모델 목록 조회
switchModel(model)       // 모델 변경
```

## 스타일링

### Tailwind 커스텀 색상

```javascript
// tailwind.config.js
colors: {
  dark: {
    50: '#f7f7f8',
    // ...
    900: '#202123',
    950: '#0d0d0d',
  },
}
```

### 다크모드

- 기본적으로 다크모드 활성화
- localStorage에 테마 저장
- `document.documentElement.classList`로 전환

## 환경 설정

### Vite Proxy

```javascript
// vite.config.js
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

### API Base URL

```javascript
// api/index.js
const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 300000,  // 5분
})
```
