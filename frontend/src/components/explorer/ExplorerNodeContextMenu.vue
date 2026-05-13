<script setup>
import {
  DocumentAdd,
  FolderAdd,
  EditPen,
  Link,
  Delete,
} from '@element-plus/icons-vue'
import { vContextmenuBlockNative } from '@/directives/contextmenuBlockNative'

const emit = defineEmits(['command'])

defineProps({
  disableNew: { type: Boolean, default: false },
  disableRename: { type: Boolean, default: false },
  disableDelete: { type: Boolean, default: false },
  disableCopyPath: { type: Boolean, default: false },
  /** folder：Module 树右键，隐藏「新建 Node」，文案侧重文件夹 */
  variant: { type: String, default: 'node' },
})

function onCommand(cmd) {
  emit('command', cmd)
}
</script>

<template>
  <el-dropdown
    trigger="contextmenu"
    placement="bottom-start"
    :teleported="true"
    popper-class="explorer-node-context-popper"
    @command="onCommand"
  >
    <span
      v-contextmenu-block-native
      class="explorer-node-context-trigger"
    >
      <slot />
    </span>
    <template #dropdown>
      <el-dropdown-menu class="explorer-node-context-menu">
        <el-dropdown-item
          v-if="variant !== 'folder'"
          command="new-node"
          :disabled="disableNew"
        >
          <el-icon class="explorer-node-context-menu__icon">
            <DocumentAdd />
          </el-icon>
          新建 Node
        </el-dropdown-item>
        <el-dropdown-item
          command="new-folder"
          :disabled="disableNew"
        >
          <el-icon class="explorer-node-context-menu__icon">
            <FolderAdd />
          </el-icon>
          {{ variant === 'folder' ? '新建子文件夹' : '新建文件夹' }}
        </el-dropdown-item>
        <el-dropdown-item
          divided
          command="rename"
          :disabled="disableRename"
        >
          <el-icon class="explorer-node-context-menu__icon">
            <EditPen />
          </el-icon>
          重命名
        </el-dropdown-item>
        <el-dropdown-item
          command="copy-path"
          :disabled="disableCopyPath"
        >
          <el-icon class="explorer-node-context-menu__icon">
            <Link />
          </el-icon>
          复制路径
        </el-dropdown-item>
        <el-dropdown-item
          command="delete"
          :disabled="disableDelete"
          class="is-danger"
        >
          <el-icon class="explorer-node-context-menu__icon">
            <Delete />
          </el-icon>
          {{ variant === 'folder' ? '删除文件夹' : '删除' }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style scoped>
.explorer-node-context-trigger {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  flex: 1;
  width: 100%;
}
</style>

<style>
.explorer-node-context-popper.el-popper {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0;
}

.explorer-node-context-popper .el-dropdown-menu {
  margin: 0;
}

.explorer-node-context-menu.el-dropdown-menu {
  background: rgba(20, 20, 20, 0.9) !important;
  border: 1px solid rgba(0, 229, 255, 0.45);
  border-radius: 8px;
  box-shadow:
    0 0 0 1px rgba(0, 229, 255, 0.15),
    0 0 20px rgba(0, 229, 255, 0.35),
    0 8px 24px rgba(0, 0, 0, 0.55);
  padding: 4px 0;
  min-width: 168px;
}

.explorer-node-context-menu .el-dropdown-menu__item {
  color: rgba(230, 247, 255, 0.92);
  line-height: 32px;
}

.explorer-node-context-menu .el-dropdown-menu__item:not(.is-disabled):hover,
.explorer-node-context-menu .el-dropdown-menu__item:not(.is-disabled):focus {
  background-color: rgba(0, 229, 255, 0.2) !important;
  color: #e8fbff;
}

.explorer-node-context-menu .el-dropdown-menu__item.is-danger:not(.is-disabled) {
  color: #ff6b6b;
}

.explorer-node-context-menu .el-dropdown-menu__item.is-danger:not(.is-disabled):hover,
.explorer-node-context-menu .el-dropdown-menu__item.is-danger:not(.is-disabled):focus {
  background-color: rgba(255, 80, 80, 0.18) !important;
  color: #ffb4b4;
}

.explorer-node-context-menu__icon {
  margin-right: 8px;
  vertical-align: middle;
}
</style>
