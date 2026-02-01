<script setup>
/**
 * SessionPanel 컴포넌트
 * 채팅 세션 목록 관리
 */

import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()

// 편집 중인 세션
const editingSessionId = ref(null)
const editingName = ref('')

// 삭제 확인
const deletingSessionId = ref(null)

// 세션 목록 (최신순)
const sortedSessions = computed(() => {
  return [...chatStore.sessions].sort((a, b) => {
    return new Date(b.createdAt) - new Date(a.createdAt)
  })
})

// 새 세션 생성
function handleNewSession() {
  chatStore.createSession()
}

// 세션 전환
function handleSwitchSession(sessionId) {
  if (editingSessionId.value === sessionId) return
  chatStore.switchSession(sessionId)
}

// 세션 삭제
function handleDeleteSession(sessionId) {
  chatStore.deleteSession(sessionId)
  deletingSessionId.value = null
}

// 이름 편집 시작
function startEditing(session) {
  editingSessionId.value = session.id
  editingName.value = session.name
}

// 이름 편집 완료
function finishEditing() {
  if (editingSessionId.value) {
    chatStore.renameSession(editingSessionId.value, editingName.value)
    editingSessionId.value = null
    editingName.value = ''
  }
}

// 날짜 포맷
function formatDate(date) {
  const d = new Date(date)
  const now = new Date()
  const diff = now - d

  // 오늘
  if (diff < 24 * 60 * 60 * 1000 && d.getDate() === now.getDate()) {
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }
  // 어제
  if (diff < 48 * 60 * 60 * 1000) {
    return '어제'
  }
  // 그 외
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}
</script>

<template>
  <aside class="w-56 bg-white dark:bg-dark-950 border-l border-gray-200 dark:border-dark-800 flex flex-col h-full">
    <!-- 헤더 -->
    <div class="p-4 flex items-center justify-between">
      <h2 class="text-sm font-semibold text-gray-900 dark:text-white">채팅 세션</h2>
      <button
        @click="handleNewSession"
        class="p-1.5 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg transition-colors"
        title="새 대화"
      >
        <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>

    <!-- 세션 목록 -->
    <div class="flex-1 overflow-y-auto px-3 pb-3">
      <div class="space-y-1">
        <div
          v-for="session in sortedSessions"
          :key="session.id"
          @click="handleSwitchSession(session.id)"
          :class="[
            'group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors',
            session.id === chatStore.currentSessionId
              ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
              : 'hover:bg-gray-100 dark:hover:bg-dark-800'
          ]"
        >
          <!-- 채팅 아이콘 -->
          <svg
            :class="[
              'w-4 h-4 shrink-0',
              session.id === chatStore.currentSessionId
                ? 'text-blue-500'
                : 'text-gray-400 dark:text-gray-500'
            ]"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>

          <div class="flex-1 min-w-0">
            <!-- 이름 편집 중 -->
            <input
              v-if="editingSessionId === session.id"
              v-model="editingName"
              @blur="finishEditing"
              @keyup.enter="finishEditing"
              @click.stop
              class="w-full text-sm bg-transparent border-b border-blue-500 outline-none text-gray-900 dark:text-white"
              autofocus
            />
            <!-- 이름 표시 -->
            <div v-else class="text-sm text-gray-900 dark:text-white truncate">
              {{ session.name }}
            </div>
            <!-- 날짜 -->
            <div class="text-xs text-gray-500 dark:text-gray-500">
              {{ session.messages.length }}개 메시지 · {{ formatDate(session.createdAt) }}
            </div>
          </div>

          <!-- 액션 버튼들 -->
          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <!-- 이름 편집 -->
            <button
              @click.stop="startEditing(session)"
              class="p-1 hover:bg-gray-200 dark:hover:bg-dark-700 rounded"
              title="이름 변경"
            >
              <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <!-- 삭제 -->
            <button
              v-if="chatStore.sessions.length > 1"
              @click.stop="deletingSessionId = session.id"
              class="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
              title="삭제"
            >
              <svg class="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 삭제 확인 모달 -->
    <Teleport to="body">
      <div
        v-if="deletingSessionId"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="deletingSessionId = null"
      >
        <div class="bg-white dark:bg-dark-800 rounded-xl p-5 w-full max-w-xs mx-4 border border-gray-200 dark:border-dark-600 shadow-xl">
          <h3 class="text-base font-semibold text-gray-900 dark:text-white mb-2">세션 삭제</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            이 대화를 삭제하시겠습니까?
          </p>
          <div class="flex gap-2">
            <button
              @click="deletingSessionId = null"
              class="flex-1 px-3 py-2 bg-gray-200 dark:bg-dark-700 hover:bg-gray-300 dark:hover:bg-dark-600 rounded-lg text-sm text-gray-900 dark:text-white transition-colors"
            >
              취소
            </button>
            <button
              @click="handleDeleteSession(deletingSessionId)"
              class="flex-1 px-3 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm text-white transition-colors"
            >
              삭제
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>
