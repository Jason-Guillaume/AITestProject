<template>
  <div class="approach-page min-h-full cyber-page">
    <!-- 工具栏：搜索 + 筛选 + 智能新增 -->
    <div class="approach-toolbar">
      <div class="approach-toolbar__search">
        <el-input
          v-model="searchKw"
          class="approach-search-input"
          placeholder="请输入测试方案名称"
          clearable
          @keyup.enter="load"
        >
          <template #append>
            <el-button type="primary" class="approach-search-btn" @click="load">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
      <div class="approach-toolbar__actions">
        <el-button class="filter-btn" :type="isRecycleMode ? 'warning' : ''" @click="toggleRecycleMode">
          {{ isRecycleMode ? '返回列表' : '回收站' }}
        </el-button>
        <el-button class="filter-btn" :type="isSelectMode ? 'info' : ''" @click="toggleSelectMode">
          {{ isSelectMode ? '取消选择' : '选择' }}
          <span v-if="isSelectMode && selectedIds.length" style="margin-left: 6px">（{{ selectedIds.length }}）</span>
        </el-button>

        <el-button
          v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
          type="danger"
          plain
          :loading="batchDeleting"
          @click="batchSoftDelete"
        >
          批量删除（{{ selectedIds.length }}）
        </el-button>
        <el-button
          v-if="isSelectMode && isRecycleMode && selectedIds.length > 0"
          type="success"
          plain
          :loading="batchRestoring"
          @click="batchRestore"
        >
          批量恢复（{{ selectedIds.length }}）
        </el-button>
        <el-button
          v-if="isSelectMode && isRecycleMode && selectedIds.length > 0"
          type="danger"
          plain
          :loading="batchHardDeleting"
          @click="batchHardDelete"
        >
          彻底删除（{{ selectedIds.length }}）
        </el-button>
        <el-button
          v-if="isSelectMode && !isRecycleMode && selectedIds.length > 0"
          type="success"
          plain
          :loading="batchCopying"
          @click="batchCopySelected"
        >
          批量复制
        </el-button>
        <el-button class="filter-btn" @click="filterDrawerOpen = true">
          <el-icon><Filter /></el-icon>
          更多筛选
        </el-button>
        <el-button type="primary" class="smart-add-btn" @click="openCreate">
          <el-icon><Plus /></el-icon>
          智能新增
        </el-button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div class="approach-grid">
      <div
        v-for="item in filteredList"
        :key="item.id"
        class="approach-card"
        :class="{ 'approach-card--selected': selectedIds.includes(item.id) }"
        @click="onCardClick(item)"
      >
        <div v-if="isSelectMode" class="approach-card__select" @click.stop>
          <button
            type="button"
            class="approach-card__select-btn"
            :class="{ 'is-checked': selectedIdSet.has(item.id) }"
            :aria-pressed="selectedIdSet.has(item.id)"
            :aria-label="selectedIdSet.has(item.id) ? '取消选择' : '选择测试方案'"
            @click.stop="toggleSelected(item.id, !selectedIdSet.has(item.id))"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M20 6L9 17l-5-5"
                stroke="currentColor"
                stroke-width="2.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </div>
        <div class="approach-card__cover">
          <img v-if="coverUrl(item)" :src="coverUrl(item)" class="cover-img" alt="" loading="lazy" />
          <div v-else class="cover-placeholder cover-placeholder--empty">
            <el-icon class="cover-placeholder__icon"><Picture /></el-icon>
          </div>
          <div class="approach-card__badge" :class="'approach-card__badge--' + badgeVariant(item.test_category)">
            <el-icon :size="18"><component :is="categoryBadgeIcon(item.test_category)" /></el-icon>
          </div>
        </div>
        <div class="approach-card__body">
          <div class="approach-card__title-row">
            <span class="approach-card__title" :title="item.scheme_name">{{ item.scheme_name }}</span>
            <div class="approach-card__actions" @click.stop>
              <el-button
                link
                type="primary"
                class="approach-card__edit"
                :disabled="isSelectMode || isRecycleMode"
                @click="editItem(item)"
              >
                <el-icon><EditPen /></el-icon>
              </el-button>
              <el-button
                v-if="!isRecycleMode"
                link
                type="danger"
                class="approach-card__delete"
                :disabled="isSelectMode"
                @click="softDeleteItem(item)"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
              <el-button
                v-else
                link
                type="success"
                class="approach-card__restore"
                :disabled="isSelectMode"
                @click="restoreItem(item)"
              >
                恢复
              </el-button>
              <el-button
                v-if="isRecycleMode"
                link
                type="danger"
                class="approach-card__delete"
                :disabled="isSelectMode"
                @click="hardDeleteItem(item)"
              >
                彻底删除
              </el-button>
            </div>
          </div>
          <div class="approach-card__meta">
            <span class="meta-label">测试目标：</span>
            <span class="meta-value ellipsis">{{ goalPreview(item) }}</span>
          </div>
          <div class="approach-card__meta">
            <span class="meta-label">创建人：</span>
            <span class="meta-value">{{ item.creator_name || '-' }}</span>
          </div>
          <div class="approach-card__meta">
            <span class="meta-label">更新时间：</span>
            <span class="meta-value">{{ formatDateTime(item.update_time) }}</span>
          </div>
          <div class="approach-card__footer">
            <span
              class="category-tag"
              :class="'category-tag--' + badgeVariant(item.test_category)"
            >{{ item.test_category_display || '—' }}</span>
          </div>
        </div>
      </div>

      <div class="approach-card approach-card--empty" @click="openCreate">
        <el-icon class="empty-icon"><Plus /></el-icon>
        <span class="empty-text">新增测试方案</span>
      </div>
    </div>

    <!-- 更多筛选 -->
    <el-drawer v-model="filterDrawerOpen" title="筛选条件" direction="rtl" size="320px" class="cyber-drawer-dark">
      <el-form label-position="top">
        <el-form-item label="测试类型">
          <el-select v-model="filterCategory" placeholder="全部" clearable class="w-full">
            <el-option
              v-for="opt in categoryOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="drawer-footer">
          <el-button @click="resetFilter">重置</el-button>
          <el-button type="primary" @click="filterDrawerOpen = false">确定</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="showDialog"
      :title="editing ? '编辑测试方案' : '智能新增测试方案'"
      width="480px"
      destroy-on-close
      class="approach-dialog cyber-dialog-dark"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="方案名称" prop="scheme_name">
          <el-input v-model="form.scheme_name" placeholder="请输入方案名称" />
        </el-form-item>
        <el-form-item label="版本" prop="version">
          <el-input v-model="form.version" placeholder="如 V3.0" />
        </el-form-item>
        <el-form-item label="测试类型" prop="test_category">
          <el-select v-model="form.test_category" placeholder="请选择" class="w-full">
            <el-option
              v-for="opt in categoryOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="测试目标" prop="test_goal">
          <el-input
            v-model="form.test_goal"
            type="textarea"
            :rows="3"
            placeholder="简述测试目标（可选）"
          />
        </el-form-item>
      </el-form>
      <div class="image-section">
        <div class="image-section__title">图片历史</div>
        <div class="thumb-grid">
          <div v-for="img in dialogImagesHistory" :key="img.id || img.image_url" class="thumb-item">
            <div class="thumb-item__media">
              <img :src="img.image_url" alt="" class="thumb-img" />
            </div>
            <el-button
              v-if="img.id && (img.approach_id || editing?.id)"
              type="danger"
              class="thumb-remove"
              circle
              size="small"
              :loading="deletingImageId === img.id"
              @click.stop="deleteHistoryImage(img)"
            >
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <div v-if="dialogImagesHistory.length === 0" class="thumb-item thumb-item--empty">
            暂无图片
          </div>
        </div>
        <div class="image-upload-row">
          <div class="pick-files-wrap">
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*"
              multiple
              class="file-input-overlay"
              @change="onFilesChange"
            />
            <el-button class="pick-files-btn">选择图片</el-button>
          </div>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="selectedFiles.length === 0 || !editing"
            @click="uploadSelectedImages"
          >
            上传图片
          </el-button>
        </div>
        <div v-if="selectedPreviewUrls.length" class="thumb-grid selected-preview-grid">
          <div v-for="(url, idx) in selectedPreviewUrls" :key="url" class="thumb-item">
            <img :src="url" alt="" class="thumb-img" />
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, markRaw } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Search,
  Filter,
  EditPen,
  Delete,
  CircleCheck,
  Connection,
  Monitor,
  User,
  Picture,
  Close,
} from '@element-plus/icons-vue'
import {
  getApproachsApi,
  createApproachApi,
  updateApproachApi,
  deleteApproachApi,
  batchCopyApproachsApi,
  getApproachsRecycleApi,
  restoreApproachApi,
  hardDeleteApproachApi,
  bulkSoftDeleteApproachsApi,
  bulkRestoreApproachsApi,
  bulkHardDeleteApproachsApi,
  uploadApproachImagesApi,
  deleteApproachImageApi,
} from '@/api/testcase'

