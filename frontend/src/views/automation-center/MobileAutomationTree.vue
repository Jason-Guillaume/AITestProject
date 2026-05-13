<script setup lang="ts">
import type { Component } from 'vue'
import { Document, Iphone } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { HubTreeNode } from '@/composables/useScriptHubTrees'

const mobileTreeProps = { label: 'label', children: 'children', isLeaf: 'isLeaf' }

function loadMobileTree(
  node: { level: number; data: HubTreeNode },
  resolve: (data: HubTreeNode[]) => void,
) {
  if (node.level === 0) {
    resolve([
      {
        id: 'mobile-catalog-placeholder',
        label: 'Mobile Node 目录（接入中）',
        kind: 'mobile-placeholder',
        isLeaf: true,
      },
    ])
  } else {
    resolve([])
  }
}

function treeNodeIcon(d: HubTreeNode): Component {
  if (d.kind === 'mobile-placeholder') return Iphone
  return Document
}

function onMobileTreeNodeClick(data: HubTreeNode) {
  if (data.kind === 'mobile-placeholder') {
    ElMessage.info('移动端 Node 目录尚未接入，无法选中')
  }
}
</script>

<template>
  <div class="tree-pane">
    <div class="tree-panel-head">
      Mobile · Node Explorer
    </div>
    <div class="script-tree-scroll">
      <el-tree
        class="script-resource-tree"
        node-key="id"
        lazy
        :load="loadMobileTree"
        :props="mobileTreeProps"
        highlight-current
        @node-click="(data: HubTreeNode) => onMobileTreeNodeClick(data)"
      >
        <template #default="{ data }">
          <span class="script-tree-node">
            <el-icon class="script-tree-node__icon script-tree-node__icon--mobile">
              <component :is="treeNodeIcon(data)" />
            </el-icon>
            <span class="script-tree-node__label">{{ data.label }}</span>
          </span>
        </template>
      </el-tree>
    </div>
  </div>
</template>
