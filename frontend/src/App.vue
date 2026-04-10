<template>
  <div class="app-root" :class="{ dark: isDarkChrome }">
    <router-view />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
/** 登录/注册等 public 页保持独立视觉；内嵌工作台等启用 EP 暗色变量与科技风壳层 */
const isDarkChrome = computed(() => route.meta?.public !== true);
</script>

<style scoped>
.app-root {
  min-height: 100%;
}
</style>