const router = useRouter()

const CATEGORY = {
  1: { label: '单元测试', icon: markRaw(CircleCheck) },
  2: { label: '集成测试', icon: markRaw(Connection) },
  3: { label: '系统测试', icon: markRaw(Monitor) },
  4: { label: '用户测试', icon: markRaw(User) },
}

const categoryOptions = [
  { value: 1, label: '单元测试' },
  { value: 2, label: '集成测试' },
  { value: 3, label: '系统测试' },
  { value: 4, label: '用户测试' },
]

const list = ref([])
const searchKw = ref('')
const filterDrawerOpen = ref(false)
const filterCategory = ref(null)
const showDialog = ref(false)
const editing = ref(null)
const saving = ref(false)
const uploading = ref(false)
const formRef = ref()
const fileInputRef = ref(null)
const selectedFiles = ref([])
const selectedPreviewUrls = ref([])
// 弹窗“图片历史”在“新建”时也希望沿用的本地图片库（避免 editing 为空导致历史丢失）
const myImageHistory = ref([])
const deletingImageId = ref(null)
const selectedIds = ref([])
const batchDeleting = ref(false)
const batchRestoring = ref(false)
const batchHardDeleting = ref(false)
const batchCopying = ref(false)
const form = ref({
  scheme_name: '',
  version: '',
  test_goal: '',
  test_category: 1,
})

