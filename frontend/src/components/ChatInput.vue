<script setup>
/**
 * ChatInput 컴포넌트
 * 메시지 입력 및 전송 (textarea + 자동포커스)
 */

import { ref, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const input = ref('')
const textareaRef = ref(null)
const isComposing = ref(false)  // IME 입력 중 (한글 등)

// 메시지 전송
async function handleSubmit() {
  if (!input.value.trim() || chatStore.isLoading) return

  const message = input.value
  input.value = ''

  // textarea 높이 초기화
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }

  await chatStore.sendMessage(message)

  // 전송 후 다시 포커스
  textareaRef.value?.focus()
}

// Enter 키 처리 (Shift+Enter는 줄바꿈)
// keyup 사용: v-model 업데이트 후 발생하여 마지막 글자 누락 방지
// isComposing 체크: 한글 등 IME 입력 완료 전 전송 방지
function handleKeyup(e) {
  if (e.key === 'Enter' && !e.shiftKey && !isComposing.value) {
    e.preventDefault()
    handleSubmit()
  }
}

// keydown에서는 Enter 기본 동작(줄바꿈)만 방지
function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !isComposing.value) {
    e.preventDefault()
  }
}

// IME 입력 시작/종료 처리
function handleCompositionStart() {
  isComposing.value = true
}

function handleCompositionEnd() {
  isComposing.value = false
}

// Textarea 자동 높이 조절
function handleInput(e) {
  const textarea = e.target
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
}

// 마운트시 자동 포커스
onMounted(() => {
  textareaRef.value?.focus()
})
</script>

<template>
  <div class="px-6 py-4 bg-gray-50 dark:bg-dark-900 border-t border-gray-200 dark:border-dark-800">
    <form @submit.prevent="handleSubmit" class="flex items-center gap-3 max-w-4xl mx-auto">
      <div class="flex-1 min-w-0 flex items-center">
        <textarea
          ref="textareaRef"
          v-model="input"
          @keydown="handleKeydown"
          @keyup="handleKeyup"
          @compositionstart="handleCompositionStart"
          @compositionend="handleCompositionEnd"
          @input="handleInput"
          rows="1"
          placeholder="코드에 대해 질문하세요... (Shift+Enter: 줄바꿈)"
          :disabled="chatStore.isLoading"
          class="w-full min-h-11 max-h-[200px] py-3 px-4 bg-white dark:bg-dark-800 border border-gray-300 dark:border-dark-700 rounded-xl text-gray-900 dark:text-white text-sm placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 dark:focus:border-dark-600 disabled:opacity-50 disabled:cursor-not-allowed leading-5 box-border"
        ></textarea>
      </div>

      <button
        type="submit"
        :disabled="!input.trim() || chatStore.isLoading"
        class="h-11 shrink-0 px-5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-dark-700 disabled:text-gray-500 disabled:cursor-not-allowed rounded-xl text-white text-sm font-medium transition-colors flex items-center justify-center"
      >
        {{ chatStore.isLoading ? '생성 중...' : '전송' }}
      </button>
    </form>
  </div>
</template>
