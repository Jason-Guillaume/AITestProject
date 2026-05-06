<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshLeft, Delete, CircleCheck } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const tableRef = ref(null)
const selectedRows = ref([])

const hasSelection = computed(() => selectedRows.value.length > 0)

function formatTime(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return String(iso)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return String(iso)
  }
}

function onSelectionChange(list) {
  selectedRows.value = list || []
}

async function loadTrash() {
  loading.value = true
  try {
    const { data } = await request.get('/assistant/ui-scripts/trash/')
    const list = data?.results ?? []
    rows.value = Array.isArray(list) ? list : []
    tableRef.value?.clearSelection()
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载回收站失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function onRestore(row) {
  try {
    await request.post(`/assistant/ui-scripts/${row.id}/restore/`)
    ElMessage.success('已还原')
    await loadTrash()
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || '还原失败'
    ElMessage.error(typeof msg === 'string' ? msg : '还原失败')
  }
}

async function onPurge(row) {
  try {
    await ElMessageBox.confirm(
      `确定永久抹除「${row.name}」吗？工作空间文件将删除且不可恢复。`,
      '永久抹除',
      { type: 'warning', confirmButtonText: '永久抹除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await request.post(`/assistant/ui-scripts/${row.id}/permanent_delete/`)
    ElMessage.success('已永久抹除')
    await loadTrash()
  } catch (e) {
    const msg = e?.response?.data?.error || e?.response?.data?.detail || e?.message || '操作失败'
    ElMessage.error(typeof msg === 'string' ? msg : '永久抹除失败')
  }
}

async function batchRestore() {
  const list = selectedRows.value
  if (!list.length) {
    ElMessage.warning('请先勾选要还原的脚本')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将选中的 ${list.length} 个脚本还原到列表？`,
      '批量还原',
      { type: 'info', confirmButtonText: '还原', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  let ok = 0
  let fail = 0
  for (const row of list) {
    try {
      await request.post(`/assistant/ui-scripts/${row.id}/restore/`)
      ok += 1
    } catch {
      fail += 1
    }
  }
  if (ok) ElMessage.success(`已还原 ${ok} 项${fail ? `，失败 ${fail} 项` : ''}`)
  else ElMessage.error('全部还原失败')
  await loadTrash()
}

async function batchPurge() {
  const list = selectedRows.value
  if (!list.length) {
    ElMessage.warning('请先勾选要永久抹除的脚本')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将永久删除选中的 ${list.length} 个脚本及其工作空间文件，不可恢复。确定继续？`,
      '批量永久抹除',
      { type: 'warning', confirmButtonText: '永久抹除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  let ok = 0
  let fail = 0
  for (const row of list) {
    try {
      await request.post(`/assistant/ui-scripts/${row.id}/permanent_delete/`)
      ok += 1
    } catch {
      fail += 1
    }
  }
  if (ok) ElMessage.success(`已永久抹除 ${ok} 项${fail ? `，失败 ${fail} 项` : ''}`)
  else ElMessage.error('全部抹除失败')
  await loadTrash()
}

onMounted(() => {
  loadTrash()
})
</script>

<template>
  <div class="ui-recycle-bin">
    <header class="ui-recycle-bin__head">
      <div>
        <h1 class="ui-recycle-bin__title">回收站 <span class="ui-recycle-bin__sub">Recycle Bin</span></h1>
        <p class="ui-recycle-bin__desc">已软删除的 UI 脚本（Node），可还原或永久抹除；支持批量操作。</p>
      </div>
      <div class="ui-recycle-bin__toolbar">
        <el-button
          type="success"
          plain
          :icon="CircleCheck"
          :disabled="!hasSelection"
          @click="batchRestore"
        >
          批量还原
        </el-button>
        <el-button
          type="danger"
          plain
          :icon="Delete"
          :disabled="!hasSelection"
          @click="batchPurge"
        >
          批量永久抹除
        </el-button>
        <el-button type="primary" plain :icon="RefreshLeft" :loading="loading" @click="loadTrash">
          刷新
        </el-button>
      </div>
    </header>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="rows"
      row-key="id"
      stripe
      border
      empty-text="回收站为空"
      class="ui-recycle-bin__table"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="48" fixed />
      <el-table-column prop="name" label="名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="original_path" label="原始路径" min-width="220" show-overflow-tooltip />
      <el-table-column label="删除时间" width="180">
        <template #default="{ row }">
          {{ formatTime(row.deleted_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="onRestore(row)">还原</el-button>
          <el-button link type="danger" @click="onPurge(row)">永久抹除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.ui-recycle-bin {
  padding: 16px 20px 24px;
  max-width: 1200px;
}
.ui-recycle-bin__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.ui-recycle-bin__title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}
.ui-recycle-bin__sub {
  font-size: 0.85rem;
  font-weight: 400;
  opacity: 0.75;
  margin-left: 8px;
}
.ui-recycle-bin__desc {
  margin: 6px 0 0;
  font-size: 13px;
  opacity: 0.8;
}
.ui-recycle-bin__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.ui-recycle-bin__table {
  width: 100%;
}
</style>