function revokeSelectedPreviews() {
  if (selectedPreviewUrls.value.length) {
    selectedPreviewUrls.value.forEach((u) => {
      try {
        URL.revokeObjectURL(u)
      } catch {
        /* silent */
      }
    })
  }
  selectedPreviewUrls.value = []
}

const rules = {
  scheme_name: [{ required: true, message: '请输入方案名称', trigger: 'blur' }],
  version: [{ required: true, message: '请输入版本', trigger: 'blur' }],
}

function normalizeListResponse(data) {
  if (Array.isArray(data)) return data
  return data?.results || data?.data || []
}

const filteredList = computed(() => {
  let rows = list.value
  if (filterCategory.value != null && filterCategory.value !== '') {
    rows = rows.filter((i) => Number(i.test_category) === Number(filterCategory.value))
  }
  if (!searchKw.value) return rows
  return rows.filter((i) => (i.scheme_name || '').includes(searchKw.value.trim()))
})

const isRecycleMode = ref(false)
const isSelectMode = ref(false)
const selectedIdSet = computed(() => new Set(selectedIds.value))

function toggleSelectMode() {
  isSelectMode.value = !isSelectMode.value
  if (!isSelectMode.value) selectedIds.value = []
}

function toggleRecycleMode() {
  isRecycleMode.value = !isRecycleMode.value
  selectedIds.value = []
  isSelectMode.value = false
  load()
}

function toggleSelected(id, checked) {
  const nid = Number(id)
  if (!Number.isFinite(nid)) return
  const cur = new Set((selectedIds.value || []).map((x) => Number(x)))
  if (checked) cur.add(nid)
  else cur.delete(nid)
  selectedIds.value = Array.from(cur)
}

function onCardClick(item) {
  if (isSelectMode.value) {
    const id = item?.id
    toggleSelected(id, !selectedIdSet.value.has(id))
    return
  }
  goDesign()
}

function rebuildMyImageHistoryFromList() {
  const merged = []
  for (const item of list.value || []) {
    if (Array.isArray(item?.images) && item.images.length) merged.push(...item.images)
  }
  const next = new Map()
  for (const img of merged) {
    const key = img?.id ?? img?.image_url
    if (key != null) next.set(key, img)
  }
  myImageHistory.value = Array.from(next.values())
}

const dialogImagesHistory = computed(() => {
  // 编辑态：展示当前方案的图片
  if (editing.value?.images?.length) return editing.value.images
  // 新建态：展示本地“我的图片历史”
  return myImageHistory.value
})

function badgeVariant(cat) {
  const k = Number(cat)
  if (!k || Number.isNaN(k)) return 'none'
  return k
}

