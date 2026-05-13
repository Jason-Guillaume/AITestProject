<template>
  <div class="layout sw-cyber">
    <aside class="sw-cyber-panel col-tree">
      <div class="panel-head sw-glow-text">
        POM / 工程结构
      </div>
      <el-tree
        :key="wb.uiTreeKey"
        class="tree"
        lazy
        :load="wb.loadUiTreeNode"
        :props="{ label: 'label', children: 'children', isLeaf: 'isLeaf' }"
        highlight-current
        @node-click="wb.onUiTreeClick"
      />
    </aside>
    <div class="col-main">
      <div class="sw-cyber-panel is-active row-toolbar">
        <el-button
          class="ghost-btn"
          :icon="Plus"
          @click="wb.openImport"
        >
          导入
        </el-button>
        <el-button
          class="ghost-btn"
          :loading="wb.saveLoading"
          :disabled="!wb.canSaveEditor"
          @click="wb.saveEditor"
        >
          保存
        </el-button>
        <el-button
          class="ghost-btn accent"
          :icon="VideoPlay"
          :disabled="!hasProject"
          :loading="ui.isRunning"
          @click="wb.runExecution"
        >
          {{ ui.isRunning ? '执行中' : '执行' }}
        </el-button>
        <el-button
          class="ghost-btn danger"
          :icon="VideoPause"
          :disabled="!ui.isRunning || !ui.currentExecutionId || wb.stopExecutionLoading"
          :loading="wb.stopExecutionLoading"
          @click="wb.stopExecution"
        >
          停止
        </el-button>
      </div>

      <div class="sw-cyber-panel row-editor">
        <div class="exec-row">
          <span class="muted">浏览器</span>
          <el-select
            v-model="wb.executionConfig.browser"
            size="small"
            class="mini-sel"
          >
            <el-option
              label="Chrome"
              value="chrome"
            />
            <el-option
              label="Firefox"
              value="firefox"
            />
            <el-option
              label="Edge"
              value="edge"
            />
          </el-select>
          <el-radio-group
            v-model="wb.executionConfig.headless"
            size="small"
          >
            <el-radio-button :label="false">
              有头
            </el-radio-button>
            <el-radio-button :label="true">
              无头
            </el-radio-button>
          </el-radio-group>
          <span class="muted">并发</span>
          <el-input-number
            v-model="wb.executionConfig.parallel"
            :min="1"
            :max="10"
            size="small"
          />
        </div>
        <p class="path sw-glow-text">
          {{ wb.editorTitle || '未选择文件' }}
        </p>
        <div
          v-loading="wb.editorLoading"
          class="monaco-box"
        >
          <Suspense v-if="showMonaco">
            <template #default>
              <MonacoEditor
                :key="wb.monacoKeyUi"
                v-model="wb.editorContent"
                :language="wb.editorLanguage"
                :read-only="!wb.editorPath"
              />
            </template>
            <template #fallback>
              <div class="monaco-ph">
                加载编辑器组件…
              </div>
            </template>
          </Suspense>
          <div
            v-else
            class="monaco-ph"
          >
            准备编辑器…
          </div>
        </div>
      </div>

      <div class="sw-cyber-panel row-pipeline">
        <div class="panel-head sw-glow-text">
          截图 / 录屏流水线
        </div>
        <el-steps
          :active="pipelineActive"
          simple
          class="steps"
        >
          <el-step title="用例开始" />
          <el-step title="关键步骤截图" />
          <el-step title="失败自动录屏" />
          <el-step title="归档报告" />
        </el-steps>
        <div class="preview-strip">
          <div
            v-for="i in 4"
            :key="i"
            class="thumb sw-cyber-panel"
          >
            <span class="thumb-label">Step {{ i }}</span>
            <el-empty
              description="等待执行产出"
              :image-size="48"
            />
          </div>
        </div>
      </div>

      <el-tabs
        v-model="wb.mainTab"
        class="bottom-tabs"
      >
        <el-tab-pane
          label="最近报告"
          name="report"
        >
          <div class="report-grid">
            <div class="sw-cyber-panel report-side">
              <div class="panel-head">
                POM 归档
              </div>
              <el-table
                v-loading="wb.pomLoading"
                :data="wb.pomRows"
                size="small"
                :border="false"
                max-height="220"
                class="tbl"
                highlight-current-row
                @row-click="(r: unknown) => wb.onPomRowClick(r)"
              >
                <el-table-column
                  prop="title"
                  label="标题"
                  min-width="120"
                  show-overflow-tooltip
                />
                <el-table-column
                  prop="execution_status"
                  label="状态"
                  width="64"
                />
              </el-table>
            </div>
            <div class="sw-cyber-panel report-frame">
              <iframe
                v-if="wb.reportIframeUrl"
                class="iframe"
                title="r"
                :src="wb.reportIframeUrl"
              />
              <el-empty
                v-else
                description="选中表格行预览 HTML"
                :image-size="64"
              />
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane
          label="终端"
          name="terminal"
        >
          <div
            :ref="(el) => bindTermScroll(el as HTMLElement | null)"
            class="term sw-cyber-panel"
          >
            <template v-if="ui.logs.length === 0">
              <span class="term-idle">$ idle</span>
            </template>
            <div
              v-for="(log, idx) in ui.logs"
              :key="idx"
              class="term-line"
            >
              {{ log.time }} {{ log.message }}
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, unref, ref, onMounted, onBeforeUnmount } from 'vue'
import { Plus, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import { defineAsyncComponent } from 'vue'
import { SCRIPT_WORKBENCH_INJECT } from './workbenchInject'

const MonacoEditor = defineAsyncComponent(() => import('@/components/MonacoEditor/index.vue'))

const showMonaco = ref(false)
let monacoDeferTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  monacoDeferTimer = window.setTimeout(() => {
    showMonaco.value = true
    monacoDeferTimer = null
  }, 2000)
})

