<script setup>
/**
 * ChatView 페이지
 * 메인 채팅 인터페이스 (Pinia theme 스토어로 다크/라이트)
 */

import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useThemeStore } from '@/stores/theme'
import { cleanupActiveStream } from '@/api'
import Sidebar from '@/components/Sidebar.vue'
import SessionPanel from '@/components/SessionPanel.vue'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'

const chatStore = useChatStore()
const themeStore = useThemeStore()
const messagesContainer = ref(null)

// 대화 내보내기
const showExportMenu = ref(false)
const exportCopied = ref(false)

// 인덱싱된 프로젝트 이름들
const projectNames = computed(() =>
  chatStore.indexedProjects.map(p => p.project).join(', ')
)

// 메시지 추가시 스크롤
watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 대화를 마크다운으로 변환
function conversationToMarkdown() {
  if (!chatStore.messages.length) return ''

  const lines = ['# 대화 내역\n']
  const now = new Date()
  lines.push(`> 생성일시: ${now.toLocaleString('ko-KR')}\n`)
  lines.push('---\n')

  for (const msg of chatStore.messages) {
    if (msg.role === 'user') {
      lines.push(`## 👤 사용자\n`)
      lines.push(`${msg.content}\n`)
    } else {
      lines.push(`## 🤖 Assistant\n`)
      lines.push(`${msg.content}\n`)

      // 소스 정보 추가
      if (msg.sources?.length) {
        lines.push(`\n<details>\n<summary>📎 참조 소스 (${msg.sources.length}개)</summary>\n`)
        for (const src of msg.sources) {
          lines.push(`- \`${src.file}\`: ${src.name}`)
        }
        lines.push(`\n</details>\n`)
      }
    }
    lines.push('\n---\n')
  }

  return lines.join('\n')
}

// 대화 복사
async function copyConversation() {
  try {
    const markdown = conversationToMarkdown()
    await navigator.clipboard.writeText(markdown)
    exportCopied.value = true
    setTimeout(() => {
      exportCopied.value = false
      showExportMenu.value = false
    }, 1500)
  } catch (err) {
    console.error('복사 실패:', err)
  }
}

// MD 파일 다운로드
function downloadMarkdown() {
  const markdown = conversationToMarkdown()
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `conversation_${new Date().toISOString().slice(0, 10)}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  showExportMenu.value = false
}

// 외부 클릭시 드롭다운 닫기
function handleClickOutside(event) {
  if (showExportMenu.value && !event.target.closest('.export-menu-container')) {
    showExportMenu.value = false
  }
}

// 초기 로드
onMounted(() => {
  chatStore.fetchStatus()
  document.addEventListener('click', handleClickOutside)
})

// 정리
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  cleanupActiveStream()
})
</script>

<template>
  <div class="flex h-screen bg-gray-50 dark:bg-dark-900">
    <!-- 사이드바 -->
    <Sidebar />

    <!-- 메인 영역 -->
    <main class="flex-1 flex flex-col min-w-0">
      <!-- 상단 헤더 -->
      <header class="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-dark-800 bg-white dark:bg-dark-900">
        <!-- Ollama 상태 -->
        <div class="flex items-center gap-2">
          <!-- 로딩 중 -->
          <template v-if="chatStore.isStatusLoading">
            <span class="w-2 h-2 rounded-full bg-yellow-500 animate-pulse"></span>
            <span class="text-sm text-gray-600 dark:text-gray-400">연결 확인 중...</span>
          </template>
          <!-- 연결됨 -->
          <template v-else-if="chatStore.systemStatus.ollama_connected">
            <span class="w-2 h-2 rounded-full bg-green-500"></span>
            <span class="text-sm text-gray-600 dark:text-gray-400">
              Ollama connected ({{ chatStore.systemStatus.ollama_model }})
            </span>
          </template>
          <!-- 연결 안됨 -->
          <template v-else>
            <span class="w-2 h-2 rounded-full bg-red-500"></span>
            <span class="text-sm text-gray-600 dark:text-gray-400">Ollama disconnected</span>
          </template>
        </div>

        <div class="flex items-center gap-2">
          <!-- 대화 내보내기 버튼 -->
          <div class="relative export-menu-container">
            <button
              v-if="chatStore.hasMessages"
              @click="showExportMenu = !showExportMenu"
              class="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg transition-colors"
              title="대화 내보내기"
            >
              <svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>

            <!-- 드롭다운 메뉴 -->
            <div
              v-if="showExportMenu"
              class="absolute right-0 mt-2 w-48 bg-white dark:bg-dark-800 border border-gray-200 dark:border-dark-600 rounded-lg shadow-lg z-50"
            >
              <button
                @click="copyConversation"
                class="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-700 rounded-t-lg transition-colors"
              >
                <svg v-if="!exportCopied" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <svg v-else class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                {{ exportCopied ? '복사됨!' : '클립보드에 복사' }}
              </button>
              <button
                @click="downloadMarkdown"
                class="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-700 rounded-b-lg transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                MD 파일로 저장
              </button>
            </div>
          </div>

          <!-- 다크/라이트 토글 (Pinia theme) -->
          <button
            @click="themeStore.toggle"
            class="p-2 hover:bg-gray-100 dark:hover:bg-dark-800 rounded-lg transition-colors"
            :title="themeStore.isDarkMode ? '라이트 모드' : '다크 모드'"
          >
            <svg v-if="themeStore.isDarkMode" class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
            <svg v-else class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </button>
        </div>
      </header>

      <!-- 메시지 영역 -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto px-6 py-4"
      >
        <!-- 빈 상태 -->
        <div
          v-if="!chatStore.hasMessages"
          class="h-full flex items-center justify-center"
        >
          <div class="text-center max-w-md">
            <div class="w-16 h-16 mx-auto mb-4 bg-gray-200 dark:bg-dark-800 rounded-2xl flex items-center justify-center">
              <svg class="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">코드에 대해 질문하세요</h2>
            <p class="text-gray-500 dark:text-gray-500 text-sm">
              인덱싱된 프로젝트의 코드를 기반으로 답변합니다
            </p>
          </div>
        </div>

        <!-- 메시지 목록 -->
        <div v-else class="max-w-4xl mx-auto space-y-6">
          <ChatMessage
            v-for="message in chatStore.messages"
            :key="message.id"
            :message="message"
            :is-streaming="chatStore.isLoading && message.role === 'assistant' && message.id === (chatStore.lastMessage?.id)"
          />

          <!-- 로딩 인디케이터 (스트리밍이 아닐 때만: 마지막이 어시스턴트면 이미 위에서 표시) -->
          <div v-if="chatStore.isLoading && (!chatStore.lastMessage || chatStore.lastMessage.role !== 'assistant')" class="flex justify-start">
            <div class="bg-gray-200 dark:bg-dark-800 rounded-2xl px-5 py-4">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 bg-gray-400 dark:bg-dark-600 rounded-lg flex items-center justify-center">
                  <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <span class="text-sm text-gray-500 dark:text-gray-400">Assistant</span>
              </div>
              <div class="flex items-center gap-2 mt-3 ml-8">
                <div class="flex space-x-1">
                  <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                  <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                  <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                </div>
                <span class="text-gray-500 text-sm">답변 생성 중...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 입력 영역 -->
      <ChatInput />

      <!-- 하단 안내 문구 -->
      <div v-if="projectNames" class="text-center py-2 text-xs text-gray-500 dark:text-gray-600">
        {{ projectNames }} 프로젝트 코드를 기반으로 답변합니다
      </div>
    </main>

    <!-- 세션 패널 (오른쪽) -->
    <SessionPanel />
  </div>
</template>
