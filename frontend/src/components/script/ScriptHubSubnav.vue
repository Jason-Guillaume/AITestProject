<template>
  <div class="script-hub-subnav">
    <el-button
      v-if="showScriptHub"
      text
      type="primary"
      @click="goScriptHub"
    >
      返回自动化指挥中心
    </el-button>
    <el-button
      text
      type="primary"
      @click="goDashboard"
    >
      返回工作台
    </el-button>
    <el-button
      v-if="showWebUiTrash"
      text
      type="warning"
      @click="goWebUiTrash"
    >
      Web UI 回收站
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

withDefaults(
  defineProps<{
    /** 是否显示「返回脚本执行中心」（脚本中心首页本身为 false） */
    showScriptHub?: boolean
    /** 是否显示直达 Web UI 回收站（工作台内已有切换时可关） */
    showWebUiTrash?: boolean
  }>(),
  {
    showScriptHub: true,
    showWebUiTrash: true,
  }
)

const router = useRouter()

function goScriptHub() {
  router.push('/automation-center')
}

function goDashboard() {
  router.push('/dashboard')
}

function goWebUiTrash() {
  router.push({ path: '/automation-center/webui', query: { listMode: 'trash' } })
}
</script>

<style scoped>
.script-hub-subnav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-bottom: 14px;
}
</style>
