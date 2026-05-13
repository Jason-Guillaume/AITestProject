<template>
  <div
    ref="containerRef"
    class="monaco-editor-root"
  />
</template>

<script setup>
import {
  ref,
  shallowRef,
  watch,
  onMounted,
  onBeforeUnmount,
} from 'vue'
import '@/utils/monacoEnvironment.js'
import * as monaco from 'monaco-editor'
import { useCopilotStore } from '@/stores/copilotStore'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  language: {
    type: String,
    default: 'python',
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
  /** 为 false 时不向全局 Copilot 注册（只读预览等） */
  copilotEnabled: {
    type: Boolean,
    default: true,
  },
  /** 固定桥接 id；多编辑器时建议父组件传入稳定 id */
  copilotBridgeId: {
    type: String,
    default: '',
  },
  /** Copilot 上下文展示用 */
  copilotLabel: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const containerRef = ref(null)
const editor = shallowRef(null)
let suppressEmit = false
const copilotStore = useCopilotStore()
const resolvedBridgeId = ref('')

function normalizeLanguage(lang) {
  const l = String(lang || 'python').toLowerCase()
  const map = {
    py: 'python',
    python: 'python',
    js: 'javascript',
    ts: 'typescript',
    jsx: 'javascript',
    tsx: 'typescript',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    xml: 'xml',
    html: 'html',
    css: 'css',
    sh: 'shell',
    bash: 'shell',
  }
  return map[l] || l
}

onMounted(() => {
  monaco.editor.setTheme('vs-dark')

  const el = containerRef.value
  if (!el) return

  const ed = monaco.editor.create(el, {
    value: props.modelValue ?? '',
    language: normalizeLanguage(props.language),
    readOnly: props.readOnly,
    automaticLayout: true,
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
    minimap: { enabled: true },
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    tabSize: 4,
    padding: { top: 8, bottom: 8 },
  })

  editor.value = ed

  ed.onDidChangeModelContent(() => {
    if (suppressEmit) return
    emit('update:modelValue', ed.getValue())
  })

  if (props.copilotEnabled) {
    const bid =
      (props.copilotBridgeId && String(props.copilotBridgeId)) ||
      `monaco-${typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`
    resolvedBridgeId.value = bid
    copilotStore.registerBridge(bid, {
      getValue: () => ed.getValue(),
      setValue: (v) => {
        const next = v ?? ''
        suppressEmit = true
        ed.setValue(next)
        suppressEmit = false
        emit('update:modelValue', next)
      },
      insertAtCursor: (text) => {
        const sel = ed.getSelection()
        const range = sel
          ? new monaco.Range(
              sel.startLineNumber,
              sel.startColumn,
              sel.endLineNumber,
              sel.endColumn,
            )
          : ed.getModel()?.getFullModelRange()
        if (!range) return
        ed.executeEdits('copilot', [{ range, text: text ?? '', forceMoveMarkers: true }])
        ed.focus()
      },
      getLanguage: () => normalizeLanguage(props.language),
      isReadOnly: () => !!props.readOnly,
      getLabel: () => String(props.copilotLabel || '').trim() || '编辑器',
      focus: () => ed.focus(),
    })
    ed.onDidFocusEditorWidget(() => {
      copilotStore.setActiveBridgeId(bid)
    })
  }
})

onBeforeUnmount(() => {
  if (props.copilotEnabled && resolvedBridgeId.value) {
    copilotStore.unregisterBridge(resolvedBridgeId.value)
    resolvedBridgeId.value = ''
  }
  const ed = editor.value
  if (ed) {
    ed.dispose()
    editor.value = null
  }
})

watch(
  () => props.modelValue,
  (v) => {
    const ed = editor.value
    if (!ed) return
    const next = v ?? ''
    if (ed.getValue() === next) return
    suppressEmit = true
    ed.setValue(next)
    suppressEmit = false
  },
)

watch(
  () => props.language,
  (lang) => {
    const ed = editor.value
    const model = ed?.getModel?.()
    if (model) {
      monaco.editor.setModelLanguage(model, normalizeLanguage(lang))
    }
  },
)

watch(
  () => props.readOnly,
  (ro) => {
    editor.value?.updateOptions({ readOnly: ro })
  },
)
</script>

<style scoped>
.monaco-editor-root {
  width: 100%;
  height: 100%;
  min-height: 200px;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid rgba(0, 216, 255, 0.18);
  box-sizing: border-box;
  background: #1e1e1e;
}
</style>
