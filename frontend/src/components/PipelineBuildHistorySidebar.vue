<template>
  <aside class="build-history" v-loading="loading">
    <div class="build-history__title">构建历史</div>
    <p class="build-history__hint">点击 #编号查看该次构建日志</p>
    <el-scrollbar max-height="calc(100vh - 220px)">
      <div v-if="!items.length && !loading" class="build-history__empty">暂无构建记录</div>
      <button
        v-for="row in items"
        :key="row.id"
        type="button"
        class="build-history__item"
        :class="{ 'is-active': modelValue === row.id }"
        @click="select(row.id)"
      >
        <span class="build-history__num">#{{ row.build_number }}</span>
        <el-tag :type="statusTag(row.status)" size="small" class="build-history__tag">
          {{ statusText(row.status) }}
        </el-tag>
        <span class="build-history__time">{{ formatTime(row.start_time) }}</span>
      </button>
    </el-scrollbar>
  </aside>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getPipelineBuildsApi } from '@/api/project'

export interface BuildRow {
  id: number
  build_number: number
  status: number
  start_time?: string
  end_time?: string | null
}

const props = defineProps<{
  pipelineId: number
  /** 当前选中的构建记录 ID（与控制台轮询的 build_id 一致） */
  modelValue: number | null
  /** 父组件在触发新构建后递增，以刷新列表 */
  refreshTrigger?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  /** 用户点击某条历史记录时触发（便于父组件重置控制台） */
  select: [id: number]
}>()

const loading = ref(false)
const items = ref<BuildRow[]>([])

function statusText(s: number) {
  const m: Record<number, string> = {
    0: '排队',
    1: '运行',
    2: '成功',
    3: '失败',
    4: '取消',
  }
  return m[s] ?? String(s)
}

function statusTag(s: number): 'info' | 'warning' | 'success' | 'danger' {
  if (s === 1) return 'warning'
  if (s === 2) return 'success'
  if (s === 3) return 'danger'
  return 'info'
}

function formatTime(t?: string | null) {
  if (!t) return '—'
  return t.slice(0, 16).replace('T', ' ')
}

function select(id: number) {
  emit('update:modelValue', id)
  emit('select', id)
}

async function fetchBuilds() {
  if (!props.pipelineId) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const { data } = await getPipelineBuildsApi(props.pipelineId, { limit: 80 })
    const raw = Array.isArray(data?.items) ? data.items : []
    items.value = raw as BuildRow[]
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.pipelineId, props.refreshTrigger ?? 0] as const,
  () => fetchBuilds(),
  { immediate: true }
)
</script>

<style scoped>
.build-history {
  width: 200px;
  flex-shrink: 0;
  padding: 10px 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--el-border-color);
  background: var(--el-fill-color-blank);
}

.build-history__title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--el-text-color-primary);
}

.build-history__hint {
  margin: 0 0 10px;
  font-size: 11px;
  line-height: 1.35;
  color: var(--el-text-color-secondary);
}

.build-history__empty {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 8px 4px;
}

.build-history__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  margin-bottom: 8px;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.build-history__item:hover {
  border-color: var(--el-color-primary-light-5);
}

.build-history__item.is-active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
}

.build-history__num {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.build-history__tag {
  transform: scale(0.92);
  transform-origin: left center;
}

.build-history__time {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}
</style>
