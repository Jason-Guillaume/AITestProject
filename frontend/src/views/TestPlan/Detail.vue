<template>
  <div class="plan-detail cyber-page">
    <!-- 标题 -->
    <div class="detail-header">
      <div class="detail-header__left">
        <span class="plan-id">{{ detail.id }}</span>
        <span class="plan-name">{{ detail.plan_name }}</span>
        <span class="update-tip">最近更新：{{ detail.updater_name }} {{ formatDate(detail.update_time) }}</span>
        <el-tag :type="planTagType(detail.plan_status)" size="small">{{ planLabel(detail.plan_status) }}</el-tag>
      </div>
      <div class="detail-header__right">
        <el-button size="small" type="primary" @click="startTest">
          <el-icon><VideoPlay /></el-icon> 开始测试
        </el-button>
        <el-button size="small" @click="genReport">
          <el-icon><Document /></el-icon> 生成测试报告
        </el-button>
        <el-button size="small"><el-icon><CopyDocument /></el-icon> 复制</el-button>
        <el-button size="small" type="danger" @click="removePlan"><el-icon><Delete /></el-icon> 删除</el-button>
      </div>
    </div>

    <div class="plan-body">
      <!-- 左侧基本信息 -->
      <div class="plan-left cyber-glass">
        <div class="section-title">
          基本信息
          <el-icon class="edit-icon" @click="toggleEditInfo"><Edit /></el-icon>
        </div>
        <el-form :model="detail" label-width="90px" class="info-form">
          <el-form-item label="测试周期">
            <el-date-picker v-model="dateRange" type="daterange" range-separator="至" :disabled="!editingInfo" size="small" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="测试人员">
            <template v-if="editingInfo">
              <el-select
                v-model="selectedTesters"
                multiple
                filterable
                collapse-tags
                collapse-tags-tooltip
                placeholder="请选择测试人员"
                size="small"
                style="width: 100%"
              >
                <el-option
                  v-for="u in userOptions"
                  :key="u.id"
                  :label="u.real_name || u.username || String(u.id)"
                  :value="u.id"
                />
              </el-select>
            </template>
            <span v-else class="info-readonly">{{ detail.testers_display || '—' }}</span>
          </el-form-item>
          <el-form-item label="计划描述">
            <el-input v-model="detail.description" type="textarea" :rows="3" :disabled="!editingInfo" size="small" />
          </el-form-item>
          <el-form-item label="关联迭代">
            <el-input v-model="detail.iteration" :disabled="!editingInfo" size="small" />
          </el-form-item>
          <el-form-item label="版本号">
            <el-input v-model="detail.version_no" :disabled="!editingInfo" size="small" />
          </el-form-item>
          <el-form-item label="测试环境">
            <el-input v-model="detail.environment" :disabled="!editingInfo" size="small" />
          </el-form-item>
          <el-form-item label="测试目标">
            <el-input v-model="detail.test_goal" :disabled="!editingInfo" size="small" />
          </el-form-item>
          <el-form-item v-if="editingInfo">
            <el-button type="primary" size="small" @click="saveInfo">保存</el-button>
            <el-button size="small" @click="cancelEdit">取消</el-button>
          </el-form-item>
        </el-form>

        <!-- 需求范围 -->
        <div class="section-title" style="margin-top:16px">需求范围</div>
        <el-table :data="reqList" size="small" class="admin-data-table">
          <el-table-column prop="id" label="需求ID" width="88" align="left" />
          <el-table-column prop="title" label="需求标题" min-width="120" align="left" show-overflow-tooltip />
          <el-table-column prop="priority" label="优先级" width="80" align="center" />
          <el-table-column prop="status" label="状态" width="80" align="center" />
          <el-table-column prop="handler" label="处理人" min-width="96" width="96" align="center" show-overflow-tooltip />
        </el-table>
      </div>

      <!-- 右侧测试用例 -->
      <div class="plan-right cyber-glass">
        <div class="section-title">测试用例</div>
        <el-table :data="caseList" size="small" class="admin-data-table">
          <el-table-column prop="id" label="用例ID" width="88" align="left" />
          <el-table-column label="等级" width="72" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="levelTagType(row.level)">{{ row.level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="case_name" label="用例名称" min-width="160" align="left" show-overflow-tooltip>
            <template #default="{ row }">
              <el-button link type="primary" size="small">{{ row.case_name }}</el-button>
            </template>
          </el-table-column>
          <el-table-column label="执行状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="execTagType(row.exec_status)" size="small">{{ row.exec_status || '未开始' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="执行结果" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.result" :type="row.result === '通过' ? 'success' : 'danger'" size="small">{{ row.result }}</el-tag>
              <span v-else class="dash">——</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, Document, CopyDocument, Delete, Edit } from '@element-plus/icons-vue'
import { getPlanDetailApi, updatePlanApi, deletePlanApi } from '@/api/execution'
import { getUsersApi } from '@/api/system'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const editingInfo = ref(false)
const dateRange = ref([])
const userOptions = ref([])
const selectedTesters = ref([])

function normalizeUsers(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

async function loadUsers() {
  try {
    const { data } = await getUsersApi({ page_size: 500 })
    userOptions.value = normalizeUsers(data)
  } catch {
    userOptions.value = []
  }
}

function syncTestersFromDetail() {
  const raw = detail.value?.testers
  if (!Array.isArray(raw)) {
    selectedTesters.value = []
    return
  }
  selectedTesters.value = raw.map((t) => (typeof t === 'object' ? t.id : t))
}

function toggleEditInfo() {
  if (editingInfo.value) {
    editingInfo.value = false
    syncTestersFromDetail()
  } else {
    syncTestersFromDetail()
    editingInfo.value = true
  }
}

function cancelEdit() {
  editingInfo.value = false
  syncTestersFromDetail()
}

const reqList = ref([
  { id: 1150023, title: '创建订单需求', priority: 'Middle', status: '开发中', handler: '张三' },
  { id: 1150024, title: '订单详情', priority: 'Middle', status: '开发中', handler: '李四' },
])

const caseList = ref([
  { id: 100001, level: 'P0', case_name: '未登录用户创建订单（游客下单）', exec_status: '未开始', result: null },
  { id: 100002, level: 'P0', case_name: '订单创建时修改商品数量（结算页调整）', exec_status: '未开始', result: null },
  { id: 100003, level: 'P1', case_name: '使用积分抵扣的订单创建', exec_status: '进行中', result: null },
  { id: 100004, level: 'P1', case_name: '收货地址为偏远地区（不支持配送）', exec_status: '已完成', result: '通过' },
  { id: 100005, level: 'P2', case_name: '订单创建后商品价格变动（未支付前）', exec_status: '已完成', result: '通过' },
  { id: 100006, level: 'P2', case_name: '批量创建订单（同一个用户短时间内多单）', exec_status: '已完成', result: '通过' },
  { id: 100007, level: 'P1', case_name: '正常支付订单（未超时）撤销', exec_status: '已完成', result: '失败' },
])

function planLabel(v) { return { 1: '未开始', 2: '进行中', 3: '已完成' }[v] || '-' }
function planTagType(v) { return { 1: 'info', 2: 'warning', 3: 'success' }[v] || '' }
function levelTagType(l) { return { P0: 'danger', P1: 'warning', P2: '', P3: 'info' }[l] || '' }
function execTagType(s) { return { '已完成': 'success', '进行中': 'warning', '未开始': 'info' }[s] || 'info' }
function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '' }

function startTest() { ElMessage.info('开始测试') }
function genReport() { router.push('/test-report') }

async function saveInfo() {
  const id = route.params.id
  const dr = dateRange.value
  const patch = {
    iteration: detail.value.iteration ?? '',
    environment: detail.value.environment ?? 'TEST',
    testers: selectedTesters.value,
  }
  if (dr?.length === 2) {
    patch.start_date = dr[0]
    patch.end_date = dr[1]
  }
  try {
    await updatePlanApi(id, patch)
    ElMessage.success('保存成功')
    editingInfo.value = false
    const { data } = await getPlanDetailApi(id)
    detail.value = data?.data || data || {}
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  }
}

async function removePlan() {
  try {
    await ElMessageBox.confirm(`确定删除计划「${detail.value.plan_name || route.params.id}」？`, '警告', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deletePlanApi(route.params.id)
    ElMessage.success('已删除')
    router.push('/test-plan')
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

onMounted(async () => {
  const id = route.params.id
  if (!id) return
  await loadUsers()
  try {
    const { data } = await getPlanDetailApi(id)
    detail.value = data?.data || data || {}
    syncTestersFromDetail()
    if (detail.value.start_date && detail.value.end_date) {
      dateRange.value = [detail.value.start_date.slice(0, 10), detail.value.end_date.slice(0, 10)]
    }
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载计划详情失败')
  }
})
</script>

<style scoped>
.plan-detail {
  background: transparent;
  border-radius: 10px;
  padding: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 10px;
  background: rgba(20, 28, 47, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 255, 255, 0.15);
}

.detail-header__left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.detail-header__right { display: flex; gap: 8px; }

.plan-id {
  font-size: 16px;
  font-weight: 700;
  font-family: ui-monospace, "Cascadia Code", monospace;
  color: #00d8ff;
  text-shadow: 0 0 14px rgba(0, 216, 255, 0.35);
}

.plan-name { font-size: 16px; font-weight: 600; color: #e2e8f0; }
.update-tip { font-size: 12px; color: rgba(226, 232, 240, 0.55); }
.plan-body { display: flex; gap: 24px; align-items: flex-start; }
.plan-left { flex: 0 0 380px; min-width: 0; }
.plan-right { flex: 1; min-width: 0; }

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.edit-icon { cursor: pointer; color: #00d8ff; font-size: 14px; }
.info-form { margin-top: 4px; }
.dash { color: rgba(255, 255, 255, 0.35); }

.plan-left :deep(.el-form-item__label),
.plan-right :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.75);
}

.plan-left :deep(.el-input__wrapper),
.plan-left :deep(.el-textarea__inner),
.plan-right :deep(.el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
  color: #e2e8f0;
}

.info-readonly {
  font-size: 13px;
  color: rgba(226, 232, 240, 0.85);
}
</style>
