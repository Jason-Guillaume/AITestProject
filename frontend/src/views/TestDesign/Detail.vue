<template>
  <div class="design-detail cyber-page">
    <!-- 标题栏 -->
    <div class="detail-header">
      <div class="detail-header__left">
        <h2 class="design-title">{{ detail.design_name || 'XXXX测试设计' }}</h2>
        <span class="update-tip">最近更新：{{ detail.updater_name }} {{ formatDate(detail.update_time) }}</span>
      </div>
      <div class="detail-header__right">
        <el-button size="small" @click="router.push('/test-design')">
          <el-icon><EditPen /></el-icon> 编辑信息
        </el-button>
        <el-button size="small">
          <el-icon><CopyDocument /></el-icon> 复制
        </el-button>
        <el-button size="small" type="danger" @click="removeDesign">
          <el-icon><Delete /></el-icon> 删除
        </el-button>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="detail-tabs">
      <el-tab-pane label="设计测试内容" name="design">
        <div class="design-toolbar">
          <div class="design-toolbar__left">
            <el-button size="small"><el-icon><RefreshLeft /></el-icon></el-button>
            <el-button size="small"><el-icon><RefreshRight /></el-icon></el-button>
            <el-button size="small"><el-icon><Upload /></el-icon> 上传</el-button>
            <el-button size="small"><el-icon><Download /></el-icon> 下载</el-button>
          </div>
          <div class="design-toolbar__right">
            <el-input v-model="caseSearch" placeholder="请输入测试用例" clearable size="small" style="width:200px" />
            <el-select v-model="aiModel" size="small" style="width:140px">
              <el-option label="文心大模型5.0" value="wenxin" />
              <el-option label="GPT-4o" value="gpt4o" />
            </el-select>
            <el-button type="primary" size="small" @click="aiGenerate">AI生成用例</el-button>
            <el-button size="small" @click="toPlan">转测试计划</el-button>
            <el-dropdown size="small">
              <el-button size="small">历史记录<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>查看历史版本</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
        <el-checkbox v-model="onlyUnreviewed" label="只展示未归档用例" style="margin:8px 0" />

        <!-- 树形内容 -->
        <div class="tree-wrap">
          <el-tree
            :data="treeData"
            :props="{ label: 'label', children: 'children' }"
            default-expand-all
            show-checkbox
            node-key="id"
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <span class="node-tag" :class="`tag--${data.type}`">{{ typeLabel(data.type) }}</span>
                <span class="node-label">{{ data.label }}</span>
                <span class="node-actions">
                  <el-icon class="node-icon" @click.stop="addChild(data)"><Plus /></el-icon>
                  <el-icon class="node-icon" @click.stop="editNode(data)"><Edit /></el-icon>
                </span>
              </span>
            </template>
          </el-tree>
        </div>
      </el-tab-pane>

      <el-tab-pane label="评审测试设计" name="review">
        <el-empty description="暂无评审记录" />
      </el-tab-pane>

      <el-tab-pane label="执行测试用例" name="execute">
        <el-empty description="请先关联测试计划" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, CopyDocument, Delete, RefreshLeft, RefreshRight, Upload, Download, ArrowDown, Plus, Edit } from '@element-plus/icons-vue'
import { getDesignDetailApi, deleteDesignApi } from '@/api/testcase'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const activeTab = ref('design')
const caseSearch = ref('')
const aiModel = ref('wenxin')
const onlyUnreviewed = ref(false)

const treeData = ref([
  {
    id: 1, type: 'req', label: '【需求】商务订单',
    children: [
      {
        id: 2, type: 'module', label: '【模块】创建订单',
        children: [
          { id: 3, type: 'point', label: '【测试点】验证游客下单', children: [
            { id: 4, type: 'case', label: '【用例】P0 未登录用户创建订单（游客下单）' },
          ]},
          { id: 5, type: 'point', label: '【测试点】多商品创建', children: [
            { id: 6, type: 'case', label: '【用例】P1 商品包含多规格（颜色/尺寸）的订单创建' },
          ]},
        ],
      },
      { id: 7, type: 'module', label: '【模块】审批订单', children: [] },
      { id: 8, type: 'module', label: '【模块】付款订单', children: [] },
    ],
  },
])

function typeLabel(type) {
  return { req: '需', module: '模', point: '点', case: '例' }[type] || ''
}
function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '' }

function aiGenerate() { ElMessage.info('正在调用 AI 生成用例...') }
function toPlan() { ElMessage.info('转测试计划功能开发中') }
function addChild(data) { ElMessage.info('新增子节点：' + data.label) }
function editNode(data) { ElMessage.info('编辑节点：' + data.label) }

async function removeDesign() {
  try {
    await ElMessageBox.confirm(`确定删除测试设计「${detail.value.design_name || route.params.id}」？`, '警告', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteDesignApi(route.params.id)
    ElMessage.success('已删除')
    router.push('/test-design')
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

onMounted(async () => {
  const id = route.params.id
  if (!id) return
  try {
    const { data } = await getDesignDetailApi(id)
    detail.value = data?.data || data || {}
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载测试设计失败')
  }
})
</script>

<style scoped>
.design-detail {
  background: rgba(20, 28, 47, 0.45);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 10px;
  padding: 20px;
  min-height: 500px;
  border: 1px solid rgba(0, 255, 255, 0.15);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.detail-header__right { display: flex; gap: 8px; }

.design-title {
  font-size: 18px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0;
}

.update-tip { font-size: 12px; color: rgba(226, 232, 240, 0.55); margin-left: 12px; }

.detail-tabs :deep(.el-tabs__header) { margin-bottom: 12px; }

.detail-tabs :deep(.el-tabs__item) {
  color: rgba(226, 232, 240, 0.65);
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: #00d8ff;
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background-color: #00d8ff;
  box-shadow: 0 0 10px rgba(0, 216, 255, 0.45);
}

.design-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}

.design-toolbar__left,
.design-toolbar__right { display: flex; align-items: center; gap: 6px; }

.tree-wrap {
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  padding: 12px;
  min-height: 300px;
  background: rgba(12, 18, 32, 0.35);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.tree-node { display: flex; align-items: center; gap: 8px; width: 100%; }

.node-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  flex-shrink: 0;
  font-weight: 600;
  border: 1px solid transparent;
}

.tag--req {
  background: rgba(0, 216, 255, 0.12);
  color: #5ee7ff;
  border-color: rgba(0, 216, 255, 0.25);
}

.tag--module {
  background: rgba(167, 139, 250, 0.15);
  color: #c4b5fd;
  border-color: rgba(167, 139, 250, 0.3);
}

.tag--point {
  background: rgba(251, 191, 36, 0.12);
  color: #fcd34d;
  border-color: rgba(251, 191, 36, 0.28);
}

.tag--case {
  background: rgba(52, 211, 153, 0.12);
  color: #6ee7b7;
  border-color: rgba(52, 211, 153, 0.28);
}

.node-label { flex: 1; font-size: 13px; color: #e2e8f0; }
.node-actions { display: none; gap: 6px; }
.tree-node:hover .node-actions { display: flex; }
.node-icon { font-size: 14px; color: #00d8ff; cursor: pointer; }

.design-detail :deep(.el-checkbox__label) {
  color: rgba(226, 232, 240, 0.85);
}

.design-detail :deep(.el-empty__description) {
  color: rgba(226, 232, 240, 0.55);
}
</style>
