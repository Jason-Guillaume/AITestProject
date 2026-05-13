<template>
  <div
    v-if="!pipelineId"
    class="cyber-page pipeline-detail-page"
  >
    <el-empty description="无效的流水线 ID" />
    <el-button
      type="primary"
      @click="router.push('/pipelines')"
    >
      返回列表
    </el-button>
  </div>
  <div
    v-else
    class="cyber-page pipeline-detail-page"
  >
    <div class="detail-top">
      <el-button
        text
        type="primary"
        @click="router.push('/pipelines')"
      >
        <el-icon><ArrowLeft /></el-icon>
        返回列表
      </el-button>
      <el-tag
        v-if="loaded"
        type="info"
      >
        {{ kindLabel(form.kind) }}
      </el-tag>
      <el-tag
        v-if="loaded"
        :type="statusTagType(detail?.status)"
      >
        {{ statusLabel(detail?.status) }}
      </el-tag>
    </div>

    <el-row
      :gutter="16"
      class="detail-grid"
    >
      <el-col
        :xs="24"
        :lg="11"
      >
        <el-card
          v-loading="loading"
          shadow="never"
          class="panel-card"
        >
          <template #header>
            项目配置
          </template>
          <el-form
            :model="form"
            label-position="top"
            class="config-form"
          >
            <el-form-item label="名称">
              <el-input
                v-model="form.name"
                maxlength="255"
                show-word-limit
              />
            </el-form-item>
            <el-form-item label="项目类型">
              <el-radio-group v-model="form.kind">
                <el-radio-button :value="0">
                  自由风格
                </el-radio-button>
                <el-radio-button :value="1">
                  流水线脚本
                </el-radio-button>
              </el-radio-group>
              <p class="mini-hint">
                流水线脚本支持用「<code># stage: 阶段名</code>」拆段执行；自由风格为整段 Shell 一次执行。
              </p>
            </el-form-item>
            <el-form-item label="代码仓库（可选）">
              <el-input
                v-model="form.repo_url"
                clearable
                placeholder="https://…"
              />
            </el-form-item>
            <el-form-item label="构建脚本（Shell）">
              <el-input
                v-model="form.build_definition"
                type="textarea"
                :rows="12"
                class="mono-input"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="saving"
                :disabled="!loaded"
                @click="save"
              >
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card
          shadow="never"
          class="panel-card run-card"
        >
          <template #header>
            触发构建
          </template>
          <p class="mini-hint">
            留空则使用上方已保存的构建脚本；填写则仅本次构建覆盖（不写入配置）。
          </p>
          <el-input
            v-model="runOverride"
            type="textarea"
            :rows="4"
            placeholder="可选：本次临时 Shell（覆盖已保存脚本）"
            class="mono-input"
          />
          <el-checkbox
            v-model="clearLogsBeforeRun"
            class="chk"
          >
            执行前清空控制台历史日志
          </el-checkbox>
          <div class="run-actions">
            <el-button
              type="success"
              :loading="running"
              :disabled="!loaded"
              @click="runBuild"
            >
              立即构建
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col
        :xs="24"
        :lg="13"
      >
        <div class="console-host">
          <PipelineConsole
            :pipeline-id="pipelineId"
            :reset-nonce="consoleNonce"
          />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getPipelineApi, runPipelineApi, updatePipelineApi } from '@/api/project'
import PipelineConsole from '@/components/PipelineConsole.vue'

const route = useRoute()
const router = useRouter()

const pipelineId = computed(() => {
  const n = Number(route.params.id)
  return Number.isFinite(n) && n > 0 ? n : 0
})

const loading = ref(false)
const saving = ref(false)
const running = ref(false)
const loaded = ref(false)
const detail = ref<{ status?: number; kind?: number } | null>(null)
const form = reactive({
  name: '',
  kind: 0,
  repo_url: '',
  build_definition: '',
})
const runOverride = ref('')
const clearLogsBeforeRun = ref(false)
const consoleNonce = ref(0)

function kindLabel(k?: number) {
  return k === 1 ? '流水线脚本' : '自由风格'
}

function statusLabel(s?: number) {
  const m: Record<number, string> = { 0: '待执行', 1: '运行中', 2: '成功', 3: '失败' }
  if (s === undefined || s === null) return '—'
  return m[s] ?? String(s)
}

function statusTagType(s?: number): 'info' | 'warning' | 'success' | 'danger' {
  if (s === 1) return 'warning'
  if (s === 2) return 'success'
  if (s === 3) return 'danger'
  return 'info'
}

async function load() {
  const id = pipelineId.value
  if (!id) {
    loaded.value = false
    return
  }
  loading.value = true
  loaded.value = false
  try {
    const { data } = await getPipelineApi(id)
    detail.value = data
    form.name = data?.name ?? ''
    form.kind = data?.kind === 1 ? 1 : 0
    form.repo_url = data?.repo_url ?? ''
    form.build_definition = data?.build_definition ?? ''
    loaded.value = true
  } catch {
    detail.value = null
    loaded.value = false
  } finally {
    loading.value = false
  }
}

async function save() {
  const id = pipelineId.value
  if (!id) return
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      kind: form.kind,
      build_definition: form.build_definition,
    }
    const ru = form.repo_url.trim()
    payload.repo_url = ru || null
    const { data } = await updatePipelineApi(id, payload)
    detail.value = data
    ElMessage.success('已保存')
  } catch {
    /* */
  } finally {
    saving.value = false
  }
}

async function runBuild() {
  const id = pipelineId.value
  if (!id) return
  running.value = true
  try {
    const cmd = runOverride.value.trim()
    await runPipelineApi(id, {
      command: cmd || undefined,
      clear_logs: clearLogsBeforeRun.value,
    })
    ElMessage.success('已排队执行，请查看右侧日志')
    if (clearLogsBeforeRun.value) consoleNonce.value += 1
    await load()
  } catch {
    /* */
  } finally {
    running.value = false
  }
}

watch(pipelineId, () => load(), { immediate: true })
</script>

<style scoped>
.pipeline-detail-page {
  padding: 16px;
  box-sizing: border-box;
  min-height: calc(100vh - 100px);
}

.detail-top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.detail-grid {
  align-items: stretch;
}

.panel-card {
  margin-bottom: 16px;
}

.run-card .mini-hint {
  margin-bottom: 10px;
}

.chk {
  display: block;
  margin: 12px 0 8px;
}

.run-actions {
  margin-top: 8px;
}

.console-host {
  min-height: 420px;
  height: calc(100vh - 200px);
}

.console-host :deep(.pipeline-console) {
  height: 100%;
}

.mini-hint {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.45;
}

.config-form :deep(.mono-input textarea) {
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
}
</style>
