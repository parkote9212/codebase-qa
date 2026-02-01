<script setup>
/**
 * CodeBlock 컴포넌트
 * 코드 신택스 하이라이팅 및 복사 기능 (목업 UI 반영)
 */

import { ref, computed } from 'vue'
import hljs from 'highlight.js'

const props = defineProps({
  code: {
    type: String,
    required: true,
  },
  language: {
    type: String,
    default: '',
  },
})

const copied = ref(false)

// 언어 감지 및 하이라이팅
const highlightedCode = computed(() => {
  if (props.language && hljs.getLanguage(props.language)) {
    return hljs.highlight(props.code, { language: props.language }).value
  }
  // 자동 감지
  const result = hljs.highlightAuto(props.code)
  return result.value
})

const detectedLanguage = computed(() => {
  if (props.language) return props.language
  const result = hljs.highlightAuto(props.code)
  return result.language || 'text'
})

// 복사 기능
async function copyCode() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('복사 실패:', err)
  }
}
</script>

<template>
  <div class="rounded-lg overflow-hidden bg-gray-50 dark:bg-dark-950 border border-gray-200 dark:border-dark-700">
    <!-- 헤더 -->
    <div class="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-dark-800/50">
      <span class="text-xs text-gray-500 font-mono">{{ detectedLanguage }}</span>
      <button
        @click="copyCode"
        class="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
      >
        <input
          type="checkbox"
          :checked="copied"
          readonly
          class="w-3.5 h-3.5 rounded border-gray-600 bg-transparent text-blue-500 focus:ring-0 cursor-pointer"
        />
        <span>Copy</span>
      </button>
    </div>

    <!-- 코드 -->
    <pre class="overflow-x-auto p-4 text-sm leading-relaxed"><code
      class="hljs text-gray-800 dark:text-gray-300"
      v-html="highlightedCode"
    ></code></pre>
  </div>
</template>
