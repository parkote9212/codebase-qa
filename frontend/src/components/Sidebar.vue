<script setup>
/**
 * Sidebar 컴포넌트
 * 프로젝트 목록 및 인덱싱 관리 (진행률 표시 추가)
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { browseDirectory } from '@/api'

const chatStore = useChatStore()

// 인덱싱 모달
const showModal = ref(false)
const indexPath = ref('/Users/gcpark/code')
const projectName = ref('')  // 프로젝트 이름 (선택)
const isIndexing = ref(false)
const indexError = ref('')
const indexResult = ref(null)

// 폴더 브라우저
const showBrowser = ref(false)
const browserPath = ref('/Users/gcpark/code')
const browserDirs = ref([])
const browserParent = ref(null)
const browserLoading = ref(false)

// 삭제 확인 모달
const showDeleteModal = ref(false)
const deleteTarget = ref(null)
const isDeleting = ref(false)

// 인덱싱 취소
const isCancelling = ref(false)

// 진행률 폴링 인터벌
let progressInterval = null

// 미인덱싱 프로젝트 (예시)
const unindexedProjects = ref([])

// 인덱싱된 프로젝트 이름 목록
const indexedProjectNames = computed(() =>
  chatStore.indexedProjects.map(p => p.project)
)

// 초기 로드
onMounted(() => {
  chatStore.fetchStatus()
})

onUnmounted(() => {
  if (progressInterval) {
    clearInterval(progressInterval)
  }
})

// 진행률 폴링 시작
function startProgressPolling() {
  progressInterval = setInterval(async () => {
    const progress = await chatStore.fetchIndexProgress()
    if (!progress?.is_indexing) {
      clearInterval(progressInterval)
      progressInterval = null
    }
  }, 500)
}

// 진행률 폴링 중지
function stopProgressPolling() {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }
}

// 인덱싱 실행
async function handleIndex() {
  if (!indexPath.value.trim()) return

  isIndexing.value = true
  indexError.value = ''
  indexResult.value = null

  // 진행률 폴링 시작
  startProgressPolling()

  try {
    // 프로젝트명이 비어있으면 null 전달 (폴더명 사용)
    const name = projectName.value.trim() || null
    const result = await chatStore.indexProject(indexPath.value.trim(), name)
    indexResult.value = result

    // 인덱싱 성공시 미인덱싱 목록에서 제거
    const folderName = indexPath.value.split('/').pop()
    unindexedProjects.value = unindexedProjects.value.filter(p => p !== folderName)
  } catch (error) {
    indexError.value = error.response?.data?.detail || error.message
  } finally {
    isIndexing.value = false
    stopProgressPolling()
  }
}

// 미인덱싱 프로젝트 클릭시 인덱싱
function indexUnindexed(projectName) {
  indexPath.value = `/Users/gcpark/code/${projectName}`
  showModal.value = true
}

// 모달 닫기
function closeModal() {
  showModal.value = false
  showBrowser.value = false
  indexError.value = ''
  indexResult.value = null
  projectName.value = ''
}

// 폴더 브라우저 열기
async function openBrowser() {
  showBrowser.value = true
  await loadDirectory(indexPath.value || '/Users/gcpark/code')
}

// 디렉토리 로드
async function loadDirectory(path) {
  browserLoading.value = true
  try {
    const result = await browseDirectory(path)
    browserPath.value = result.current_path
    browserDirs.value = result.directories
    browserParent.value = result.parent_path
  } catch (error) {
    console.error('디렉토리 로드 실패:', error)
  } finally {
    browserLoading.value = false
  }
}

// 폴더 선택
function selectFolder(dir) {
  indexPath.value = dir.path
  projectName.value = dir.name
  showBrowser.value = false
}

// 상위 폴더로 이동
function goToParent() {
  if (browserParent.value) {
    loadDirectory(browserParent.value)
  }
}

// 삭제 확인 모달 열기
function confirmDelete(project) {
  deleteTarget.value = project
  showDeleteModal.value = true
}

// 삭제 확인 모달 닫기
function closeDeleteModal() {
  showDeleteModal.value = false
  deleteTarget.value = null
}

// 프로젝트 삭제 실행
async function handleDelete() {
  if (!deleteTarget.value) return

  isDeleting.value = true
  try {
    await chatStore.removeProject(deleteTarget.value.project)
    closeDeleteModal()
  } catch (error) {
    console.error('삭제 실패:', error)
  } finally {
    isDeleting.value = false
  }
}

// 대화 초기화
function clearChat() {
  chatStore.clearMessages()
}

// 스테이지 한글 변환
function getStageLabel(stage) {
  const labels = {
    scanning: '파일 스캔',
    embedding: '임베딩 생성',
    storing: '저장 중',
  }
  return labels[stage] || stage
}

// 인덱싱 취소
async function handleCancel() {
  isCancelling.value = true
  try {
    await chatStore.cancelIndex()
    // 취소 후 상태 갱신을 위해 잠시 대기
    setTimeout(async () => {
      await chatStore.fetchStatus()
      isCancelling.value = false
    }, 1000)
  } catch (error) {
    console.error('취소 실패:', error)
    isCancelling.value = false
  }
}
</script>

<template>
  <aside class="w-52 bg-white dark:bg-dark-950 border-r border-gray-200 dark:border-dark-800 flex flex-col h-full">
    <!-- 헤더 -->
    <div class="p-4">
      <h1 class="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
        <svg class="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
        Codebase Q&A
      </h1>
    </div>

    <!-- 대화 초기화 버튼 -->
    <div class="px-3 mb-2">
      <button
        @click="clearChat"
        class="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-100 dark:bg-dark-800 hover:bg-gray-200 dark:hover:bg-dark-700 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
        Clear Chat
      </button>
    </div>

    <!-- 프로젝트 섹션 -->
    <div class="flex-1 overflow-y-auto px-3">
      <div class="text-xs font-medium text-gray-500 dark:text-gray-500 uppercase tracking-wider mb-3">
        Projects
      </div>

      <!-- 인덱싱 진행률 -->
      <div
        v-if="chatStore.indexProgress.is_indexing"
        class="mb-3 p-3 bg-blue-900/20 border border-blue-800/50 rounded-lg"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-blue-400 font-medium">
            {{ chatStore.indexProgress.project }}
          </span>
          <div class="flex items-center gap-2">
            <span class="text-xs text-blue-300">
              {{ chatStore.indexProgress.percent }}%
            </span>
            <!-- 취소 버튼 -->
            <button
              @click="handleCancel"
              :disabled="isCancelling"
              class="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all"
              title="인덱싱 취소"
            >
              <svg v-if="!isCancelling" class="w-3 h-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <svg v-else class="w-3 h-3 text-red-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
              </svg>
            </button>
          </div>
        </div>
        <div class="w-full bg-gray-200 dark:bg-dark-700 rounded-full h-1.5 mb-1">
          <div
            class="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
            :style="{ width: `${chatStore.indexProgress.percent}%` }"
          ></div>
        </div>
        <div class="text-xs text-gray-500">
          {{ getStageLabel(chatStore.indexProgress.stage) }}
          ({{ chatStore.indexProgress.current }}/{{ chatStore.indexProgress.total }})
        </div>
      </div>

      <!-- 프로젝트 목록 -->
      <div class="space-y-1">
        <!-- 인덱싱된 프로젝트 -->
        <div
          v-for="project in chatStore.indexedProjects"
          :key="project.project"
          class="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-100 dark:bg-dark-800/50 hover:bg-gray-200 dark:hover:bg-dark-800 transition-colors group"
        >
          <!-- 체크 아이콘 -->
          <svg class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>

          <div class="flex-1 min-w-0">
            <div class="text-sm text-gray-900 dark:text-white font-medium truncate">{{ project.project }}</div>
            <div class="text-xs text-gray-500">{{ project.chunks.toLocaleString() }} chunks</div>
          </div>

          <!-- 삭제 버튼 -->
          <button
            @click.stop="confirmDelete(project)"
            class="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-all"
            title="프로젝트 삭제"
          >
            <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>

        <!-- 미인덱싱 프로젝트 -->
        <div
          v-for="project in unindexedProjects"
          :key="project"
          @click="indexUnindexed(project)"
          class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-200 dark:hover:bg-dark-800 cursor-pointer transition-colors"
        >
          <!-- 빈 원 아이콘 -->
          <div class="w-4 h-4 rounded-full border-2 border-gray-400 dark:border-gray-600 shrink-0"></div>

          <div class="flex-1 min-w-0">
            <div class="text-sm text-gray-500 dark:text-gray-400 truncate">{{ project }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 프로젝트 추가 버튼 -->
    <div class="p-3">
      <button
        @click="showModal = true"
        class="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Add Project
      </button>
    </div>

    <!-- 인덱싱 모달 -->
    <Teleport to="body">
      <div
        v-if="showModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="closeModal"
      >
        <div class="bg-white dark:bg-dark-800 rounded-xl p-6 w-full max-w-md mx-4 border border-gray-200 dark:border-dark-600 shadow-xl">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">프로젝트 인덱싱</h2>

          <div class="space-y-4">
            <!-- 폴더 브라우저 -->
            <div v-if="showBrowser" class="border border-gray-300 dark:border-dark-600 rounded-lg overflow-hidden">
              <!-- 현재 경로 -->
              <div class="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-dark-700 border-b border-gray-300 dark:border-dark-600">
                <button
                  v-if="browserParent"
                  @click="goToParent"
                  class="p-1 hover:bg-gray-200 dark:hover:bg-dark-600 rounded"
                  title="상위 폴더"
                >
                  <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span class="text-xs text-gray-600 dark:text-gray-400 truncate flex-1">{{ browserPath }}</span>
              </div>

              <!-- 디렉토리 목록 -->
              <div class="max-h-48 overflow-y-auto">
                <div v-if="browserLoading" class="p-4 text-center text-gray-500 text-sm">
                  로딩 중...
                </div>
                <div v-else-if="browserDirs.length === 0" class="p-4 text-center text-gray-500 text-sm">
                  하위 폴더가 없습니다
                </div>
                <div v-else>
                  <div
                    v-for="dir in browserDirs"
                    :key="dir.path"
                    class="flex items-center gap-2 px-3 py-2 hover:bg-gray-100 dark:hover:bg-dark-700 cursor-pointer border-b border-gray-200 dark:border-dark-700 last:border-b-0"
                  >
                    <!-- 폴더 아이콘 -->
                    <svg class="w-4 h-4 text-yellow-500 shrink-0" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M10 4H4a2 2 0 00-2 2v12a2 2 0 002 2h16a2 2 0 002-2V8a2 2 0 00-2-2h-8l-2-2z" />
                    </svg>
                    <span
                      @click="selectFolder(dir)"
                      class="text-sm text-gray-900 dark:text-white flex-1 truncate hover:text-blue-500"
                    >
                      {{ dir.name }}
                    </span>
                    <!-- 하위 폴더 보기 -->
                    <button
                      @click="loadDirectory(dir.path)"
                      class="p-1 hover:bg-gray-200 dark:hover:bg-dark-600 rounded"
                      title="하위 폴더 보기"
                    >
                      <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 코드 경로 -->
            <div v-else>
              <label class="block text-sm text-gray-600 dark:text-gray-400 mb-2">코드 경로</label>
              <div class="flex gap-2">
                <input
                  v-model="indexPath"
                  type="text"
                  placeholder="/Users/gcpark/code/프로젝트명"
                  :disabled="isIndexing"
                  class="flex-1 px-4 py-2.5 bg-gray-50 dark:bg-dark-900 border border-gray-300 dark:border-dark-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm disabled:opacity-50"
                />
                <button
                  @click="openBrowser"
                  :disabled="isIndexing"
                  class="px-3 py-2.5 bg-gray-200 dark:bg-dark-700 hover:bg-gray-300 dark:hover:bg-dark-600 rounded-lg disabled:opacity-50 transition-colors"
                  title="폴더 선택"
                >
                  <svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                </button>
              </div>
            </div>

            <div>
              <label class="block text-sm text-gray-600 dark:text-gray-400 mb-2">
                프로젝트 이름 <span class="text-gray-400">(선택)</span>
              </label>
              <input
                v-model="projectName"
                type="text"
                placeholder="비워두면 폴더명 사용"
                :disabled="isIndexing"
                class="w-full px-4 py-2.5 bg-gray-50 dark:bg-dark-900 border border-gray-300 dark:border-dark-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 text-sm disabled:opacity-50"
              />
            </div>

            <!-- 인덱싱 진행률 (모달 내) -->
            <div v-if="isIndexing && chatStore.indexProgress.is_indexing" class="space-y-2">
              <div class="flex items-center justify-between text-sm">
                <span class="text-gray-400">{{ getStageLabel(chatStore.indexProgress.stage) }}</span>
                <div class="flex items-center gap-2">
                  <span class="text-blue-400">{{ chatStore.indexProgress.percent }}%</span>
                  <!-- 취소 버튼 -->
                  <button
                    @click="handleCancel"
                    :disabled="isCancelling"
                    class="px-2 py-0.5 text-xs bg-red-600 hover:bg-red-700 disabled:bg-red-900 rounded text-white transition-colors"
                  >
                    {{ isCancelling ? '취소 중...' : '취소' }}
                  </button>
                </div>
              </div>
              <div class="w-full bg-gray-200 dark:bg-dark-700 rounded-full h-2">
                <div
                  class="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  :style="{ width: `${chatStore.indexProgress.percent}%` }"
                ></div>
              </div>
              <div class="text-xs text-gray-500 text-center">
                {{ chatStore.indexProgress.current }} / {{ chatStore.indexProgress.total }}
              </div>
            </div>

            <!-- 에러 메시지 -->
            <div v-if="indexError" class="p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
              {{ indexError }}
            </div>

            <!-- 결과 메시지 -->
            <div v-if="indexResult" class="p-3 bg-green-900/30 border border-green-800 rounded-lg text-green-400 text-sm">
              <div class="font-medium">{{ indexResult.message }}</div>
              <div class="text-xs mt-1 text-green-500">
                파일: {{ indexResult.indexed_files }}개 · 청크: {{ indexResult.chunks }}개
              </div>
            </div>

            <div class="flex gap-3 pt-2">
              <button
                @click="closeModal"
                :disabled="isIndexing"
                class="flex-1 px-4 py-2.5 bg-gray-200 dark:bg-dark-700 hover:bg-gray-300 dark:hover:bg-dark-600 disabled:opacity-50 rounded-lg text-gray-900 dark:text-white text-sm transition-colors"
              >
                닫기
              </button>
              <button
                @click="handleIndex"
                :disabled="isIndexing"
                class="flex-1 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 disabled:cursor-not-allowed rounded-lg text-white text-sm transition-colors flex items-center justify-center gap-2"
              >
                <svg v-if="isIndexing" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ isIndexing ? '인덱싱 중...' : '인덱싱 시작' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 삭제 확인 모달 -->
    <Teleport to="body">
      <div
        v-if="showDeleteModal"
        class="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
        @click.self="closeDeleteModal"
      >
        <div class="bg-white dark:bg-dark-800 rounded-xl p-6 w-full max-w-sm mx-4 border border-gray-200 dark:border-dark-600 shadow-xl">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">프로젝트 삭제</h2>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            <strong class="text-gray-900 dark:text-white">{{ deleteTarget?.project }}</strong> 프로젝트를 삭제하시겠습니까?
            <br>
            <span class="text-red-500">이 작업은 되돌릴 수 없습니다.</span>
          </p>

          <div class="flex gap-3">
            <button
              @click="closeDeleteModal"
              :disabled="isDeleting"
              class="flex-1 px-4 py-2.5 bg-gray-200 dark:bg-dark-700 hover:bg-gray-300 dark:hover:bg-dark-600 disabled:opacity-50 rounded-lg text-gray-900 dark:text-white text-sm transition-colors"
            >
              취소
            </button>
            <button
              @click="handleDelete"
              :disabled="isDeleting"
              class="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 disabled:bg-red-900 disabled:cursor-not-allowed rounded-lg text-white text-sm transition-colors flex items-center justify-center gap-2"
            >
              <svg v-if="isDeleting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ isDeleting ? '삭제 중...' : '삭제' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>
