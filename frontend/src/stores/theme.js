/**
 * Theme Store (Pinia)
 * 다크/라이트 모드 상태 및 localStorage 유지
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'theme'
const DARK = 'dark'
const LIGHT = 'light'

export const useThemeStore = defineStore('theme', () => {
  /** @type {import('vue').Ref<'dark'|'light'>} */
  const mode = ref('dark')

  const isDarkMode = ref(true)

  function setDark() {
    mode.value = DARK
    isDarkMode.value = true
    document.documentElement.classList.add('dark')
    document.documentElement.setAttribute('data-theme', DARK)
    localStorage.setItem(STORAGE_KEY, DARK)
  }

  function setLight() {
    mode.value = LIGHT
    isDarkMode.value = false
    document.documentElement.classList.remove('dark')
    document.documentElement.setAttribute('data-theme', LIGHT)
    localStorage.setItem(STORAGE_KEY, LIGHT)
  }

  function toggle() {
    if (isDarkMode.value) {
      setLight()
    } else {
      setDark()
    }
  }

  function init() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === LIGHT) {
      setLight()
    } else {
      setDark()
    }
  }

  return {
    mode,
    isDarkMode,
    toggle,
    setDark,
    setLight,
    init,
  }
})
