<script setup lang="ts">
import { Postcard } from '@element-plus/icons-vue'
</script>

<template>
  <div class="tree-pane tree-pane--cross">
    <div class="tree-panel-head">
      H5 · Node Explorer
    </div>
    <p class="tree-pane--cross__intro">
      H5 页面脚本执行入口（占位）：后续将接入内嵌 WebView / 独立 H5 工程树与浏览器驱动。
    </p>
    <div
      class="tree-pane--cross__chips"
      role="list"
    >
      <span
        class="tree-pane--cross__chip"
        role="listitem"
      >
        <el-icon class="tree-pane--cross__chip-icon"><Postcard /></el-icon>
        H5 页面
      </span>
    </div>
    <el-empty
      class="tree-pane--cross__empty"
      description="脚本目录与执行管线建设中"
      :image-size="72"
    />
  </div>
</template>
