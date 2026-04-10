<template>
  <div class="report-detail cyber-page">
    <!-- 标题 -->
    <div class="detail-header">
      <div class="detail-header__left">
        <span class="report-id">{{ detail.id }}</span>
        <span class="report-name">{{ detail.report_name }}</span>
        <span class="update-tip">报告生成时间：{{ formatDate(detail.create_time) }}</span>
        <el-tag type="warning" size="small">进行中</el-tag>
      </div>
      <div class="detail-header__right">
        <el-button size="small" :disabled="!planLinkId" @click="router.push(`/test-plan/${planLinkId}`)">
          <el-icon><View /></el-icon> 查看测试计划
        </el-button>
        <el-button size="small"><el-icon><Download /></el-icon> 下载</el-button>
        <el-button size="small" type="danger" @click="onDelete"><el-icon><Delete /></el-icon> 删除</el-button>
      </div>
    </div>

    <!-- 概览 -->
    <div class="section-card">
      <div class="section-title">概览</div>
      <div class="overview-body">
        <div class="overview-circle">
          <div ref="circleEl" class="circle-chart"></div>
          <div class="circle-label">整体测试进度</div>
        </div>
        <div class="overview-info">
          <div class="info-row">
            <span class="info-label">测试开始时间</span>
            <span class="info-value">{{ formatDate(detail.start_time) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">测试结束时间</span>
            <span class="info-value">{{ detail.end_time ? formatDate(detail.end_time) : '--' }}</span>
          </div>
        </div>
        <div class="overview-stats">
          <div class="stat-item">
            <div class="stat-num blue">{{ detail.case_count || 328 }}</div>
            <div class="stat-lbl">用例总数</div>
          </div>
          <div class="stat-item">
            <div class="stat-num green">{{ detail.pass_rate || 65 }}%</div>
            <div class="stat-lbl">测试通过率</div>
          </div>
          <div class="stat-item">
            <div class="stat-lbl-top">用例执行进度</div>
            <el-progress :percentage="Number(detail.coverage_rate || 60)" :show-text="true" style="width:120px" />
          </div>
          <div class="stat-item">
            <div class="stat-num orange">{{ detail.defect_count || 5 }}</div>
            <div class="stat-lbl">缺陷总数</div>
          </div>
          <div class="stat-item">
            <div class="stat-num red">--</div>
            <div class="stat-lbl">缺陷解决率</div>
          </div>
          <div class="stat-item">
            <div class="stat-num red">--</div>
            <div class="stat-lbl">严重缺陷解决率</div>
          </div>
          <div class="stat-item">
            <div class="stat-num blue">0d 1h 2min</div>
            <div class="stat-lbl">执行耗时</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试结论 -->
    <div class="section-card" style="margin-top:16px">
      <div class="section-title">
        测试结论
        <el-icon class="edit-icon" @click="editingConclusion = !editingConclusion"><Edit /></el-icon>
      </div>
      <el-form :model="conclusion" label-width="80px" class="conclusion-form">
        <el-form-item label="测试结果">
          <el-select v-model="conclusion.result" placeholder="请选测试结果" :disabled="!editingConclusion" style="width:200px">
            <el-option label="通过" value="pass" />
            <el-option label="不通过" value="fail" />
            <el-option label="有条件通过" value="conditional" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试总结">
          <el-input
            v-model="conclusion.summary"
            type="textarea"
            :rows="5"
            placeholder="请输入测试总结内容..."
            :disabled="!editingConclusion"
            class="conclusion-editor"
          />
        </el-form-item>
        <el-form-item v-if="editingConclusion">
          <el-button type="primary" size="small" @click="saveConclusion">确认</el-button>
          <el-button size="small" @click="editingConclusion = false">取消</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 测试详情（图表区） -->
    <div class="section-card" style="margin-top:16px">
      <div class="section-title">测试详情</div>
      <div class="detail-charts">
        <div class="detail-chart-wrap">
          <div class="chart-sub-title">用例分布—按执行结果</div>
          <div ref="execChartEl" style="height:180px"></div>
        </div>
        <div class="detail-chart-wrap">
          <div class="chart-sub-title">用例分布—按执行结果</div>
          <div ref="distChartEl" style="height:180px"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { View, Download, Delete, Edit } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getReportDetailApi, updateReportApi } from '@/api/execution'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const editingConclusion = ref(false)
const conclusion = ref({ result: '', summary: '' })
const circleEl = ref(null)
const execChartEl = ref(null)
const distChartEl = ref(null)

function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '--' }

function saveConclusion() {
  ElMessage.success('保存成功')
  editingConclusion.value = false
}

