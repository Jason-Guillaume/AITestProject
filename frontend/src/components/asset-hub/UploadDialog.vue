<script setup lang="ts">
/**
 * 资产上传 / 初始化弹窗（无 Module 必填；打通上传与列表展示）
 */
import { reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadFiles } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'

export type UploadDialogMode = 'create' | 'edit'

export interface UploadFormPayload {
  displayName: string
  techStack: 'PYTHON' | 'JAVA'
  designMode: 'POM' | 'LINEAR'
  /** POM + ZIP：ZIP 包内执行入口相对路径 */
  pomEntryPath?: string
  files: File[]
}

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    mode: UploadDialogMode
    initialDisplayName?: string
    initialTechStack?: 'PYTHON' | 'JAVA'
    initialDesignMode?: 'POM' | 'LINEAR'
    hintRelPath?: string
    submitLoading?: boolean
  }>(),
  {
    initialDisplayName: '',
    initialTechStack: 'PYTHON',
    initialDesignMode: 'LINEAR',
    hintRelPath: '',
    submitLoading: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [boolean]
  submit: [payload: UploadFormPayload]
}>()

const form = reactive({
  displayName: '',
  techStack: 'PYTHON' as 'PYTHON' | 'JAVA',
  designMode: 'LINEAR' as 'POM' | 'LINEAR',
  pomEntryPath: '',
})

const dialogFileList = ref<{ raw?: File }[]>([])

function inferTechFromName(name: string): 'PYTHON' | 'JAVA' | null {
  const n = name.toLowerCase()
  if (n.endsWith('.py')) return 'PYTHON'
  if (n.endsWith('.java')) return 'JAVA'
  return null
}

function applyTechFromFileList(list: { raw?: File }[]) {
  for (const item of list) {
    const file = item.raw
    if (!file) continue
    const t = inferTechFromName(file.name)
    if (t) {
      form.techStack = t
      return
    }
  }
}

function syncFormFromProps() {
  form.displayName = props.initialDisplayName || ''
  form.techStack = props.initialTechStack || 'PYTHON'
  form.designMode = props.initialDesignMode || 'LINEAR'
  form.pomEntryPath = ''
  dialogFileList.value = []
}

watch(
  () => [props.modelValue, props.mode, props.initialDisplayName] as const,
  () => {
    if (props.modelValue) syncFormFromProps()
  },
)

function close() {
  emit('update:modelValue', false)
}

function beforeUpload(file: File) {
  const ok = /\.(py|java|json|jar|yaml|yml)$/i.test(file.name)
  if (!ok) ElMessage.warning('支持 .py / .java / .json / .jar / .yaml')
  return ok
}

function onFileChange(_f: UploadFile, list: UploadFiles) {
  dialogFileList.value = list as { raw?: File }[]
  applyTechFromFileList(dialogFileList.value)
}

function onConfirm() {
  const displayName = form.displayName.trim()
  if (!displayName) {
    ElMessage.warning('请填写脚本名称（别名）')
    return
  }
  const files = dialogFileList.value.map((x) => x.raw).filter((x): x is File => Boolean(x))
  if (props.mode === 'create' && files.length === 0) {
    ElMessage.warning('请上传脚本文件或选择本地物理文件')
    return
  }
  if (props.mode === 'create' && form.designMode === 'POM') {
    const first = files[0]
    if (first && !first.name.toLowerCase().endsWith('.zip')) {
      ElMessage.warning('POM 模式请上传 ZIP 工程包')
      return
    }
    const ep = form.pomEntryPath.trim()
    if (!ep) {
      ElMessage.warning('请填写 ZIP 包内的执行入口相对路径（如 tests/test_login.py）')
      return
    }
  }
  emit('submit', {
    displayName,
    techStack: form.techStack,
    designMode: form.designMode,
    pomEntryPath: form.pomEntryPath.trim(),
    files,
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="mode === 'create' ? '智能上传 · 资产登记' : '初始化脚本 · 补全配置'"
    width="520px"
    class="asset-hub-upload-dialog upload-dialog"
    modal-class="asset-hub-upload-overlay"
    destroy-on-close
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
  >
    <p
      v-if="hintRelPath"
      class="upload-dialog__hint"
    >
      物理路径：<code>{{ hintRelPath }}</code>
    </p>
    <el-form
      label-position="top"
      class="upload-dialog__form"
    >
      <el-form-item
        label="名称（系统别名）"
        required
      >
        <el-input
          v-model="form.displayName"
          placeholder="如 Playwright 登录流"
          maxlength="128"
          show-word-limit
          clearable
        />
      </el-form-item>

      <el-form-item
        label="语言 / 技术栈"
        required
      >
        <el-radio-group v-model="form.techStack">
          <el-radio-button label="PYTHON">
            Python
          </el-radio-button>
          <el-radio-button label="JAVA">
            Java
          </el-radio-button>
        </el-radio-group>
        <p class="upload-dialog__sub">
          拖拽 .py / .java 时会自动切换技术栈
        </p>
      </el-form-item>

      <el-form-item
        label="设计模式"
        required
      >
        <el-radio-group v-model="form.designMode">
          <el-radio-button label="POM">
            POM 模式
          </el-radio-button>
          <el-radio-button label="LINEAR">
            线性脚本
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item
        v-if="form.designMode === 'POM'"
        label="ZIP 内执行入口"
        required
      >
        <el-input
          v-model="form.pomEntryPath"
          placeholder="解压后相对工程根的路径，如 tests/login_flow.py"
          clearable
        />
      </el-form-item>

      <el-form-item :label="mode === 'create' ? '脚本文件' : '脚本文件（可选覆盖）'">
        <el-upload
          drag
          multiple
          :limit="8"
          :auto-upload="false"
          accept=".py,.java,.json,.jar,.yaml,.yml"
          :before-upload="beforeUpload"
          @change="onFileChange"
        >
          <el-icon class="upload-dialog__upload-ico">
            <Upload />
          </el-icon>
          <div>拖拽到此处，或点击选择本地物理文件</div>
          <template #tip>
            <span class="upload-dialog__tip">将提交到服务端并写入工作台工程（UI 自动化）；线性请传 .py，POM 请传 .zip。Java 请使用工作台导入。</span>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">
        取消
      </el-button>
      <el-button
        type="primary"
        :loading="submitLoading"
        @click="onConfirm"
      >
        {{ mode === 'create' ? '确认登记' : '保存初始化' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.upload-dialog__hint {
  margin: 0 0 12px;
  font-size: 12px;
  opacity: 0.85;
}
.upload-dialog__hint code {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--el-fill-color-dark);
}
.upload-dialog__sub {
  margin: 6px 0 0;
  font-size: 12px;
  opacity: 0.72;
}
.upload-dialog__upload-ico {
  font-size: 36px;
  color: var(--el-color-primary);
  margin-bottom: 8px;
}
.upload-dialog__tip {
  font-size: 12px;
  opacity: 0.75;
}
</style>
