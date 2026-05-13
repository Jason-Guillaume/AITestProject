<template>
  <div
    class="app-root"
    :class="{ dark: isDarkChrome, 'app-root--mini-status': showStatusBar }"
  >
    <router-view class="app-root__view" />
    <CommandPalette />
    <AIDrawer />
    <MiniStatusBar />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import CommandPalette from "@/components/CommandPalette/index.vue";
import AIDrawer from "@/components/AIDrawer.vue";
import MiniStatusBar from "@/components/MiniStatusBar.vue";

const route = useRoute();
const isDarkChrome = computed(() => route.meta?.public !== true);
const isAuthed = ref(!!localStorage.getItem("token"));
const showStatusBar = computed(() => isDarkChrome.value && isAuthed.value);

function syncAuth() {
  isAuthed.value = !!localStorage.getItem("token");
}

watch(() => route.fullPath, syncAuth);
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