function categoryBadgeIcon(cat) {
  const k = Number(cat)
  if (!k || Number.isNaN(k)) return CircleCheck
  return CATEGORY[k]?.icon || CircleCheck
}

/** 仅使用库表/接口：首图 URL → cover_image → 无则空（不拉外网占位图） */
function coverUrl(item) {
  const first = item?.images?.[0]
  if (first?.image_url) return first.image_url
  const url = (item.cover_image || '').trim()
  return url || ''
}

/** 仅展示 test_goal 字段；空则 — */
function goalPreview(item) {
  const g = (item.test_goal || '').trim()
  if (!g) return '—'
  return g.length > 48 ? `${g.slice(0, 48)}…` : g
}

function formatDateTime(dt) {
  if (!dt) return '-'
  const s = typeof dt === 'string' ? dt.slice(0, 19) : String(dt)
  return s.replace('T', ' ').replace(/-/g, '/')
}

function goDesign() {
  router.push('/test-design')
}

function openCreate() {
  editing.value = null
  selectedFiles.value = []
  revokeSelectedPreviews()
  if (fileInputRef.value) fileInputRef.value.value = ''
  form.value = {
    scheme_name: '',
    version: '',
    test_goal: '',
    test_category: 1,
  }
  showDialog.value = true
}

function resetFilter() {
  filterCategory.value = null
}

async function load() {
  try {
    const { data } = await (isRecycleMode.value ? getApproachsRecycleApi() : getApproachsApi())
    list.value = normalizeListResponse(data)
    rebuildMyImageHistoryFromList()
  } catch (err) {
    const d = err?.response?.data;
    const msg =
      (typeof d === "string" && d) ||
      d?.msg ||
      d?.detail ||
      err?.message;
    ElMessage.error(msg && typeof msg === "string" ? msg : "加载测试方案失败");
  }
}

function editItem(item) {
  editing.value = item
  selectedFiles.value = []
  revokeSelectedPreviews()
  if (fileInputRef.value) fileInputRef.value.value = ''
  form.value = {
    scheme_name: item.scheme_name || '',
    version: item.version || '',
    test_goal: item.test_goal || '',
    test_category: item.test_category != null ? Number(item.test_category) : 1,
  }
  showDialog.value = true
}

