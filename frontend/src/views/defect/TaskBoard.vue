<template>
  <div class="board-page task-board--sci cyber-page">
    <div class="board-layout">
      <!-- 三列看板 -->
      <div class="board-columns">
        <div class="board-col" v-for="col in columns" :key="col.key" :class="`board-col--${col.key}`">
          <div class="col-header" :class="`col-header--${col.key}`">
            <span class="col-title">{{ col.label }}</span>
            <span class="col-count">{{ col.tasks.length }}</span>
          </div>
          <div class="col-body">
            <div v-if="!col.tasks.length" class="col-empty">
              <el-empty description="暂无缺陷" :image-size="56" />
            </div>
            <div
              class="task-card"
              v-for="task in col.tasks"
              :key="task.id"
              draggable="true"
              @dragstart="onDragStart(task, col.key)"
              @dragover.prevent
              @drop="onDrop(col.key)"
            >
              <div class="task-card__header">
                <el-tag :type="severityTag(task.severity)" size="small">{{ severityLabel(task.severity) }}</el-tag>
                <span class="task-id">{{ task.defect_no }}</span>
              </div>
              <div class="task-title">{{ task.defect_name || task.task_title }}</div>
              <div class="task-desc" v-if="task.task_desc">{{ task.task_desc }}</div>
              <div class="task-footer">
                <span class="task-assignee">处理人：{{ task.handler_name || task.assignee_name || '-' }}</span>
                <span class="task-footer__right">
                  <el-button link type="primary" size="small" @click.stop="router.push(`/defect/detail/${task.id}`)">详情</el-button>
                  <span class="task-date">{{ formatDate(task.update_time) }}</span>
                </span>
              </div>
            </div>

            <button type="button" class="add-card-btn" @click="addTask(col)">
              <el-icon class="add-card-btn__icon"><Plus /></el-icon>
              <span class="add-card-btn__text">在此列新增缺陷</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧统计 -->
      <aside class="board-sidebar">
        <el-card class="board-widget-card" shadow="never">
          <template #header>
            <span class="board-widget-card__title">缺陷严重程度统计</span>
          </template>
          <div class="board-widget-card__body board-widget-card__body--chart">
            <div ref="pieEl" class="board-chart-host" />
          </div>
        </el-card>
        <el-card class="board-widget-card board-widget-card--table" shadow="never">
          <template #header>
            <span class="board-widget-card__title">版本发布计划</span>
          </template>
          <div class="board-widget-card__body">
            <el-table class="sidebar-table--sci admin-data-table" :data="releasePlans" size="small">
              <el-table-column prop="version_no" label="版本" min-width="72" width="72" align="left" show-overflow-tooltip />
              <el-table-column prop="project_name" label="产品" min-width="88" align="left" show-overflow-tooltip />
              <el-table-column label="状态" width="76" align="center">
                <template #default="{ row }">
                  <el-tag :type="releaseTag(row.status)" size="small">{{ releaseLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="日期" min-width="104" width="104" align="center" class-name="col-datetime">
                <template #default="{ row }">{{ formatDate(row.release_date) }}</template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无发布计划" :image-size="64" />
              </template>
            </el-table>
          </div>
        </el-card>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getReleasesApi } from '@/api/project'
import { getDefectsApi, updateDefectApi } from '@/api/defect'

const router = useRouter()
const pieEl = ref(null)
const releasePlans = ref([])
const dragging = ref(null)
const draggingFrom = ref(null)

/** 看板列：待处理=新缺陷(1)，处理中=2，已处理=已拒绝/已关闭(3/4) */
const columns = ref([
  { key: 'todo', statuses: [1], label: '待处理', tasks: [] },
  { key: 'doing', statuses: [2], label: '处理中', tasks: [] },
  { key: 'done', statuses: [3, 4], label: '已处理', tasks: [] },
])

function severityLabel(v) { return { 1: '致命', 2: '严重', 3: '一般', 4: '建议' }[v] || '未知' }
function severityTag(v) { return { 1: 'danger', 2: 'warning', 3: '', 4: 'info' }[v] || '' }
function releaseLabel(v) { return { 1: '待发布', 2: '已发布', 3: '已取消' }[v] || '-' }
function releaseTag(v) { return { 1: 'warning', 2: 'success', 3: 'info' }[v] || '' }
function formatDate(dt) { return dt ? dt.slice(0, 10) : '-' }

function onDragStart(task, fromColKey) {
  dragging.value = task
  draggingFrom.value = fromColKey
}

function colIndexByStatus(status) {
  return columns.value.findIndex((c) => c.statuses.includes(Number(status)))
}

function targetStatusForColumn(col) {
  if (col.key === 'todo') return 1
  if (col.key === 'doing') return 2
  return 4
}

async function onDrop(toColKey) {
  const task = dragging.value
  const fromKey = draggingFrom.value
  if (!task || !fromKey || fromKey === toColKey) {
    dragging.value = null
    draggingFrom.value = null
    return
  }
  const fromCol = columns.value.find((c) => c.key === fromKey)
  const toCol = columns.value.find((c) => c.key === toColKey)
  if (!fromCol || !toCol) return
  const newStatus = targetStatusForColumn(toCol)
  const prevStatus = task.status
  fromCol.tasks = fromCol.tasks.filter((t) => t.id !== task.id)
  task.status = newStatus
  toCol.tasks.push(task)
  try {
    await updateDefectApi(task.id, { status: newStatus })
  } catch {
    task.status = prevStatus
    toCol.tasks = toCol.tasks.filter((t) => t.id !== task.id)
    fromCol.tasks.push(task)
    ElMessage.error('更新状态失败，请重试')
  }
  dragging.value = null
  draggingFrom.value = null
  await nextTick()
  initPie()
}

function addTask(col) {
  const q = col.key === 'todo' ? '' : `?defaultStatus=${targetStatusForColumn(col)}`
  router.push(`/defect/detail${q}`)
}

function normalizeDefectList(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

async function loadData() {
  columns.value.forEach((col) => {
    col.tasks = []
  })
  try {
    const { data } = await getDefectsApi({ page_size: 500 })
    const defects = normalizeDefectList(data)
    defects.forEach((d) => {
      const idx = colIndexByStatus(d.status)
      if (idx >= 0) columns.value[idx].tasks.push(d)
    })
  } catch {
    ElMessage.error('加载缺陷看板失败')
  }

  try {
    const { data } = await getReleasesApi({ page_size: 50 })
    const rows = normalizeDefectList(data)
    releasePlans.value = rows.slice(0, 8)
  } catch {
    releasePlans.value = []
  }

  await nextTick()
  initPie()
}

function initPie() {
  if (!pieEl.value) return
  const existed = echarts.getInstanceByDom(pieEl.value)
  if (existed) existed.dispose()
  const counts = { 1: 0, 2: 0, 3: 0, 4: 0 }
  columns.value.forEach((col) => {
    col.tasks.forEach((t) => {
      if (counts[t.severity] !== undefined) counts[t.severity] += 1
    })
  })
  const chart = echarts.init(pieEl.value)
  const total = (counts[1] || 0) + (counts[2] || 0) + (counts[3] || 0) + (counts[4] || 0)
  chart.setOption({
    title:
      total === 0
        ? {
            text: '暂无分布数据',
            left: 'center',
            top: 'middle',
            textStyle: { color: 'rgba(255,255,255,0.45)', fontSize: 13, fontWeight: 400 },
          }
        : { show: false },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(20, 28, 47, 0.92)',
      borderColor: 'rgba(0, 216, 255, 0.35)',
      textStyle: { color: 'rgba(255,255,255,0.9)', fontSize: 12 },
    },
    legend: {
      orient: 'horizontal',
      left: 'center',
      bottom: 4,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 14,
      textStyle: { fontSize: 11, color: 'rgba(255,255,255,0.72)' },
    },
    series: [{
      type: 'pie',
      radius: ['42%', '62%'],
      center: ['50%', '44%'],
      label: { show: false },
      data: [
        { value: counts[1] || 0, name: '致命', itemStyle: { color: '#ff3d6a' } },
        { value: counts[2] || 0, name: '严重', itemStyle: { color: '#ff9f1a' } },
        { value: counts[3] || 0, name: '一般', itemStyle: { color: '#00d8ff' } },
        { value: counts[4] || 0, name: '建议', itemStyle: { color: '#3dff9c' } },
      ],
    }],
  })
}

onMounted(loadData)
</script>

<style scoped>
.task-board--sci.board-page {
  height: 100%;
  background: transparent;
}

.board-layout {
  display: flex;
  gap: 20px;
  height: 100%;
  min-height: 0;
}
.board-columns {
  flex: 1;
  display: flex;
  gap: 16px;
  overflow-x: auto;
  min-width: 0;
  padding-bottom: 4px;
}

.task-board--sci .board-col {
  flex: 1;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
}

/* 列区分色：略亮于主背景 #12121a 类，保持深色高级感 */
.task-board--sci .board-col--todo {
  background: #1e1e2d;
}
.task-board--sci .board-col--doing {
  background: #222232;
}
.task-board--sci .board-col--done {
  background: #1a1a28;
}

.task-board--sci .col-header {
  position: relative;
  padding: 14px 16px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  background: rgba(8, 12, 22, 0.55);
  color: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.task-board--sci .col-header::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 10px 10px 0 0;
}

.task-board--sci .col-header--todo::before {
  background: linear-gradient(90deg, #ff1a5c, #ff7eb3);
  box-shadow:
    0 0 12px rgba(255, 26, 92, 0.75),
    0 0 24px rgba(255, 80, 150, 0.35);
}

.task-board--sci .col-header--todo .col-title {
  text-shadow: 0 0 18px rgba(255, 90, 130, 0.45);
}

.task-board--sci .col-header--doing::before {
  background: linear-gradient(90deg, #ffb020, #ff7300);
  box-shadow:
    0 0 12px rgba(255, 176, 32, 0.7),
    0 0 22px rgba(255, 115, 0, 0.35);
}

.task-board--sci .col-header--doing .col-title {
  text-shadow: 0 0 16px rgba(255, 160, 48, 0.4);
}

.task-board--sci .col-header--done::before {
  background: linear-gradient(90deg, #00e676, #00d8ff);
  box-shadow:
    0 0 12px rgba(0, 230, 118, 0.55),
    0 0 22px rgba(0, 216, 255, 0.4);
}

.task-board--sci .col-header--done .col-title {
  text-shadow: 0 0 14px rgba(0, 216, 255, 0.45);
}

.task-board--sci .col-count {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.78);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.task-board--sci .col-body {
  flex: 1;
  overflow-y: auto;
  min-height: 120px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-board--sci .task-card {
  background: rgba(40, 50, 70, 0.6);
  border-radius: 8px;
  padding: 12px;
  cursor: grab;
  border: 1px solid rgba(255, 255, 255, 0.07);
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease;
}

.task-board--sci .task-card:hover {
  border-color: rgba(0, 216, 255, 0.4);
  box-shadow:
    0 0 0 1px rgba(0, 216, 255, 0.15),
    0 4px 22px rgba(0, 216, 255, 0.14),
    0 0 28px rgba(0, 216, 255, 0.08);
}

.task-board--sci .task-card:active {
  cursor: grabbing;
}

.task-board--sci .task-card__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.task-board--sci .task-id { font-size: 11px; color: rgba(255, 255, 255, 0.42); }
.task-board--sci .task-title { font-size: 13px; color: rgba(255, 255, 255, 0.94); font-weight: 500; margin-bottom: 4px; }
.task-board--sci .task-desc {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.52);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.task-board--sci .task-footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: rgba(255, 255, 255, 0.45); }
.task-footer__right { display: flex; align-items: center; gap: 6px; }

.task-board--sci .add-card-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  min-height: 56px;
  margin: 0;
  padding: 12px 14px;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  color: rgba(0, 216, 255, 0.75);
  cursor: pointer;
  border-radius: 8px;
  border: 1px dashed rgba(0, 216, 255, 0.35);
  background: rgba(0, 216, 255, 0.04);
  transition:
    color 0.2s ease,
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.15s ease;
}

.task-board--sci .add-card-btn__icon {
  font-size: 18px;
}

.task-board--sci .add-card-btn__text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.02em;
}

.task-board--sci .add-card-btn:hover {
  color: #5cefff;
  border-color: rgba(0, 216, 255, 0.65);
  background: rgba(0, 216, 255, 0.1);
  box-shadow: 0 0 20px rgba(0, 216, 255, 0.15);
}

.task-board--sci .add-card-btn:hover .add-card-btn__text {
  color: rgba(255, 255, 255, 0.72);
}

.task-board--sci .add-card-btn:active {
  transform: scale(0.99);
}

.board-sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.task-board--sci .board-widget-card {
  border-radius: 10px;
  border: 1px solid rgba(0, 255, 255, 0.12);
  background: rgba(20, 28, 47, 0.75) !important;
  --el-card-bg-color: rgba(20, 28, 47, 0.75);
}

.task-board--sci .board-widget-card :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(8, 12, 22, 0.4);
}

.task-board--sci .board-widget-card :deep(.el-card__body) {
  padding: 0;
}

.task-board--sci .board-widget-card__title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  letter-spacing: 0.02em;
}

