/**
 * API 서비스
 * 백엔드 API 호출 함수들
 */

import axios from 'axios'

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분 (인덱싱은 오래 걸릴 수 있음)
  headers: {
    'Content-Type': 'application/json',
  },
})

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '알 수 없는 오류'
    console.error(`[API Error] ${message}`)
    return Promise.reject(error)
  }
)

/**
 * 시스템 상태 조회
 */
export async function getStatus() {
  const response = await api.get('/api/status')
  return response.data
}

/**
 * 헬스체크
 */
export async function healthCheck() {
  const response = await api.get('/api/health')
  return response.data
}

/**
 * 디렉토리 목록 조회
 * @param {string} path - 조회할 경로
 */
export async function browseDirectory(path = '/Users/gcpark/code') {
  const response = await api.get('/api/browse', { params: { path } })
  return response.data
}

/**
 * 코드베이스 인덱싱
 * @param {string} codePath - 인덱싱할 코드 경로
 * @param {string|null} projectName - 프로젝트명 (선택)
 * @param {boolean} force - 강제 재인덱싱 여부
 */
export async function indexCode(codePath, projectName = null, force = false) {
  const body = {
    code_path: codePath,
    force,
  }
  if (projectName != null && projectName !== '') {
    body.project_name = projectName
  }
  const response = await api.post('/api/index', body)
  return response.data
}

/**
 * 인덱싱 진행률 조회
 */
export async function getIndexProgress() {
  const response = await api.get('/api/index/progress')
  return response.data
}

/**
 * 인덱싱 취소
 */
export async function cancelIndexing() {
  const response = await api.post('/api/index/cancel')
  return response.data
}

/**
 * RAG 질의
 * @param {string} question - 질문
 * @param {number} topK - 검색할 문서 수
 */
export async function queryCode(question, topK = 5) {
  const response = await api.post('/api/query', {
    question,
    top_k: topK,
  })
  return response.data
}

/**
 * 프로젝트 인덱스 삭제
 * @param {string} projectName - 프로젝트명
 */
export async function deleteIndex(projectName) {
  const response = await api.delete(`/api/index/${projectName}`)
  return response.data
}

/**
 * Ollama 모델 목록 조회
 */
export async function getModels() {
  const response = await api.get('/api/models')
  return response.data
}

/**
 * 모델 변경
 * @param {string} model - 변경할 모델명
 */
export async function switchModel(model) {
  const response = await api.post('/api/models/switch', { model })
  return response.data
}

// 활성 스트리밍 AbortController (취소용)
let activeStreamController = null

/**
 * 활성 스트리밍 연결 정리
 */
export function cleanupActiveStream() {
  if (activeStreamController) {
    activeStreamController.abort()
    activeStreamController = null
  }
}

/**
 * SSE 스트리밍 질의 (POST + fetch 스트림, 타자치듯 한 글자씩)
 * @param {string} question - 질문
 * @param {number} topK - 검색할 문서 수
 * @param {function} onMessage - 메시지 콜백 (chunk)
 * @param {function} onError - 에러 콜백
 * @param {function} onDone - 완료 콜백
 * @returns {{ abort: function }}
 */
export async function queryCodeStream(question, topK = 5, { onMessage, onError, onDone }) {
  cleanupActiveStream()
  const controller = new AbortController()
  activeStreamController = controller

  const abort = () => {
    controller.abort()
    if (activeStreamController === controller) activeStreamController = null
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: topK }),
      signal: controller.signal,
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(err.detail || `HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const block of parts) {
        if (!block.trim()) continue
        let event = ''
        let dataLines = []
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) dataLines.push(line.slice(5))
        }
        // data: 여러 줄이면 줄바꿈으로 연결 (SSE 스펙)
        const data = dataLines.join('\n')
        if (event === 'message') {
          onMessage?.(data)
        } else if (event === 'done' && data.trim() === '[DONE]') {
          if (activeStreamController === controller) activeStreamController = null
          onDone?.()
          return { abort }
        } else if (event === 'error') {
          if (activeStreamController === controller) activeStreamController = null
          onError?.(new Error(data))
          return { abort }
        }
      }
    }
    if (activeStreamController === controller) activeStreamController = null
    onDone?.()
  } catch (err) {
    if (activeStreamController === controller) activeStreamController = null
    if (err.name === 'AbortError') return { abort }
    onError?.(err)
  }
  return { abort }
}

export default api