onBeforeUnmount(() => {
  if (monacoDeferTimer != null) {
    clearTimeout(monacoDeferTimer)
    monacoDeferTimer = null
  }
})

const wb = inject(SCRIPT_WORKBENCH_INJECT)!
const ui = wb.uiStore
const hasProject = computed(() => !!unref(wb.selectedProject)?.id)
const pipelineActive = computed(() => {
  if (ui.isRunning) return 2
  if (ui.result && !ui.result.pending) return 4
  return 1
})

function bindTermScroll(el: HTMLElement | null) {
  wb.terminalScrollRef.value = el
}
</script>

<style scoped src="./panelCyber.css"></style>
<style scoped>
.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 14px;
  min-height: 640px;
  align-items: stretch;
}
.col-tree {
  padding: 12px;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.panel-head {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
  margin-bottom: 10px;
}
.tree {
  flex: 1;
  overflow: auto;
  background: transparent !important;
  --el-tree-node-hover-bg-color: rgba(0, 240, 255, 0.06);
}
.col-main {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.row-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 12px;
}
.ghost-btn {
  background: transparent !important;
  border: 1px solid rgba(0, 240, 255, 0.1) !important;
  color: rgba(255, 255, 255, 0.85) !important;
}
.ghost-btn:hover {
  border-color: rgba(0, 240, 255, 0.8) !important;
  box-shadow: 0 0 15px rgba(0, 240, 255, 0.2) !important;
}
.ghost-btn.accent {
  border-color: rgba(0, 240, 255, 0.35) !important;
}
.ghost-btn.danger {
  border-color: rgba(248, 113, 113, 0.35) !important;
}
.row-editor {
  padding: 12px;
  flex: 1;
  min-height: 280px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.exec-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.muted {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}
.mini-sel {
  width: 120px;
}
.path {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: rgba(0, 240, 255, 0.9);
}
.monaco-box {
  flex: 1;
  min-height: 220px;
  border-radius: 8px;
  overflow: hidden;
}
.monaco-box :deep(.monaco-editor-root) {
  border: none !important;
}
.monaco-ph {
  flex: 1;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.06em;
}
.row-pipeline {
  padding: 12px;
}
.steps {
  margin: 8px 0 14px;
}
.preview-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
@media (max-width: 1100px) {
  .preview-strip {
    grid-template-columns: repeat(2, 1fr);
  }
}
.thumb {
  min-height: 120px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.thumb-label {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  margin-bottom: 4px;
}
.bottom-tabs :deep(.el-tabs__header) {
  margin: 0;
}
.bottom-tabs :deep(.el-tabs__item.is-active) {
  color: #00f0ff;
  text-shadow: 0 0 8px rgba(0, 240, 255, 0.5);
}
.report-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 12px;
}
.report-side,
.report-frame {
  padding: 10px;
  min-height: 240px;
}
.iframe {
  width: 100%;
  height: 220px;
  border: none;
  background: #fff;
}
.tbl {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-border-color: transparent;
}
.term {
  padding: 12px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #86efac;
  max-height: 220px;
  overflow: auto;
}
.term-idle {
  opacity: 0.45;
}
.term-line {
  margin-bottom: 4px;
}
.hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  margin: 0;
}
@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
