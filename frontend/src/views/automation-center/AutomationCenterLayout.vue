<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import {
  DocumentChecked,
  VideoPlay,
  VideoPause,
  Operation,
} from '@element-plus/icons-vue'
import TerminalTerminal from '@/components/script/TerminalTerminal.vue'
import { useAutomationHubCore } from '@/composables/useAutomationHubCore'
import WebExecParamsFields from '@/components/automation-center/WebExecParamsFields.vue'
import MobileExecParamsFields from '@/components/automation-center/MobileExecParamsFields.vue'
import ApiExecParamsFields from '@/components/automation-center/ApiExecParamsFields.vue'
import MiniprogramExecParamsFields from '@/components/automation-center/MiniprogramExecParamsFields.vue'
import H5ExecParamsFields from '@/components/automation-center/H5ExecParamsFields.vue'

import './automation-center-workstation.css'

const MonacoEditor = defineAsyncComponent(() => import('@/components/MonacoEditor/index.vue'))
const MobileWorkspaceShell = defineAsyncComponent(
  () => import('@/components/automation-center/MobileWorkspaceShell.vue'),
)

const route = useRoute()

const { hub, hubTerminalRef } = useAutomationHubCore()

const isWebPlatform = computed(() => hub.activePlatform === 'web')

const isCrossPlaceholder = computed(
  () => hub.activePlatform === 'miniprogram' || hub.activePlatform === 'h5',
)

const crossPlaceholderDescription = computed(() =>
  hub.activePlatform === 'miniprogram'
    ? '微信小程序脚本：脚本树、开发者工具与真机执行接入中'
    : 'H5 页面脚本：脚本树、浏览器 / WebView 执行接入中',
)

const crossPlaceholderHint = computed(() =>
  hub.activePlatform === 'miniprogram'
    ? '遥测面板与 Web 共用；后续小程序执行日志将写入此处。'
    : '遥测面板与 Web 共用；后续 H5 执行日志将写入此处。',
)
</script>

<template>
  <div class="automation-center-hub script-hub script-hub--cyber">
    <section class="script-hub__workarea">
      <div
        class="workstation-panel workstation-panel--ide"
        :class="{
          'is-inspector-open': hub.inspectorOpen,
          [`layout-profile--${hub.layoutProfile.inspectorVariant}`]: true,
        }"
      >
        <aside class="workstation-panel__col workstation-panel__col--tree">
          <router-view :key="route.path" />
        </aside>

        <div class="workstation-panel__col workstation-panel__col--main ide-center">
          <header class="action-header">
            <el-button
              plain
              class="action-header__btn"
              :icon="DocumentChecked"
              :loading="hub.saveLoading"
              :disabled="!hub.canSave || isCrossPlaceholder"
              @click="hub.onSaveClick"
            >
              保存
            </el-button>
            <el-button
              plain
              class="action-header__btn action-header__btn--exec-config"
              :icon="Operation"
              @click="hub.paramsDrawerVisible = true"
            >
              执行配置
            </el-button>
            <el-button
              plain
              class="action-header__btn action-header__btn--exec"
              :class="{ 'action-header__btn--exec-running': hub.executeLoading }"
              :icon="VideoPlay"
              :loading="hub.executeLoading"
              :disabled="!isWebPlatform"
              @click="hub.onExecuteClick"
            >
              执行
            </el-button>
            <el-button
              plain
              class="action-header__btn action-header__btn--stop"
              :icon="VideoPause"
              :disabled="!hub.executeLoading"
              @click="hub.onStopClick"
            >
              停止
            </el-button>
            <div class="action-header__spacer" />
          </header>

          <component
            :is="MobileWorkspaceShell"
            v-show="hub.activePlatform === 'mobile'"
            class="workspace-main-mount workspace-main-mount--mobile"
          />
          <div
            v-show="hub.activePlatform === 'web' || hub.activePlatform === 'api'"
            class="editor-stack workspace-main-mount"
          >
            <p class="editor-path" :title="hub.editorChromeTitle">{{ hub.editorChromeTitle }}</p>
            <div v-loading="hub.editorLoading" class="monaco-wrap">
              <p v-if="!hub.isEditorReady" class="editor-defer-hint">编辑器初始化中（500ms 受控唤醒）…</p>
              <MonacoEditor
                v-if="hub.isEditorReady"
                v-model="hub.editorContent"
                :language="hub.editorLanguage"
                :read-only="hub.editorReadOnly"
                copilot-bridge-id="automation-center-main"
                :copilot-label="hub.editorChromeTitle"
              />
            </div>
          </div>
          <div
            v-show="isCrossPlaceholder"
            class="workspace-main-mount workspace-main-mount--cross-placeholder"
          >
            <el-empty :description="crossPlaceholderDescription" :image-size="96" />
            <p class="ac-cross-main__hint">{{ crossPlaceholderHint }}</p>
          </div>

          <div class="bottom-telemetry-zone">
            <div class="bottom-telemetry-zone__row">
              <el-tabs v-model="hub.bottomTab" class="bottom-tabs bottom-telemetry-zone__tabs">
                <el-tab-pane label="Telemetry（遥测流）" name="telemetry">
                  <div class="bottom-pane bottom-pane--terminal">
                    <TerminalTerminal
                      ref="hubTerminalRef"
                      :fit-when-active="hub.bottomTab === 'telemetry'"
                    />
                  </div>
                </el-tab-pane>
                <el-tab-pane label="Artifacts（产物）" name="artifacts">
                  <div class="bottom-pane bottom-pane--artifacts">
                    <el-empty
                      description="Artifacts：报告截图、日志包、结构化导出将汇总于此（执行结束后可从 Telemetry 侧栏进入 Analysis Lab）"
                      :image-size="56"
                    />
                  </div>
                </el-tab-pane>
              </el-tabs>
              <button
                v-show="hub.showAnalysisLabDeepLink && hub.bottomTab === 'telemetry'"
                type="button"
                class="analysis-lab-glow-btn"
                title="打开 Analysis Lab 深度报告（演示深链）"
                @click="hub.goAnalysisLabDeepLink"
              >
                [↗ Analysis Lab]
              </button>
            </div>
          </div>

          <button
            v-show="!hub.inspectorOpen"
            type="button"
            class="inspector-reopen"
            title="展开 Inspector"
            @click="hub.inspectorOpen = true"
          >
            ⟨
          </button>
        </div>

        <aside v-show="hub.inspectorOpen" class="workstation-panel__col workstation-panel__col--inspector">
          <div class="inspector-head">
            <span class="inspector-head__title">{{ hub.inspectorHeadTitle }}</span>
            <el-button text type="primary" class="inspector-head__collapse" @click="hub.inspectorOpen = false">
              折叠
            </el-button>
          </div>
          <div class="inspector-body">
            <section class="inspector-block">
              <h4 class="inspector-block__h">节点元数据 (Node Metadata)</h4>
              <p class="inspector-block__placeholder">{{ hub.inspectorMetadataPlaceholder }}</p>
            </section>
            <section class="inspector-block">
              <h4 class="inspector-block__h">最近一次 Telemetry 状态</h4>
              <p class="inspector-block__mono inspector-block__mono--status">{{ hub.lastTelemetryStatusDisplay }}</p>
            </section>
          </div>
        </aside>
      </div>
    </section>

    <el-drawer
      v-model="hub.paramsDrawerVisible"
      title="执行配置"
      direction="rtl"
      size="360px"
      append-to-body
      class="params-drawer params-drawer--cyber"
    >
      <WebExecParamsFields
        v-if="hub.activePlatform === 'web'"
        v-model:browser-type="hub.browserType"
        v-model:is-headless="hub.isHeadless"
        v-model:parallel-count="hub.parallelCount"
        :execute-loading="hub.executeLoading"
      />
      <MobileExecParamsFields
        v-else-if="hub.activePlatform === 'mobile'"
        v-model:mobile-device-placeholder="hub.mobileDevicePlaceholder"
        v-model:mobile-package-name="hub.mobilePackageName"
      />
      <MiniprogramExecParamsFields v-else-if="hub.activePlatform === 'miniprogram'" />
      <H5ExecParamsFields v-else-if="hub.activePlatform === 'h5'" />
      <ApiExecParamsFields v-else />
    </el-drawer>
  </div>
