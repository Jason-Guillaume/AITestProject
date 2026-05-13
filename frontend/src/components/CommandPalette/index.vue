<template>
  <el-dialog
    v-model="visible"
    width="min(680px, 94vw)"
    append-to-body
    :z-index="5000"
    align-center
    class="command-palette-dialog"
    :show-close="false"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    destroy-on-close
    @opened="onDialogOpened"
    @closed="onDialogClosed"
  >
    <template #header />

    <div class="cp">
      <div
        class="cp-glow"
        aria-hidden="true"
      />

      <el-input
        ref="searchInputRef"
        v-model="query"
        class="cp-search"
        placeholder="输入指令或搜索…"
        clearable
        @keydown="onSearchKeydown"
      >
        <template #prefix>
          <span
            class="cp-search__icon"
            aria-hidden="true"
          >
            <svg
              viewBox="0 0 24 24"
              width="22"
              height="22"
            >
              <path
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                d="M10.5 18a7.5 7.5 0 100-15 7.5 7.5 0 000 15zM16.5 16.5L21 21"
              />
            </svg>
          </span>
        </template>
        <template #suffix>
          <span class="cp-search__hint">Esc 关闭</span>
        </template>
      </el-input>

      <p
        v-if="hintLine"
        class="cp-hint"
      >
        {{ hintLine }}
      </p>

      <ul
        ref="listRef"
        class="cp-list"
        role="listbox"
        :aria-activedescendant="activeId"
      >
        <li
          v-for="(cmd, idx) in filteredCommands"
          :id="`cp-item-${idx}`"
          :key="cmd.id"
          class="cp-item"
          :class="{ 'cp-item--active': idx === activeIndex }"
          role="option"
          :aria-selected="idx === activeIndex"
          @click="runCommand(cmd)"
          @mouseenter="activeIndex = idx"
        >
          <span class="cp-item__label">{{ cmd.label }}</span>
          <span
            v-if="cmd.badge"
            class="cp-item__badge"
          >{{ cmd.badge }}</span>
        </li>
        <li
          v-if="filteredCommands.length === 0"
          class="cp-empty"
        >
          没有匹配的指令
        </li>
      </ul>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { useCommandPaletteShortcut } from '@/composables/useCommandPalette'

const router = useRouter()
const workspaceStore = useWorkspaceStore()
const { projectOptions, envOptions, projectsLoading, environmentsLoading } = storeToRefs(workspaceStore)

const visible = ref(false)
const query = ref('')
const activeIndex = ref(0)
const searchInputRef = ref(null)
const listRef = ref(null)

const hintLine = computed(() => {
  if (projectsLoading.value || environmentsLoading.value) {
    return '正在同步工作区数据…'
  }
  return ''
})

function matchesQuery(text, q) {
  const hay = String(text || '').toLowerCase()
  const needle = String(q || '')
    .trim()
    .toLowerCase()
  if (!needle) return true
  return needle
    .split(/\s+/)
    .filter(Boolean)
    .every((part) => hay.includes(part))
}

const staticCommands = computed(() => {
  const items = [
    {
      id: 'nav-dashboard',
      label: '🏠 前往工作台',
      badge: '导航',
      keywords: 'dashboard 首页 工作台',
      run: () => router.push('/dashboard'),
    },
    {
      id: 'nav-automation-center',
      label: '📦 打开自动化指挥中心',
      badge: '导航',
      keywords: 'automation center script hub 脚本 指挥中心',
      run: () => router.push('/automation-center'),
    },
    {
      id: 'nav-webui',
      label: '🚀 执行 Web UI 自动化脚本',
      badge: '导航',
      keywords: 'webui playwright selenium 工作台',
      run: () => router.push({ name: 'WebUIScriptWorkbench' }),
    },
    {
      id: 'nav-agent-hub',
      label: '✨ 唤醒智能体中心',
      badge: '导航',
      keywords: 'agent ai 智能体',
      run: () => router.push({ name: 'AgentHub' }),
    },
    {
      id: 'nav-ai-assistant',
      label: '🤖 打开智能助手',
      badge: '导航',
      keywords: 'assistant 助手',
      run: () => router.push('/ai-assistant'),
    },
  ]
  return items
})

const workspaceCommands = computed(() => {
  const out = []
  for (const p of projectOptions.value || []) {
    const name = p?.project_name ?? p?.name ?? ''
    const id = p?.id
    out.push({
      id: `project-${id}`,
      label: `切换项目：${name || id}`,
      badge: '项目',
      keywords: `项目 project ${name}`,
      run: () => workspaceStore.setSelectedProjectId(id),
    })
  }
  for (const e of envOptions.value || []) {
    const name = e?.name ?? ''
    const id = e?.id
    out.push({
      id: `env-${id}`,
      label: `切换环境：${name || id}`,
      badge: '环境',
      keywords: `环境 environment env ${name}`,
      run: () => workspaceStore.setSelectedEnvironmentId(id),
    })
  }
  return out
})

const allCommands = computed(() => [...staticCommands.value, ...workspaceCommands.value])

const filteredCommands = computed(() => {
  const q = query.value
  return allCommands.value.filter((c) => {
    const blob = `${c.label} ${c.keywords || ''} ${c.badge || ''}`
    return matchesQuery(blob, q)
  })
})

const activeId = computed(() =>
  filteredCommands.value.length ? `cp-item-${activeIndex.value}` : undefined,
)

