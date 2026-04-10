<template>
  <div class="table-action-group">
    <el-tooltip
      v-for="item in visibleActions"
      :key="item.key"
      :content="item.tooltip"
      placement="top"
    >
      <el-button
        circle
        class="table-action-group__btn"
        :class="buttonClass(item)"
        :loading="Boolean(item.loading)"
        :disabled="Boolean(item.disabled)"
        @click="emit('action', item.key, row)"
      >
        <el-icon v-if="!item.loading && item.icon"><component :is="item.icon" /></el-icon>
      </el-button>
    </el-tooltip>

    <el-dropdown
      v-if="overflowActions.length"
      trigger="click"
      @command="handleOverflowCommand"
    >
      <el-button circle class="table-action-group__btn table-action-group__btn--more">
        <el-icon><MoreFilled /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="item in overflowActions"
            :key="item.key"
            :command="item.key"
            :disabled="Boolean(item.disabled) || Boolean(item.loading)"
          >
            <span class="table-action-group__dropdown-item">
              <el-icon v-if="item.icon && !item.loading"><component :is="item.icon" /></el-icon>
              <span>{{ item.tooltip }}</span>
            </span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { MoreFilled } from "@element-plus/icons-vue";

const props = defineProps({
  row: { type: Object, default: () => ({}) },
  actions: { type: Array, default: () => [] },
  maxVisible: { type: Number, default: 3 },
});

const emit = defineEmits(["action"]);

const visibleActions = computed(() => props.actions.slice(0, props.maxVisible));
const overflowActions = computed(() => props.actions.slice(props.maxVisible));

function buttonClass(item) {
  return {
    "table-action-group__btn--primary": item.type === "primary",
    "table-action-group__btn--success": item.type === "success",
    "table-action-group__btn--warning": item.type === "warning",
    "table-action-group__btn--danger": item.type === "danger",
  };
}

function handleOverflowCommand(actionKey) {
  emit("action", actionKey, props.row);
}
</script>

<style scoped>
.table-action-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

:deep(.table-action-group__btn) {
  border-color: rgba(100, 116, 139, 0.45);
  background: rgba(15, 23, 42, 0.65);
  color: #cbd5e1;
  transition:
    border-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

:deep(.table-action-group__btn:hover) {
  transform: translateY(-1px);
}

:deep(.table-action-group__btn--primary:hover) {
  border-color: rgba(56, 189, 248, 0.65);
  color: #7dd3fc;
  box-shadow: 0 0 14px rgba(56, 189, 248, 0.25);
}

:deep(.table-action-group__btn--success:hover) {
  border-color: rgba(34, 211, 238, 0.72);
  color: #67e8f9;
  box-shadow: 0 0 16px rgba(34, 211, 238, 0.3);
}

:deep(.table-action-group__btn--warning:hover) {
  border-color: rgba(250, 204, 21, 0.6);
  color: #fde047;
  box-shadow: 0 0 14px rgba(250, 204, 21, 0.22);
}

:deep(.table-action-group__btn--danger:hover) {
  border-color: rgba(248, 113, 113, 0.6);
  color: #fca5a5;
  box-shadow: 0 0 14px rgba(248, 113, 113, 0.2);
}

:deep(.table-action-group__btn.is-loading) {
  border-color: rgba(34, 211, 238, 0.72);
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.35);
}

.table-action-group__dropdown-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>