</template>

<style>
.params-drawer.params-drawer--cyber.el-drawer {
  --el-drawer-bg-color: transparent;
  background: rgba(8, 12, 22, 0.58) !important;
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  box-shadow: -16px 0 56px rgba(0, 0, 0, 0.5);
}

.params-drawer--cyber .el-drawer__header {
  margin-bottom: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 240, 255, 0.12);
}

.params-drawer--cyber .el-drawer__title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: rgba(226, 232, 240, 0.95);
}

.params-drawer--cyber .el-drawer__body {
  padding: 16px 18px 24px;
  color: rgba(226, 232, 240, 0.9);
  background: linear-gradient(165deg, rgba(12, 18, 32, 0.42), rgba(6, 10, 20, 0.28));
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.params-drawer__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.params-drawer__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.params-drawer__row--top {
  align-items: flex-start;
}

.params-drawer__row--switch {
  align-items: center;
}

.params-drawer__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(203, 213, 225, 0.92);
  flex-shrink: 0;
}

.params-drawer__hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.88);
}

.params-drawer__select {
  flex: 1;
  min-width: 0;
}

.params-drawer__input {
  flex: 1;
  min-width: 0;
}

.params-drawer--cyber .headless-switch--cyber .el-switch:not(.is-checked) .el-switch__core {
  border-color: rgba(167, 139, 250, 0.42);
  background: rgba(30, 27, 48, 0.88);
  box-shadow:
    0 0 6px rgba(139, 92, 246, 0.2),
    0 0 14px rgba(167, 139, 250, 0.1);
}

.params-drawer--cyber .headless-switch--cyber .el-switch.is-checked .el-switch__core {
  background-color: #00f0ff;
  border-color: #00f0ff;
  box-shadow:
    0 0 8px rgba(0, 240, 255, 0.5),
    0 0 20px rgba(0, 240, 255, 0.32);
}

.params-drawer--cyber .headless-switch--cyber .el-switch.is-checked .el-switch__inner {
  color: rgba(8, 20, 26, 0.92);
}

.params-drawer--cyber .headless-switch--cyber .el-switch:not(.is-checked) .el-switch__inner {
  color: rgba(230, 214, 255, 0.92);
}
</style>