.task-board--sci .board-widget-card__body {
  padding: 18px 20px 20px;
}

.task-board--sci .board-widget-card__body--chart {
  padding-bottom: 12px;
}

.task-board--sci .board-chart-host {
  width: 100%;
  height: 200px;
}

.task-board--sci .board-widget-card--table .board-widget-card__body {
  padding: 4px 12px 16px;
}

.task-board--sci :deep(.sidebar-table--sci) {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(255, 255, 255, 0.05);
  --el-table-row-hover-bg-color: rgba(0, 255, 255, 0.06);
  --el-table-border-color: transparent;
  --el-table-text-color: rgba(255, 255, 255, 0.85);
  --el-table-header-text-color: rgba(255, 255, 255, 0.7);
}

.task-board--sci :deep(.sidebar-table--sci .el-table__inner-wrapper::before),
.task-board--sci :deep(.sidebar-table--sci::before) {
  display: none;
}

.task-board--sci :deep(.sidebar-table--sci .el-table__header-wrapper th.el-table__cell) {
  background: rgba(255, 255, 255, 0.05) !important;
  border-right: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.task-board--sci :deep(.sidebar-table--sci .el-table__body-wrapper .el-table__body td.el-table__cell) {
  background: transparent !important;
  border-right: none !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.task-board--sci :deep(.sidebar-table--sci .el-table__body-wrapper .el-table__body tr:last-child td.el-table__cell) {
  border-bottom: none !important;
}

.task-board--sci .col-empty {
  padding: 8px 0 4px;
}

.task-board--sci .col-empty :deep(.el-empty__description) {
  margin-top: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.task-board--sci .col-empty :deep(.el-empty__image) {
  opacity: 0.85;
}

.task-board--sci :deep(.sidebar-table--sci .el-empty__description) {
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}
</style>