async function softDeleteItem(item) {
  try {
    await ElMessageBox.confirm(`确定将测试方案「${item.scheme_name}」移入回收站吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteApproachApi(item.id)
    ElMessage.success('已移入回收站')
    if (editing.value?.id === item.id) {
      showDialog.value = false
      editing.value = null
    }
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg =
      (typeof d === 'string' && d) ||
      d?.msg ||
      d?.detail ||
      err?.message ||
      '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function batchSoftDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定将选中的 ${selectedIds.value.length} 条测试方案移入回收站吗？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  batchDeleting.value = true
  try {
    const { data } = await bulkSoftDeleteApproachsApi({ ids: selectedIds.value })
    const deleted = Number(data?.deleted ?? data?.data?.deleted ?? 0)
    const skipped = Number(data?.skipped ?? data?.data?.skipped ?? 0)
    ElMessage.success(`已删除 ${deleted} 条；跳过 ${skipped} 条`)
    selectedIds.value = []
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg = (typeof d === 'string' && d) || d?.msg || d?.detail || err?.message || '批量删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

async function batchRestore() {
  if (!selectedIds.value.length) return
  batchRestoring.value = true
  try {
    const { data } = await bulkRestoreApproachsApi({ ids: selectedIds.value })
    const restored = Number(data?.restored ?? data?.data?.restored ?? 0)
    const skipped = Number(data?.skipped ?? data?.data?.skipped ?? 0)
    ElMessage.success(`已恢复 ${restored} 条；跳过 ${skipped} 条`)
    selectedIds.value = []
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg = (typeof d === 'string' && d) || d?.msg || d?.detail || err?.message || '批量恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量恢复失败')
  } finally {
    batchRestoring.value = false
  }
}

async function batchHardDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确定彻底删除选中的 ${selectedIds.value.length} 条测试方案吗？此操作不可恢复。`, '警告', {
      type: 'error',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  batchHardDeleting.value = true
  try {
    const { data } = await bulkHardDeleteApproachsApi({ ids: selectedIds.value })
    const count = Number(data?.count ?? data?.data?.count ?? 0)
    ElMessage.success(`已彻底删除 ${count} 条`)
    selectedIds.value = []
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg = (typeof d === 'string' && d) || d?.msg || d?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
  } finally {
    batchHardDeleting.value = false
  }
}

async function hardDeleteItem(item) {
  try {
    await ElMessageBox.confirm(`确定彻底删除测试方案「${item.scheme_name}」吗？此操作不可恢复。`, '警告', {
      type: 'error',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await hardDeleteApproachApi(item.id)
    ElMessage.success('已彻底删除')
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg = (typeof d === 'string' && d) || d?.msg || d?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
  }
}

async function restoreItem(item) {
  try {
    await restoreApproachApi(item.id)
    ElMessage.success('已恢复')
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg = (typeof d === 'string' && d) || d?.msg || d?.detail || err?.message || '恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '恢复失败')
  }
}

async function batchCopySelected() {
  if (!selectedIds.value.length) return
  let suffix = '（复制）'
  try {
    const { value } = await ElMessageBox.prompt('请输入复制后名称后缀（可留空）', '批量复制测试方案', {
      inputValue: suffix,
      confirmButtonText: '复制',
      cancelButtonText: '取消',
    })
    suffix = String(value ?? '').trim() || '（复制）'
  } catch {
    return
  }
  batchCopying.value = true
  try {
    const { data } = await batchCopyApproachsApi({ ids: selectedIds.value, name_suffix: suffix })
    const created = Number(data?.created ?? data?.data?.created ?? 0)
    const missing = Array.isArray(data?.missing_ids) ? data.missing_ids.length : Array.isArray(data?.data?.missing_ids) ? data.data.missing_ids.length : 0
    const errors = Array.isArray(data?.errors) ? data.errors.length : Array.isArray(data?.data?.errors) ? data.data.errors.length : 0
    if (errors) ElMessage.warning(`已复制 ${created} 条；缺失 ${missing} 条；失败 ${errors} 条`)
    else ElMessage.success(`已复制 ${created} 条；缺失 ${missing} 条`)
    selectedIds.value = []
    await load()
  } catch (err) {
    const d = err?.response?.data
    const msg = (typeof d === 'string' && d) || d?.msg || d?.detail || err?.message || '批量复制失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量复制失败')
  } finally {
    batchCopying.value = false
  }
}

async function submit() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      scheme_name: form.value.scheme_name,
      version: form.value.version,
      test_goal: form.value.test_goal || null,
      test_category: form.value.test_category,
    }
    if (editing.value) {
      await updateApproachApi(editing.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createApproachApi(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    editing.value = null
    load()
  } finally {
    saving.value = false
  }
}

onMounted(load)

function onFilesChange(e) {
  const files = e.target?.files
  const list = files ? Array.from(files) : []
  selectedFiles.value = list

  revokeSelectedPreviews()
  if (list.length) {
    selectedPreviewUrls.value = list.map((f) => URL.createObjectURL(f))
  }
}

// 选择按钮由 .file-input-overlay 透明覆盖触发，无需额外 click

async function uploadSelectedImages() {
  if (!editing.value) return
  if (selectedFiles.value.length === 0) return

  uploading.value = true
  try {
    const fd = new FormData()
    selectedFiles.value.forEach((f) => fd.append('images', f))
    await uploadApproachImagesApi(editing.value.id, fd)
    ElMessage.success('图片上传成功')

    selectedFiles.value = []
    revokeSelectedPreviews()
    if (fileInputRef.value) fileInputRef.value.value = ''

    // 刷新列表，保证图片历史是最新
    await load()
    const updated = list.value.find((i) => i.id === editing.value.id)
    if (updated) editing.value = updated
  } catch (err) {
    ElMessage.error(err?.response?.data?.msg || '图片上传失败')
  } finally {
    uploading.value = false
  }
}

onBeforeUnmount(() => {
  revokeSelectedPreviews()
})

async function deleteHistoryImage(img) {
  const approachId = img.approach_id ?? editing.value?.id
  if (!img?.id || !approachId) {
    ElMessage.warning('无法删除该图片')
    return
  }
  try {
    await ElMessageBox.confirm(
      '确定从图片历史中删除该图片吗？删除后不可恢复，对应方案封面可能会自动更换。',
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  deletingImageId.value = img.id
  try {
    await deleteApproachImageApi(approachId, img.id)
    ElMessage.success('已删除')
    await load()
    if (editing.value?.id === approachId) {
      const updated = list.value.find((i) => i.id === approachId)
      if (updated) editing.value = updated
    }
  } catch (err) {
    const d = err?.response?.data
    const msg =
      (typeof d === 'string' && d) ||
      d?.msg ||
      d?.detail ||
      err?.message ||
      '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  } finally {
    deletingImageId.value = null
  }
}
</script>

<style scoped>
.approach-page {
  --primary: #00d8ff;
  --primary-hover: #5ee7ff;
  background: transparent;
  margin: -16px;
  padding: 20px 20px 28px;
  border-radius: 0;
}

.approach-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 20px;
}

.approach-toolbar__search {
  flex: 1;
  min-width: 280px;
  max-width: 560px;
}

.approach-search-input :deep(.el-input__wrapper) {
  border-radius: 999px 0 0 999px;
  background: rgba(10, 16, 28, 0.55);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.15);
}

.approach-search-input :deep(.el-input-group__append) {
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.35), rgba(0, 140, 200, 0.45));
  border: none;
  border-radius: 0 999px 999px 0;
  box-shadow: none;
  padding: 0;
}

.approach-search-btn {
  border: none;
  margin: 0;
  height: 100%;
  padding: 0 18px;
  border-radius: 0 999px 999px 0;
  background: transparent;
}

.approach-search-btn:hover {
  background: rgba(0, 216, 255, 0.15);
}

.approach-toolbar__actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.filter-btn {
  border-color: rgba(0, 255, 255, 0.25);
  color: #00d8ff;
  background: rgba(20, 28, 47, 0.5);
}

.filter-btn:hover {
  border-color: rgba(0, 216, 255, 0.45);
  color: #5ee7ff;
  background: rgba(0, 216, 255, 0.08);
}

.smart-add-btn {
  border-radius: 8px;
  padding: 8px 18px;
  font-weight: 500;
}

.approach-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 18px;
}

@media (min-width: 1280px) {
  .approach-grid {
    grid-template-columns: repeat(5, 1fr);
  }
}

@media (min-width: 1600px) {
  .approach-grid {
    gap: 20px;
  }
}

.approach-card {
  background: rgba(20, 28, 47, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(0, 255, 255, 0.15);
  cursor: pointer;
  transition:
    border-color 0.22s ease,
    box-shadow 0.22s ease,
    transform 0.18s ease;
}

.approach-card:hover {
  border-color: rgba(0, 216, 255, 0.4);
  box-shadow: 0 0 28px rgba(0, 216, 255, 0.15);
  transform: translateY(-2px);
}

.approach-card__cover {
  position: relative;
  height: 132px;
  background: rgba(10, 16, 29, 0.65);
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder__icon {
  font-size: 36px;
  color: rgba(0, 216, 255, 0.25);
}

.cover-placeholder--empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(8, 12, 22, 0.5);
}

.approach-card__badge {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0a101d;
  box-shadow: 0 0 14px rgba(0, 216, 255, 0.35);
}

.approach-card__badge--1 {
  background: linear-gradient(135deg, #2dd4bf, #00d8ff);
}
.approach-card__badge--2 {
  background: linear-gradient(135deg, #a78bfa, #c084fc);
}
.approach-card__badge--3 {
  background: linear-gradient(135deg, #38bdf8, #00d8ff);
}
.approach-card__badge--4 {
  background: linear-gradient(135deg, #fb923c, #fbbf24);
}

.approach-card__body {
  padding: 12px 14px 14px;
}

.approach-card__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.approach-card__title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.approach-card__actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.approach-card__select {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 3;
  opacity: 0;
  transform: translateY(-1px);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.approach-card:hover .approach-card__select,
.approach-card--selected .approach-card__select {
  opacity: 1;
  transform: translateY(0);
}

.approach-card__select-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: rgba(165, 243, 252, 0.85);
  background: rgba(10, 16, 28, 0.35);
  border: 1px solid rgba(34, 211, 238, 0.16);
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.08);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.approach-card__select-btn:hover {
  border-color: rgba(34, 211, 238, 0.32);
  box-shadow: 0 0 22px rgba(34, 211, 238, 0.12);
  background: rgba(0, 255, 255, 0.06);
}

.approach-card__select-btn.is-checked {
  color: rgba(226, 232, 240, 0.96);
  border-color: rgba(34, 211, 238, 0.55);
  background: rgba(0, 255, 255, 0.1);
  box-shadow:
    0 0 0 1px rgba(0, 255, 255, 0.18) inset,
    0 0 26px rgba(0, 255, 255, 0.14);
}

.approach-card__select-btn:focus-visible {
  outline: none;
  box-shadow:
    0 0 0 2px rgba(0, 255, 255, 0.28),
    0 0 22px rgba(0, 255, 255, 0.12);
}

.approach-card--selected {
  border-color: rgba(0, 255, 255, 0.38);
  box-shadow:
    0 0 0 1px rgba(0, 255, 255, 0.14) inset,
    0 0 28px rgba(0, 255, 255, 0.08);
}

.approach-card__restore {
  flex-shrink: 0;
  padding: 4px 6px;
  color: rgba(34, 211, 238, 0.9) !important;
}

.approach-card__restore:hover {
  color: rgba(165, 243, 252, 0.95) !important;
  filter: drop-shadow(0 0 10px rgba(34, 211, 238, 0.28));
}

.approach-card__edit {
  flex-shrink: 0;
  padding: 4px;
}

.approach-card__delete {
  flex-shrink: 0;
  padding: 4px;
  color: rgba(248, 113, 113, 0.95) !important;
}

.approach-card__delete:hover {
  color: #fca5a5 !important;
  filter: drop-shadow(0 0 8px rgba(248, 113, 113, 0.45));
}

.approach-card__meta {
  font-size: 12px;
  line-height: 1.5;
  margin-bottom: 4px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  color: rgba(226, 232, 240, 0.65);
}

.meta-label {
  color: rgba(226, 232, 240, 0.45);
  flex-shrink: 0;
}

.meta-value {
  color: rgba(226, 232, 240, 0.82);
  word-break: break-all;
}

.meta-value.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
}

.approach-card__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.category-tag {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: 4px;
  border: 1px solid transparent;
}

.category-tag--1 {
  color: #fcd34d;
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.25);
}
.category-tag--2 {
  color: #5ee7ff;
  background: rgba(0, 216, 255, 0.1);
  border-color: rgba(0, 216, 255, 0.22);
}
.category-tag--3 {
  color: #fde68a;
  background: rgba(250, 204, 21, 0.1);
  border-color: rgba(250, 204, 21, 0.22);
}
.category-tag--4 {
  color: #f9a8d4;
  background: rgba(244, 114, 182, 0.12);
  border-color: rgba(244, 114, 182, 0.22);
}

.approach-card__badge--none {
  background: linear-gradient(135deg, #64748b, #94a3b8);
}

.category-tag--none {
  color: rgba(226, 232, 240, 0.55);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.08);
}

.approach-card--empty {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-style: dashed;
  border-color: rgba(0, 255, 255, 0.2);
  background: rgba(20, 28, 47, 0.25);
  box-shadow: none;
}

.approach-card--empty:hover {
  border-color: rgba(0, 216, 255, 0.45);
  background: rgba(0, 216, 255, 0.06);
}

.empty-icon {
  font-size: 36px;
  color: rgba(0, 216, 255, 0.35);
}

.empty-text {
  color: rgba(226, 232, 240, 0.55);
  font-size: 13px;
  margin-top: 10px;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.w-full {
  width: 100%;
}

.image-section {
  margin-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 12px;
}

.image-section__title {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.55);
  margin-bottom: 10px;
}

.thumb-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.thumb-item {
  position: relative;
  width: 76px;
  height: 48px;
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 255, 0.12);
  background: rgba(8, 12, 22, 0.55);
}

.thumb-item__media {
  width: 100%;
  height: 100%;
  border-radius: 7px;
  overflow: hidden;
}

.thumb-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 22px !important;
  height: 22px !important;
  padding: 0 !important;
  z-index: 2;
  --el-button-bg-color: rgba(220, 38, 38, 0.92);
  --el-button-border-color: transparent;
  --el-button-hover-bg-color: rgba(248, 113, 113, 0.95);
  --el-button-hover-border-color: transparent;
}

.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-item--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(226, 232, 240, 0.45);
}

.image-upload-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-input {
  flex: 1;
  color: rgba(226, 232, 240, 0.65);
}

/* 点击“选择图片”时，真正触发 file input（通过透明覆盖层） */
.pick-files-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.file-input-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  z-index: 1;
}

.pick-files-btn {
  white-space: nowrap;
  position: relative;
  z-index: 0;
}

.selected-preview-grid {
  margin-top: 10px;
}
</style>