async function onDelete() {
  const id = detail.value?.id ?? route.params.id
  if (!id) return
  try {
    await ElMessageBox.confirm('确定删除该测试报告？', '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteReportApi(id)
    ElMessage.success('已删除')
    router.push('/test-report')
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

function initCharts() {
  if (circleEl.value) {
    const c = echarts.init(circleEl.value)
    c.setOption({
      series: [{ type: 'gauge', radius: '90%', startAngle: 200, endAngle: -20, min: 0, max: 100, progress: { show: true, width: 10 }, axisLine: { lineStyle: { width: 10 } }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, pointer: { show: false }, detail: { valueAnimation: true, fontSize: 24, fontWeight: 700, color: '#1677ff', formatter: '{value}%', offsetCenter: [0, '5%'] }, data: [{ value: 60, name: '' }] }]
    })
  }
  if (execChartEl.value) {
    const c = echarts.init(execChartEl.value)
    c.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: '70%', data: [{ value: 213, name: '通过', itemStyle: { color: '#52c41a' } }, { value: 45, name: '失败', itemStyle: { color: '#ff4d4f' } }, { value: 70, name: '未执行', itemStyle: { color: '#e8e8e8' } }], label: { formatter: '{b}: {d}%', fontSize: 12 } }]
    })
  }
  if (distChartEl.value) {
    const c = echarts.init(distChartEl.value)
    c.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: '70%', data: [{ value: 80, name: 'P0', itemStyle: { color: '#ff4d4f' } }, { value: 120, name: 'P1', itemStyle: { color: '#faad14' } }, { value: 90, name: 'P2', itemStyle: { color: '#1677ff' } }, { value: 38, name: 'P3', itemStyle: { color: '#52c41a' } }], label: { formatter: '{b}: {d}%', fontSize: 12 } }]
    })
  }
}

onMounted(async () => {
  const id = route.params.id
  if (id) {
    try {
      const { data } = await getReportDetailApi(id)
      detail.value = data?.data || data || {}
    } catch { /* silent */ }
  }
  await nextTick()
  initCharts()
})
</script>

<style scoped>
.report-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: transparent;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  padding: 16px 20px;
  border-radius: 10px;
  background: rgba(20, 28, 47, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.15);
}

.detail-header__left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.detail-header__right { display: flex; gap: 8px; }

.report-id {
  font-size: 16px;
  font-weight: 700;
  font-family: ui-monospace, "Cascadia Code", monospace;
  color: #00d8ff;
  text-shadow: 0 0 14px rgba(0, 216, 255, 0.35);
}

.report-name { font-size: 16px; font-weight: 600; color: #e2e8f0; }
.update-tip { font-size: 12px; color: rgba(226, 232, 240, 0.55); }

.section-card {
  background: rgba(20, 28, 47, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.15);
  border-radius: 10px;
  padding: 20px;
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

.section-card:hover {
  border-color: rgba(0, 255, 255, 0.22);
  box-shadow: 0 0 24px rgba(0, 216, 255, 0.08);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.edit-icon { cursor: pointer; color: #00d8ff; font-size: 14px; }

.overview-body { display: flex; align-items: flex-start; gap: 32px; flex-wrap: wrap; }
.overview-circle { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.circle-chart { width: 140px; height: 140px; }
.circle-label { font-size: 12px; color: rgba(226, 232, 240, 0.5); }
.overview-info { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; gap: 8px; font-size: 13px; }
.info-label { color: rgba(226, 232, 240, 0.5); min-width: 80px; }
.info-value { color: #e2e8f0; }
.overview-stats { display: flex; flex-wrap: wrap; gap: 20px; flex: 1; }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 80px; }

.stat-num {
  font-size: 22px;
  font-weight: 700;
  line-height: 1;
  font-family: ui-monospace, "Cascadia Code", monospace;
}

.stat-num.blue {
  color: #5ee7ff;
  text-shadow: 0 0 14px rgba(94, 231, 255, 0.35);
}

.stat-num.green {
  color: #5efcb3;
  text-shadow: 0 0 12px rgba(94, 252, 179, 0.3);
}

.stat-num.orange {
  color: #ffc14d;
  text-shadow: 0 0 12px rgba(255, 193, 77, 0.25);
}

.stat-num.red {
  color: #ff7a8a;
  text-shadow: 0 0 12px rgba(255, 122, 138, 0.25);
}

.stat-lbl { font-size: 12px; color: rgba(226, 232, 240, 0.5); }
.stat-lbl-top { font-size: 12px; color: rgba(226, 232, 240, 0.5); margin-bottom: 4px; }

.conclusion-form { max-width: 800px; }

.conclusion-form :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.75);
}

.conclusion-form :deep(.el-input__wrapper),
.conclusion-form :deep(.el-select .el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.conclusion-editor :deep(.el-textarea__inner) {
  font-size: 13px;
  background: rgba(8, 12, 22, 0.45);
  color: #e2e8f0;
  border: 1px solid rgba(0, 255, 255, 0.1);
  box-shadow: none;
}

.detail-charts { display: flex; gap: 32px; flex-wrap: wrap; }
.detail-chart-wrap { flex: 1; min-width: 200px; }
.chart-sub-title { font-size: 13px; color: rgba(226, 232, 240, 0.65); margin-bottom: 8px; }

.section-card :deep(.el-progress-bar__outer) {
  background: rgba(255, 255, 255, 0.08);
}
</style>
