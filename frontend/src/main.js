import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'

import App from './App.vue'
import './style.css'

// highlight.js 스타일
import 'highlight.js/styles/github-dark.css'

// 라우터 설정
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'chat',
      component: () => import('./views/ChatView.vue'),
    },
  ],
})

// Pinia 설정
const pinia = createPinia()
const app = createApp(App)
app.use(pinia)

// 테마 초기화 (마운트 전에 실행해 플래시 방지)
import { useThemeStore } from './stores/theme'
useThemeStore().init()

app.use(router)
app.mount('#app')
