<script setup>
/**
 * ChatMessage 컴포넌트
 * 사용자/어시스턴트 메시지 표시 (목업 UI 반영)
 */

import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import CodeBlock from './CodeBlock.vue'

const chatStore = useChatStore()

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
  /** 스트리밍 중인 마지막 어시스턴트 메시지일 때 true */
  isStreaming: {
    type: Boolean,
    default: false,
  },
})

const showSources = ref(false)
const copied = ref(false)
const isRetrying = ref(false)

// 메시지 내 코드 블록 파싱
const parsedContent = computed(() => {
  const content = props.message.content
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(content)) !== null) {
    // 코드 블록 이전 텍스트
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex, match.index),
      })
    }

    // 코드 블록
    parts.push({
      type: 'code',
      language: match[1] || '',
      content: match[2].trim(),
    })

    lastIndex = match.index + match[0].length
  }

  // 마지막 텍스트
  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.slice(lastIndex),
    })
  }

  // 코드 블록이 없으면 전체를 텍스트로
  if (parts.length === 0) {
    parts.push({
      type: 'text',
      content: content,
    })
  }

  return parts
})

// **bold** 텍스트 파싱 (라이트/다크 대응)
function parseMarkdown(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-900 dark:text-white font-semibold">$1</strong>')
}

// 메시지 복사
async function copyMessage() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch (err) {
    console.error('복사 실패:', err)
  }
}

const isUser = computed(() => props.message.role === 'user')
const hasSources = computed(() => props.message.sources?.length > 0)
const isError = computed(() => props.message.isError === true)
const canRetry = computed(() => isError.value && props.message.originalQuestion)

// 재시도
async function handleRetry() {
  if (!canRetry.value || isRetrying.value) return
  isRetrying.value = true
  try {
    await chatStore.retryMessage(props.message.id)
  } finally {
    isRetrying.value = false
  }
}
</script>

<template>
  <!-- 사용자 메시지 -->
  <div v-if="isUser" class="flex justify-end group">
    <div class="max-w-[70%] bg-blue-600 text-white rounded-2xl px-4 py-2.5 relative">
      <div class="text-sm whitespace-pre-wrap">{{ message.content }}</div>
      <!-- 복사 버튼 -->
      <button
        @click="copyMessage"
        class="absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1.5 hover:bg-gray-200 dark:hover:bg-dark-700 rounded transition-all"
        :title="copied ? 'Copied!' : 'Copy message'"
      >
        <svg v-if="!copied" class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <svg v-else class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </button>
    </div>
  </div>

  <!-- 어시스턴트 메시지 -->
  <div v-else class="flex justify-start group">
    <div :class="[
      'max-w-[85%] rounded-2xl px-5 py-4 relative border',
      isError
        ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/50'
        : 'bg-gray-100 dark:bg-dark-800 border-gray-200 dark:border-transparent'
    ]">
      <!-- 어시스턴트 라벨 -->
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 bg-gray-400 dark:bg-dark-600 rounded-lg flex items-center justify-center">
            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <span class="text-sm text-gray-500 dark:text-gray-400">Assistant</span>
        </div>

        <!-- 복사 버튼 -->
        <button
          @click="copyMessage"
          class="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-gray-300 dark:hover:bg-dark-600 rounded transition-all"
          :title="copied ? 'Copied!' : 'Copy message'"
        >
          <svg v-if="!copied" class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <svg v-else class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>

      <!-- 메시지 내용 -->
      <div class="space-y-3">
        <template v-for="(part, index) in parsedContent" :key="index">
          <!-- 텍스트 (빈 내용 + 스트리밍 중일 때는 아래 로딩 표시) -->
          <div
            v-if="part.type === 'text' && (part.content || !isStreaming)"
            class="text-sm text-gray-700 dark:text-gray-200 leading-relaxed whitespace-pre-wrap"
            v-html="parseMarkdown(part.content)"
          ></div>

          <!-- 코드 블록 -->
          <CodeBlock
            v-else-if="part.type === 'code'"
            :code="part.content"
            :language="part.language"
          />
        </template>
        <!-- 스트리밍 중이고 아직 내용이 없을 때 -->
        <div v-if="isStreaming && !message.content" class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <div class="flex space-x-1">
            <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
            <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
            <div class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
          </div>
          <span>답변 생성 중...</span>
        </div>
        <!-- 스트리밍 중이고 내용이 있을 때 커서 -->
        <span v-else-if="isStreaming && message.content" class="inline-block w-2 h-4 ml-0.5 bg-blue-500 dark:bg-blue-400 animate-pulse align-middle"></span>
      </div>

      <!-- 에러 재시도 버튼 -->
      <div v-if="canRetry" class="mt-3">
        <button
          @click="handleRetry"
          :disabled="isRetrying"
          class="flex items-center gap-2 px-3 py-1.5 bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-600 dark:text-red-400 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          <svg v-if="!isRetrying" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          {{ isRetrying ? '재시도 중...' : '다시 시도' }}
        </button>
      </div>

      <!-- 소스 정보 -->
      <div v-if="hasSources" class="mt-4">
        <button
          @click="showSources = !showSources"
          class="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
          <span>Sources ({{ message.sources.length }})</span>
          <svg
            :class="['w-3 h-3 transition-transform', showSources && 'rotate-180']"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- 소스 목록 -->
        <div v-if="showSources" class="mt-2 space-y-1">
          <div
            v-for="(source, idx) in message.sources"
            :key="idx"
            class="text-xs text-gray-500 font-mono py-1.5 px-3 bg-gray-200 dark:bg-dark-900 rounded hover:bg-gray-300 dark:hover:bg-dark-700 cursor-pointer transition-colors truncate"
          >
            {{ source.file }}:{{ source.name }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
