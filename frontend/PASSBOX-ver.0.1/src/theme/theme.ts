import { useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark'
const KEY = 'passbox-theme'

function readStored(): ThemeMode | null {
  try {
    const v = localStorage.getItem(KEY)
    return v === 'dark' || v === 'light' ? v : null
  } catch {
    return null
  }
}

function systemPrefersDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

export function applyTheme(mode: ThemeMode) {
  document.documentElement.dataset.theme = mode
  document.documentElement.style.colorScheme = mode
  window.dispatchEvent(new CustomEvent('passbox-theme', { detail: mode }))
}

// 첫 페인트 전에 호출해 깜빡임 없이 저장된(또는 시스템) 테마를 적용합니다.
export function initTheme() {
  applyTheme(readStored() ?? (systemPrefersDark() ? 'dark' : 'light'))
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'))

  useEffect(() => {
    const onChange = (e: Event) => setMode((e as CustomEvent<ThemeMode>).detail)
    window.addEventListener('passbox-theme', onChange)
    return () => window.removeEventListener('passbox-theme', onChange)
  }, [])

  const setTheme = (next: ThemeMode) => {
    try { localStorage.setItem(KEY, next) } catch { /* storage unavailable */ }
    applyTheme(next)
  }
  return { mode, setTheme, toggle: () => setTheme(mode === 'dark' ? 'light' : 'dark') }
}
