<script setup lang="ts">
import type { Component } from 'vue'
import { ref, watch } from 'vue'
import { Monitor, Folder, Document, Reading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useScriptHubSelectionStore } from '@/stores/scriptHubSelectionStore'
import { useAutomationCenterHubStore } from '@/stores/automationCenterHubStore'
import {
  createScriptHubTreeLoader,
  type HubTreeNode,
  type ScriptHubEdition,
} from '@/composables/useScriptHubTrees'
import ExplorerNodeContextMenu from '@/components/explorer/ExplorerNodeContextMenu.vue'
import request from '@/utils/request'

const hubSelection = useScriptHubSelectionStore()
const automationHub = useAutomationCenterHubStore()
const uiTree = createScriptHubTreeLoader('ui', (id) => hubSelection.setSelectedScriptId(id))

const treeKey = ref(0)

watch(
  () => automationHub.explorerRefreshTick,
  () => {
    treeKey.value += 1
  },
)

function treeNodeIcon(edition: ScriptHubEdition, d: HubTreeNode): Component {
  if (edition === 'ui') {
    if (d.kind === 'project') return Monitor
    if (d.kind === 'dir') return Folder
    if (d.kind === 'file') return Document
    if (d.kind === 'online') return Reading
  }
  return Document
}

function onTreeNodeClick(data: HubTreeNode) {
  uiTree.onNodeClick(null, data)
}

function nodePathLabel(data: HubTreeNode): string {
  if (data.kind === 'project' && data.projectId != null) {
    return `ui:project:${data.projectId}`
  }
  if (data.relPath) return data.relPath
  if (data.kind === 'online' && data.projectId != null) return `online:${data.projectId}`
  return data.label || ''
}

async function onTreeContextCommand(cmd: string, data: HubTreeNode) {
  if (cmd === 'copy-path') {
    const text = nodePathLabel(data)
    if (!text) {
      ElMessage.warning('无可用路径')
      return
    }
    try {
      await navigator.clipboard.writeText(text)
      ElMessage.success('已复制路径')
    } catch {
      ElMessage.error('复制失败')
    }
    return
  }
  if (cmd === 'rename' || cmd === 'new-node' || cmd === 'new-folder') {
    ElMessage.info('该能力即将接入，请先在 WebUI 工作台管理脚本与目录')
    return
  }
  if (cmd !== 'delete') return

  if (data.kind !== 'project' || !data.projectId) {
    ElMessage.warning('仅支持将脚本工程（根 Node）移入回收站；工作区文件请在 WebUI 工作台操作')
    return
  }

  try {
    await ElMessageBox.confirm('确定将该脚本移入回收站吗？', '移入回收站', {
      type: 'warning',
      confirmButtonText: '移入回收站',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await request.patch(`/assistant/ui-scripts/${data.projectId}/`, { is_deleted: true })
    ElMessage.success('Node 已移入回收站')
    hubSelection.setSelectedScriptId(null)
    treeKey.value += 1
  } catch (e: unknown) {
    const err = e as { response?: { data?: { error?: string; detail?: string } }; message?: string }
    const d = err.response?.data
    const detail =
      (typeof d?.error === 'string' && d.error) ||
      (typeof d?.detail === 'string' && d.detail) ||
      err.message ||
      '未知错误'
    ElMessage.error('操作失败：' + detail)
  }
}
</script>

<template>
  <div class="tree-pane">
    <div class="tree-panel-head">Web · Node Explorer</div>
    <div class="script-tree-scroll">
      <el-tree
        :key="treeKey"
        class="script-resource-tree"
        node-key="id"
        lazy
        :load="uiTree.load"
        :props="uiTree.treeProps"
        highlight-current
        @node-click="(data: HubTreeNode) => onTreeNodeClick(data)"
      >
        <template #default="{ data }">
          <ExplorerNodeContextMenu
            :disable-delete="data.kind !== 'project'"
            :disable-copy-path="!nodePathLabel(data)"
            :disable-new="data.kind !== 'project' && data.kind !== 'dir'"
            :disable-rename="data.kind !== 'project' && data.kind !== 'file' && data.kind !== 'dir' && data.kind !== 'online'"
            @command="(c: string) => onTreeContextCommand(c, data)"
          >
            <span class="script-tree-node">
              <el-icon class="script-tree-node__icon script-tree-node__icon--ui">
                <component :is="treeNodeIcon('ui', data)" />
              </el-icon>
              <span class="script-tree-node__label">{{ data.label }}</span>
            </span>
          </ExplorerNodeContextMenu>
        </template>
      </el-tree>
    </div>
  </div>
</template>
