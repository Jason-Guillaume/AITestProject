<template>
  <div class="cyber-page admin-list-page scheduled-task-detail-page">
    <el-card class="admin-list-card" shadow="never" v-loading="loading">
      <div class="scheduled-task-title">
        {{ isEdit ? "定时任务详情" : "新建定时任务" }}
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：每日回归任务" />
        </el-form-item>
        <el-form-item label="Cron 表达式" prop="cron_expression">
          <el-input v-model="form.cron_expression" placeholder="例如：0 2 * * *" />
        </el-form-item>
        <el-form-item label="任务状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="paused">暂停</el-radio-button>
            <el-radio-button label="disabled">禁用</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="执行环境" prop="environment">
          <el-select v-model="form.environment" filterable placeholder="请选择环境" class="w-full">
            <el-option v-for="item in environmentOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联用例" prop="test_case_ids">
          <el-select
            v-model="form.test_case_ids"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            class="w-full"
            placeholder="选择要执行的用例"
          >
            <el-option
              v-for="item in caseOptions"
              :key="item.id"
              :label="`${item.case_name} (#${item.id})`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="scheduled-task-actions">
        <el-button @click="onBack">返回</el-button>
        <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
        <el-button v-if="isEdit" type="warning" plain @click="onPause">暂停</el-button>
        <el-button v-if="isEdit" type="success" plain @click="onResume">恢复</el-button>
        <el-button v-if="isEdit" type="info" plain @click="onTrigger">立即执行</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import request from "@/utils/request";
import {
  createScheduledTask,
  getScheduledTaskDetail,
  pauseScheduledTask,
  resumeScheduledTask,
  triggerScheduledTask,
  updateScheduledTask,
} from "@/api/scheduledTask";
import { getEnvironments } from "@/api/environment";

const route = useRoute();
const router = useRouter();

const loading = ref(false);
const saving = ref(false);
const formRef = ref();
const environmentOptions = ref([]);
const caseOptions = ref([]);

const form = ref({
  name: "",
  cron_expression: "0 2 * * *",
  status: "active",
  environment: null,
  test_case_ids: [],
});

const rules = {
  name: [{ required: true, message: "请输入任务名称", trigger: "blur" }],
  cron_expression: [{ required: true, message: "请输入 Cron 表达式", trigger: "blur" }],
  environment: [{ required: true, message: "请选择执行环境", trigger: "change" }],
};

const taskId = computed(() => Number(route.params.id || 0));
const isEdit = computed(() => Number.isInteger(taskId.value) && taskId.value > 0);

async function fetchBasicOptions() {
  const [envRes, caseRes] = await Promise.all([
    getEnvironments({ page_size: 200 }),
    request.get("/testcase/cases/", { params: { page_size: 200, testType: "api" } }),
  ]);
  environmentOptions.value = Array.isArray(envRes?.data?.results)
    ? envRes.data.results
    : Array.isArray(envRes?.data)
      ? envRes.data
      : [];
  caseOptions.value = Array.isArray(caseRes?.data?.results)
    ? caseRes.data.results
    : Array.isArray(caseRes?.data)
      ? caseRes.data
      : [];
}

async function fetchTaskDetail() {
  if (!isEdit.value) return;
  const { data } = await getScheduledTaskDetail(taskId.value);
  form.value = {
    name: data.name || "",
    cron_expression: data.cron_expression || "",
    status: data.status || "active",
    environment: data.environment || null,
    test_case_ids: Array.isArray(data.test_case_ids)
      ? data.test_case_ids
      : Array.isArray(data.test_cases)
        ? data.test_cases
        : [],
  };
}

async function onSubmit() {
  await formRef.value.validate();
  saving.value = true;
  try {
    if (isEdit.value) {
      await updateScheduledTask(taskId.value, form.value);
      ElMessage.success("定时任务已更新");
    } else {
      await createScheduledTask(form.value);
      ElMessage.success("定时任务已创建");
    }
    router.push("/performance/tasks");
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function onPause() {
  try {
    await pauseScheduledTask(taskId.value);
    ElMessage.success("任务已暂停");
    await fetchTaskDetail();
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "暂停失败");
  }
}

async function onResume() {
  try {
    await resumeScheduledTask(taskId.value);
    ElMessage.success("任务已恢复");
    await fetchTaskDetail();
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "恢复失败");
  }
}

async function onTrigger() {
  try {
    await triggerScheduledTask(taskId.value);
    ElMessage.success("任务已触发");
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "触发失败");
  }
}

function onBack() {
  router.back();
}

onMounted(async () => {
  loading.value = true;
  try {
    await fetchBasicOptions();
    await fetchTaskDetail();
  } catch (error) {
    ElMessage.error(error?.response?.data?.msg || "页面初始化失败");
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.scheduled-task-detail-page {
  min-height: 100%;
}

.scheduled-task-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.95);
  margin-bottom: 16px;
}

.scheduled-task-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
