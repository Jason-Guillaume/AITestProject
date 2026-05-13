<script setup lang="ts">
import { Cellphone } from '@element-plus/icons-vue'
</script>

<template>
  <div class="tree-pane tree-pane--cross">
    <div class="tree-panel-head">
      小程序 · Node Explorer
    </div>
    <p class="tree-pane--cross__intro">
      微信小程序脚本执行入口（占位）：后续将接入脚本目录、开发者工具 / 真机池与遥测。
    </p>
    <div
      class="tree-pane--cross__chips"
      role="list"
    >
      <span
        class="tree-pane--cross__chip"
        role="listitem"
      >
        <el-icon class="tree-pane--cross__chip-icon"><Cellphone /></el-icon>
        微信小程序
      </span>
    </div>
    <el-empty
      class="tree-pane--cross__empty"
      description="脚本目录与执行管线建设中"
      :image-size="72"
    />
  </div>
</template>
