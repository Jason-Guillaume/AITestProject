<script setup lang="ts">
import type { Component } from 'vue'
import { Document, Link, Tickets } from '@element-plus/icons-vue'
import { useScriptHubSelectionStore } from '@/stores/scriptHubSelectionStore'
import {
  createScriptHubTreeLoader,
  type HubTreeNode,
  type ScriptHubEdition,
} from '@/composables/useScriptHubTrees'

const hubSelection = useScriptHubSelectionStore()
const apiTree = createScriptHubTreeLoader('api', (id) => hubSelection.setSelectedScriptId(id))

function treeNodeIcon(edition: ScriptHubEdition, d: HubTreeNode): Component {
  if (edition === 'api') {
    if (d.kind === 'api-group') return Link
    if (d.kind === 'api-case') return Tickets
  }
  return Document
}

function onTreeNodeClick(data: HubTreeNode) {
  apiTree.onNodeClick(null, data)
}
</script>

<template>
  <div class="tree-pane">
    <div class="tree-panel-head">API · Node Explorer</div>
    <div class="script-tree-scroll">
      <el-tree
        class="script-resource-tree"
        node-key="id"
        lazy
        :load="apiTree.load"
        :props="apiTree.treeProps"
        highlight-current
        @node-click="(data: HubTreeNode) => onTreeNodeClick(data)"
      >
        <template #default="{ data }">
          <span class="script-tree-node">
            <el-icon class="script-tree-node__icon script-tree-node__icon--api">
              <component :is="treeNodeIcon('api', data)" />
            </el-icon>
            <span class="script-tree-node__label">{{ data.label }}</span>
          </span>
        </template>
      </el-tree>
    </div>
  </div>
</template>
