<template>
  <div class="inspector-mobile-panel">
    <section class="inspector-block">
      <h4 class="inspector-block__h">Device List（模拟）</h4>
      <ul class="device-list">
        <li v-for="d in devices" :key="d.id" class="device-list__item">
          <span class="device-list__name">{{ d.name }}</span>
          <el-tag :type="d.online ? 'success' : 'info'" size="small">
            {{ d.online ? 'Online' : 'Offline' }}
          </el-tag>
        </li>
      </ul>
    </section>
    <section class="inspector-block">
      <h4 class="inspector-block__h">Appium Server</h4>
      <p class="appium-status" :class="{ 'is-up': appiumUp }">
        {{ appiumUp ? '● LISTENING :4723（占位）' : '○ STOPPED' }}
      </p>
      <p class="inspector-block__desc">真实状态将在设备 Telemetry 接通后由后端推送。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
const devices = [
  { id: '1', name: 'Pixel 7 API 34 (emulator-5554)', online: false },
  { id: '2', name: 'iPhone 15 · WebDriverAgent（占位）', online: false },
]

const appiumUp = false
</script>

<style scoped>
.inspector-block__h {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(203, 213, 225, 0.92);
}

.inspector-block {
  margin-bottom: 14px;
}

.device-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.device-list__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 6px;
  border-radius: 8px;
  border: 1px solid rgba(244, 114, 182, 0.2);
  background: rgba(244, 114, 182, 0.05);
}

.device-list__name {
  font-size: 11px;
  color: rgba(226, 232, 240, 0.9);
}

.appium-status {
  margin: 0 0 6px;
  font-family: ui-monospace, 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  color: rgba(248, 113, 113, 0.9);
}

.appium-status.is-up {
  color: rgba(52, 211, 153, 0.9);
}

.inspector-block__desc {
  margin: 0;
  font-size: 11px;
  color: rgba(148, 163, 184, 0.85);
}
</style>
