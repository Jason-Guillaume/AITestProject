/** 屏蔽浏览器默认右键菜单；不 stopPropagation，便于 el-dropdown trigger="contextmenu" 接收事件 */
export const vContextmenuBlockNative = {
  mounted(el) {
    const handler = (e) => {
      if (e.button === 2) e.preventDefault()
    }
    el.__ctxMenuBlockHandler = handler
    el.addEventListener('contextmenu', handler)
  },
  unmounted(el) {
    const h = el.__ctxMenuBlockHandler
    if (h) el.removeEventListener('contextmenu', h)
  },
}
