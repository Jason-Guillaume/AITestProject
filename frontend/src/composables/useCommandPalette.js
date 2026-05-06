import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

/**
 * 全局 Ctrl+K / Cmd+K：捕获阶段拦截，避免浏览器默认行为。
 * 在公开路由（如登录）或无 token 时不响应。
 *
 * @param {{ toggle: () => void }} opts
 */
export function useCommandPaletteShortcut({ toggle }) {
  const route = useRoute()

  function onWindowKeydown(e) {
    if (route.meta?.public === true) return
    if (!localStorage.getItem('token')) return
    if ((e.ctrlKey || e.metaKey) && e.key?.toLowerCase() === 'k') {
      e.preventDefault()
      e.stopPropagation()
      toggle()
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', onWindowKeydown, true)
  })
  onUnmounted(() => {
    window.removeEventListener('keydown', onWindowKeydown, true)
  })
}
