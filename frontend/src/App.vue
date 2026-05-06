<template>
  <div
    class="app-root"
    :class="{ dark: isDarkChrome, 'app-root--mini-status': isDarkChrome }"
  >
    <router-view class="app-root__view" />
    <CommandPalette />
    <AIDrawer />
    <MiniStatusBar />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import CommandPalette from "@/components/CommandPalette/index.vue";
import AIDrawer from "@/components/AIDrawer.vue";
import MiniStatusBar from "@/components/MiniStatusBar.vue";

const route = useRoute();
/** 登录/注册等 public 页保持独立视觉；内嵌工作台等启用 EP 暗色变量与科技风壳层 */
const isDarkChrome = computed(() => route.meta?.public !== true);
</script>

<style scoped>
.app-root {
  min-height: 100%;
}

/** 为底部固定状态栏预留空间，避免内容被遮挡 */
.app-root--mini-status .app-root__view {
  padding-bottom: 24px;
  box-sizing: border-box;
}
</style>
