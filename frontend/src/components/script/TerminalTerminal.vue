<template>
  <div
    ref="wrapperRef"
    class="terminal-terminal"
  >
    <div
      ref="hostRef"
      class="terminal-terminal__host"
    />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const props = defineProps<{
  /** 为 true 时（父级「终端」Tab 激活）才执行 fit，避免隐藏状态下错误测量 */
  fitWhenActive: boolean
}>()

const wrapperRef = ref<HTMLElement | null>(null)
const hostRef = ref<HTMLElement | null>(null)

let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let resizeObserver: ResizeObserver | null = null

const cyberTheme = {
  foreground: '#e2e8f0',
  background: 'rgba(255, 255, 255, 0.03)',
  cursor: '#00f0ff',
  cursorAccent: '#0a1628',
  selectionBackground: 'rgba(0, 240, 255, 0.18)',
  black: '#0d1117',
  red: '#ff003c',
  green: '#00ff9f',
  yellow: '#ffe14a',
  blue: '#2bb0ff',
  magenta: '#ff2bd6',
  cyan: '#00f0ff',
  white: '#f1f5f9',
  brightBlack: '#64748b',
  brightRed: '#ff4d6d',
  brightGreen: '#5dffbf',
  brightYellow: '#fff566',
  brightBlue: '#5ccfff',
  brightMagenta: '#ff7ae8',
  brightCyan: '#7dfff8',
  brightWhite: '#ffffff',
} as const

function tryFit() {
  if (!props.fitWhenActive || !fitAddon || !term) return
  const w = wrapperRef.value
  if (!w || w.clientWidth < 2 || w.clientHeight < 2) return
  try {
    fitAddon.fit()
  } catch {
    /* 布局尚未稳定时忽略 */
  }
}

function scheduleFit() {
  if (!props.fitWhenActive) return
  requestAnimationFrame(() => {
    requestAnimationFrame(() => tryFit())
  })
}

/** 写入一段日志（支持 ANSI 转义序列）；若末尾无换行则补 \r\n */
function writeLog(message: string) {
  if (!term) return
  term.write(message)
  if (!/\n$/.test(message)) {
    term.write('\r\n')
  }
}

defineExpose({
  writeLog,
  /** 父组件可在 Tab 切换后主动触发一次测量 */
  fit: tryFit,
})

onMounted(() => {
  const host = hostRef.value
  if (!host) return

  term = new Terminal({
    allowTransparency: true,
    convertEol: true,
    disableStdin: true,
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, ui-monospace, monospace",
    fontSize: 12,
    lineHeight: 1.28,
    cursorBlink: true,
    cursorStyle: 'bar',
    cursorWidth: 2,
    theme: { ...cyberTheme },
    scrollback: 4000,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(host)

  resizeObserver = new ResizeObserver(() => {
    if (props.fitWhenActive) scheduleFit()
  })
  if (wrapperRef.value) {
    resizeObserver.observe(wrapperRef.value)
  }

  window.addEventListener('resize', scheduleFit)
  if (props.fitWhenActive) scheduleFit()
})

watch(
  () => props.fitWhenActive,
  (active) => {
    if (active) scheduleFit()
  },
  { flush: 'post' },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', scheduleFit)
  resizeObserver?.disconnect()
  resizeObserver = null
  term?.dispose()
  term = null
  fitAddon = null
})
</script>

<style scoped>
.terminal-terminal {
  width: 100%;
  min-height: 160px;
  height: 100%;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  border: 1px solid rgba(0, 240, 255, 0.12);
  box-sizing: border-box;
  overflow: hidden;
  background: transparent;
}

.terminal-terminal__host {
  flex: 1;
  min-height: 0;
  min-width: 0;
}

/* 赛博透明底 + 弱化默认白底 */
.terminal-terminal :deep(.xterm) {
  height: 100%;
  padding: 4px 6px;
}

.terminal-terminal :deep(.xterm-viewport),
.terminal-terminal :deep(.xterm-screen) {
  background-color: transparent !important;
}

.terminal-terminal :deep(.xterm .xterm-scrollable) {
  background: transparent;
}
</style>
