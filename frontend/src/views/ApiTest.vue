<script setup lang="ts">
/**
 * 接口测试列表页：与 /test-case/api 对应，内嵌 TestCase 并固定 test_type=api。
 * 执行控制台见 ApiExecuteConsoleDialog（在 TestCase 表格「调试」中打开）。
 */
import { provide } from 'vue'
import TestCase from './TestCase.vue'

provide('testCaseForcedType', 'api')
</script>

<template>
  <TestCase />
</template>
