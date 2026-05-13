<template>
  <div class="cyber-page pipeline-create-page">
    <el-card
      class="admin-list-card"
      shadow="never"
    >
      <template #header>
        <div class="hdr">
          <el-button
            text
            type="primary"
            @click="router.push('/pipelines')"
          >
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
          <div class="hdr__titles">
            <span class="page-title">新建构建项目</span>
            <span class="page-sub">选择 Jenkins 风格的项目类型并配置 Shell 构建脚本</span>
          </div>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        class="create-form"
      >
        <el-form-item
          label="项目类型"
          prop="kind"
        >
          <el-radio-group v-model="form.kind">
            <el-radio-button :value="0">
              自由风格
            </el-radio-button>
            <el-radio-button :value="1">
              流水线脚本
            </el-radio-button>
          </el-radio-group>
          <div class="hint">
            <template v-if="form.kind === 0">
              单次 Shell 执行，适合编译、脚本、调用工具链等。
            </template>
            <template v-else>
              按行首「<code># stage: 名称</code>」拆成多个阶段依次执行；任一段失败则构建失败。
            </template>
          </div>
        </el-form-item>
        <el-form-item
          label="名称"
          prop="name"
        >
          <el-input
            v-model="form.name"
            maxlength="255"
            show-word-limit
            placeholder="例如：订单服务 nightly 构建"
          />
        </el-form-item>
        <el-form-item
          label="代码仓库"
          prop="repo_url"
        >
          <el-input
            v-model="form.repo_url"
            clearable
            placeholder="可选，https://…（后续可与克隆步骤结合）"
          />
        </el-form-item>
        <el-form-item
          label="构建脚本"
          prop="build_definition"
        >
          <div class="script-toolbar">
            <el-button
              size="small"
              @click="fillTemplate"
            >
              填入示例脚本
            </el-button>
          </div>
          <el-input
            v-model="form.build_definition"
            type="textarea"
            :rows="14"
            placeholder="Shell 脚本（bash）。保存后可在详情页修改并触发构建。"
            class="mono-input"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="submitting"
            @click="submit"
          >
            创建并进入配置
          </el-button>
          <el-button @click="router.push('/pipelines')">
            取消
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { createPipelineApi } from '@/api/project'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  kind: 0,
  name: '',
  repo_url: '',
  build_definition: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

watch(
  () => route.query.kind,
  (k) => {
    const v = Array.isArray(k) ? k[0] : k
    if (v === '1') form.kind = 1
    else if (v === '0') form.kind = 0
  },
  { immediate: true }
)

const TEMPLATE_FREESTYLE = `set -e
echo "=== 自由风格示例 ==="
uname -a
# 在此编写你的命令，例如：
# npm ci && npm run build
`

const TEMPLATE_PIPELINE = `set -e
# stage: 检出
echo "此处可写 git clone / fetch …"

# stage: 构建
echo "编译、打包 …"

# stage: 测试
echo "单元测试 / 静态检查 …"
`

function fillTemplate() {
  form.build_definition = form.kind === 0 ? TEMPLATE_FREESTYLE : TEMPLATE_PIPELINE
}

async function submit() {
  if (!formRef.value) return
  await formRef.value.validate().catch(() => Promise.reject())
  submitting.value = true
  try {
    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      kind: form.kind,
      build_definition: form.build_definition,
    }
    const ru = form.repo_url.trim()
    if (ru) payload.repo_url = ru
    const { data } = await createPipelineApi(payload)
    const id = data?.id
    if (!id) {
      ElMessage.error('创建成功但未返回 ID')
      return
    }
    ElMessage.success('已创建')
    router.replace(`/pipelines/${id}`)
  } catch {
    /* 全局错误提示 */
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.pipeline-create-page {
  padding: 16px;
  min-height: calc(100vh - 120px);
  box-sizing: border-box;
}

.hdr {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.hdr__titles {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
}

.page-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.create-form {
  max-width: 920px;
}

.hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.script-toolbar {
  margin-bottom: 8px;
}

.mono-input :deep(textarea) {
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
}
</style>