watch(filteredCommands, () => {
  activeIndex.value = 0
})

watch(visible, async (v) => {
  if (!v) return
  query.value = ''
  activeIndex.value = 0
  await workspaceStore.ensureWorkspaceContext()
})

function scrollActiveIntoView() {
  nextTick(() => {
    const root = listRef.value
    if (!root) return
    const el = root.querySelector(`#cp-item-${activeIndex.value}`)
    el?.scrollIntoView?.({ block: 'nearest' })
  })
}

function moveActive(delta) {
  const len = filteredCommands.value.length
  if (!len) return
  activeIndex.value = (activeIndex.value + delta + len) % len
  scrollActiveIntoView()
}

function onSearchKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    moveActive(1)
    return
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    moveActive(-1)
    return
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    const cmd = filteredCommands.value[activeIndex.value]
    if (cmd) runCommand(cmd)
  }
}

function runCommand(cmd) {
  try {
    cmd.run?.()
  } catch (err) {
    console.warn('[CommandPalette]', err)
  }
  visible.value = false
}

function onDialogOpened() {
  nextTick(() => {
    searchInputRef.value?.focus?.()
  })
}

function onDialogClosed() {
  query.value = ''
  activeIndex.value = 0
}

function toggle() {
  visible.value = !visible.value
}

useCommandPaletteShortcut({ toggle })
</script>

<style scoped>
.cp {
  position: relative;
  padding: 4px 2px 8px;
  --cp-cyan: #00d8ff;
  --cp-cyan-dim: color-mix(in srgb, var(--cp-cyan) 45%, #0a0f1e);
  --cp-bg: linear-gradient(165deg, #0d1424 0%, #121a2e 55%, #0f1728 100%);
}

.cp-glow {
  pointer-events: none;
  position: absolute;
  inset: -2px;
  border-radius: 14px;
  background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(0, 216, 255, 0.14), transparent 55%);
  opacity: 0.9;
}

.cp-search {
  position: relative;
  z-index: 1;
}

.cp-search :deep(.el-input__wrapper) {
  font-size: 1.15rem;
  min-height: 52px;
  padding-left: 14px;
  padding-right: 12px;
  border-radius: 12px;
  background: rgba(10, 16, 29, 0.92);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--cp-cyan) 22%, transparent),
    0 0 28px color-mix(in srgb, var(--cp-cyan) 12%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  border: none;
}

.cp-search :deep(.el-input__wrapper):hover {
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--cp-cyan) 35%, transparent),
    0 0 36px color-mix(in srgb, var(--cp-cyan) 16%, transparent),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.cp-search :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--cp-cyan) 55%, transparent),
    0 0 42px color-mix(in srgb, var(--cp-cyan) 22%, transparent),
    inset 0 0 20px color-mix(in srgb, var(--cp-cyan) 6%, transparent);
}

.cp-search :deep(.el-input__inner) {
  color: #e8eaef;
  font-weight: 500;
}

.cp-search :deep(.el-input__inner::placeholder) {
  color: rgba(156, 163, 184, 0.75);
}

.cp-search__icon {
  display: flex;
  color: var(--cp-cyan);
  margin-right: 4px;
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--cp-cyan) 40%, transparent));
}

.cp-search__hint {
  font-size: 11px;
  color: rgba(156, 163, 184, 0.85);
  letter-spacing: 0.02em;
  user-select: none;
}

.cp-hint {
  position: relative;
  z-index: 1;
  margin: 10px 4px 6px;
  font-size: 12px;
  color: rgba(0, 216, 255, 0.75);
}

.cp-list {
  position: relative;
  z-index: 1;
  list-style: none;
  margin: 12px 0 0;
  padding: 4px;
  max-height: min(52vh, 420px);
  overflow: auto;
  border-radius: 10px;
  background: rgba(8, 12, 22, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.cp-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  margin: 2px 0;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(232, 234, 239, 0.92);
  font-size: 14px;
  transition:
    background 0.15s ease,
    box-shadow 0.15s ease;
}

.cp-item:hover,
.cp-item--active {
  background: rgba(0, 216, 255, 0.1);
  box-shadow: inset 0 0 0 1px rgba(0, 216, 255, 0.18);
}

.cp-item__label {
  flex: 1;
  min-width: 0;
}

.cp-item__badge {
  flex-shrink: 0;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  color: rgba(0, 216, 255, 0.95);
  background: rgba(0, 216, 255, 0.1);
  border: 1px solid rgba(0, 216, 255, 0.22);
}

.cp-empty {
  padding: 28px 16px;
  text-align: center;
  color: rgba(156, 163, 184, 0.8);
  font-size: 13px;
}
</style>

<style>
/* 非 scoped：覆盖 Teleport 到 body 的对话框外壳 */
.command-palette-dialog.el-dialog {
  --el-dialog-bg-color: transparent;
  --el-dialog-box-shadow: none;
  background: transparent;
  padding: 0;
}

.command-palette-dialog .el-dialog__header {
  display: none;
}

.command-palette-dialog .el-dialog__body {
  padding: 0;
  border-radius: 16px;
  background: linear-gradient(165deg, #0d1424 0%, #121a2e 52%, #101827 100%);
  border: 1px solid rgba(0, 216, 255, 0.22);
  box-shadow:
    0 0 0 1px rgba(0, 216, 255, 0.08),
    0 24px 80px rgba(0, 0, 0, 0.55),
    0 0 60px rgba(0, 216, 255, 0.12);
}
</style>
