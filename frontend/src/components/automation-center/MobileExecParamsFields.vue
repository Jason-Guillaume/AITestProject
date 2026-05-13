<script setup lang="ts">
const mobileDevicePlaceholder = defineModel<string>('mobileDevicePlaceholder', { required: true })
const mobilePackageName = defineModel<string>('mobilePackageName', { required: true })
</script>

<template>
  <div class="params-drawer__body">
    <p class="params-drawer__hint">
      移动端执行上下文（占位）；Telemetry 接通后由设备服务回填。
    </p>
    <div class="params-drawer__row params-drawer__row--top">
      <span class="params-drawer__label">Device</span>
      <el-select
        v-model="mobileDevicePlaceholder"
        size="small"
        class="params-drawer__select"
        disabled
        placeholder="选择设备（占位）"
      >
        <el-option
          label="— 暂无设备 —"
          value=""
        />
      </el-select>
    </div>
    <div class="params-drawer__row params-drawer__row--top">
      <span class="params-drawer__label">Package Name</span>
      <el-input
        v-model="mobilePackageName"
        size="small"
        clearable
        placeholder="com.example.app（占位）"
        class="params-drawer__input"
      />
    </div>
  </div>
</template>
