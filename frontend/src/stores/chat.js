/**
 * Chat Store (Pinia)
 * 채팅 상태 관리
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import {
  queryCode,
  getStatus,
  indexCode,
  deleteIndex,
  getIndexProgress,
  cancelIndexing,
  getModels,
  switchModel,
} from '@/api'

// localStorage 키
const STORAGE_KEY = 'codebase-qa-sessions'

/**
 * localStorage에서 세션 로드
 */
function loadSessionsFromStorage() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      // Date 문자열을 Date 객체로 변환
      data.sessions = data.sessions.map(s => ({
        ...s,
        createdAt: new Date(s.createdAt),
        messages: s.messages.map(m => ({
          ...m,
          timestamp: new Date(m.timestamp)
        }))
      }))
      return data
    }
  } catch (error) {
    console.error('세션 로드 실패:', error)
  }
  return null
}

/**
 * localStorage에 세션 저장
 */
function saveSessionsToStorage(sessions, currentSessionId, nextSessionId) {
  try {
    const data = {
      sessions: sessions,
      currentSessionId: currentSessionId,
      nextSessionId: nextSessionId,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch (error) {
    console.error('세션 저장 실패:', error)
  }
}

export const useChatStore = defineStore('chat', () => {
  // localStorage에서 세션 복원
  const storedData = loadSessionsFromStorage()

  // 세션 관리
  const sessions = ref(
    storedData?.sessions || [{ id: 1, name: '새 대화', messages: [], createdAt: new Date() }]
  )
  const currentSessionId = ref(storedData?.currentSessionId || 1)
  const nextSessionId = ref(storedData?.nextSessionId || 2)

  // 현재 세션의 메시지
  const messages = computed({
    get: () => {
      const session = sessions.value.find(s => s.id === currentSessionId.value)
      return session ? session.messages : []
    },
    set: (newMessages) => {
      const session = sessions.value.find(s => s.id === currentSessionId.value)
      if (session) {
        session.messages = newMessages
      }
    }
  })

  // State
  const isLoading = ref(false)
  const isStatusLoading = ref(true)  // 상태 로딩 중
  const indexedProjects = ref([])
  const systemStatus = ref({
    ollama_connected: false,
    ollama_model: '',
    total_chunks: 0,
  })

  // 인덱싱 진행률
  const indexProgress = ref({
    is_indexing: false,
    project: null,
    current: 0,
    total: 0,
    percent: 0,
    stage: '',
  })

  // 모델 목록
  const availableModels = ref([])

  // Getters
  const hasMessages = computed(() => messages.value.length > 0)
  const lastMessage = computed(() => messages.value[messages.value.length - 1])
  const currentSession = computed(() => sessions.value.find(s => s.id === currentSessionId.value))

  // 세션 변경 감지 및 localStorage 저장
  watch(
    [sessions, currentSessionId, nextSessionId],
    () => {
      saveSessionsToStorage(sessions.value, currentSessionId.value, nextSessionId.value)
    },
    { deep: true }
  )

  // Actions

  /**
   * 메시지 전송
   */
  async function sendMessage(content) {
    if (!content.trim() || isLoading.value) return

    // 사용자 메시지 추가
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (session) {
      session.messages.push(userMessage)

      // 첫 메시지면 세션 이름 업데이트
      if (session.messages.length === 1) {
        session.name = content.trim().slice(0, 30) + (content.length > 30 ? '...' : '')
      }
    }

    // 로딩 시작
    isLoading.value = true

    try {
      const response = await queryCode(content)

      // AI 응답 추가
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        model: response.model,
        timestamp: new Date(),
      }
      const sessionForResponse = sessions.value.find(s => s.id === currentSessionId.value)
      if (sessionForResponse) {
        sessionForResponse.messages.push(assistantMessage)
      }

    } catch (error) {
      // 에러 메시지 추가 (재시도용 원본 질문 포함)
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `오류가 발생했습니다: ${error.response?.data?.detail || error.message}`,
        isError: true,
        originalQuestion: content.trim(),  // 재시도용 원본 질문 저장
        timestamp: new Date(),
      }
      const sessionForError = sessions.value.find(s => s.id === currentSessionId.value)
      if (sessionForError) {
        sessionForError.messages.push(errorMessage)
      }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 시스템 상태 조회
   */
  async function fetchStatus() {
    isStatusLoading.value = true
    try {
      const status = await getStatus()
      systemStatus.value = {
        ollama_connected: status.ollama_connected,
        ollama_model: status.ollama_model,
        total_chunks: status.total_chunks,
      }
      indexedProjects.value = status.projects || []
    } catch (error) {
      console.error('상태 조회 실패:', error)
      systemStatus.value.ollama_connected = false
    } finally {
      isStatusLoading.value = false
    }
  }

  /**
   * 인덱싱 진행률 조회
   */
  async function fetchIndexProgress() {
    try {
      const progress = await getIndexProgress()
      indexProgress.value = progress
      return progress
    } catch (error) {
      console.error('진행률 조회 실패:', error)
      return null
    }
  }

  /**
   * 프로젝트 인덱싱
   * @param {string} codePath - 코드 경로
   * @param {string|null} projectName - 프로젝트명 (선택)
   * @param {boolean} force - 강제 재인덱싱
   */
  async function indexProject(codePath, projectName = null, force = false) {
    try {
      const result = await indexCode(codePath, projectName, force)
      // 상태 갱신
      await fetchStatus()
      return result
    } catch (error) {
      console.error('인덱싱 실패:', error)
      throw error
    }
  }

  /**
   * 프로젝트 삭제
   */
  async function removeProject(projectName) {
    try {
      const result = await deleteIndex(projectName)
      // 상태 갱신
      await fetchStatus()
      return result
    } catch (error) {
      console.error('삭제 실패:', error)
      throw error
    }
  }

  /**
   * 인덱싱 취소
   */
  async function cancelIndex() {
    try {
      const result = await cancelIndexing()
      return result
    } catch (error) {
      console.error('취소 실패:', error)
      throw error
    }
  }

  /**
   * 모델 목록 조회
   */
  async function fetchModels() {
    try {
      const result = await getModels()
      availableModels.value = result.models || []
      return result
    } catch (error) {
      console.error('모델 목록 조회 실패:', error)
      return null
    }
  }

  /**
   * 모델 변경
   */
  async function changeModel(modelName) {
    try {
      const result = await switchModel(modelName)
      systemStatus.value.ollama_model = result.current
      return result
    } catch (error) {
      console.error('모델 변경 실패:', error)
      throw error
    }
  }

  /**
   * 에러 메시지 재시도
   */
  async function retryMessage(messageId) {
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (!session) return

    // 에러 메시지 찾기
    const errorMsgIndex = session.messages.findIndex(m => m.id === messageId && m.isError)
    if (errorMsgIndex === -1) return

    const errorMsg = session.messages[errorMsgIndex]
    const originalQuestion = errorMsg.originalQuestion

    if (!originalQuestion) return

    // 에러 메시지와 이전 사용자 메시지 삭제
    session.messages.splice(errorMsgIndex - 1, 2)

    // 다시 전송
    await sendMessage(originalQuestion)
  }

  /**
   * 메시지 초기화
   */
  function clearMessages() {
    const session = sessions.value.find(s => s.id === currentSessionId.value)
    if (session) {
      session.messages = []
      session.name = '새 대화'
    }
  }

  /**
   * 새 세션 생성
   */
  function createSession() {
    const newSession = {
      id: nextSessionId.value++,
      name: '새 대화',
      messages: [],
      createdAt: new Date(),
    }
    sessions.value.unshift(newSession)
    currentSessionId.value = newSession.id
    return newSession
  }

  /**
   * 세션 전환
   */
  function switchSession(sessionId) {
    if (sessions.value.some(s => s.id === sessionId)) {
      currentSessionId.value = sessionId
    }
  }

  /**
   * 세션 삭제
   */
  function deleteSession(sessionId) {
    const index = sessions.value.findIndex(s => s.id === sessionId)
    if (index === -1) return

    sessions.value.splice(index, 1)

    // 삭제 후 세션이 없으면 새로 생성
    if (sessions.value.length === 0) {
      createSession()
    } else if (currentSessionId.value === sessionId) {
      // 현재 세션이 삭제되면 첫번째 세션으로 전환
      currentSessionId.value = sessions.value[0].id
    }
  }

  /**
   * 세션 이름 변경
   */
  function renameSession(sessionId, newName) {
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      session.name = newName.trim() || '새 대화'
    }
  }

  return {
    // State
    sessions,
    currentSessionId,
    messages,
    isLoading,
    isStatusLoading,
    indexedProjects,
    systemStatus,
    indexProgress,
    availableModels,

    // Getters
    hasMessages,
    lastMessage,
    currentSession,

    // Actions
    sendMessage,
    fetchStatus,
    fetchIndexProgress,
    indexProject,
    removeProject,
    cancelIndex,
    fetchModels,
    changeModel,
    clearMessages,
    retryMessage,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
  }
})
