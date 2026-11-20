/** 暗色模式切换：class 策略 + localStorage 持久化。 */
export const useDarkMode = () => {
  const isDark = useState<boolean>('dark-mode', () => false)

  const apply = () => {
    if (import.meta.client) {
      document.documentElement.classList.toggle('dark', isDark.value)
    }
  }

  const toggle = () => {
    isDark.value = !isDark.value
    if (import.meta.client) {
      localStorage.setItem('yuxm-theme', isDark.value ? 'dark' : 'light')
    }
    apply()
  }

  const init = () => {
    if (import.meta.client) {
      const saved = localStorage.getItem('yuxm-theme')
      isDark.value = saved ? saved === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches
      apply()
    }
  }

  return { isDark, toggle, init }
}
