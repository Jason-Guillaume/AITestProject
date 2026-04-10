<template>
  <div class="page-wrap cyber-page admin-list-page sys-admin-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">消息设置</h2>
          <p class="sys-page-head__sub">配置通知渠道与汇总策略，保存后写入消息设置接口。</p>
        </div>
        <el-button type="primary" size="default" :loading="saving" @click="handleSave">保存设置</el-button>
      </div>
    </el-card>

    <div class="sys-msg-cards">
      <el-card class="sys-msg-card" shadow="never">
        <template #header>
          <span class="sys-msg-card__title">系统告警与通道</span>
        </template>
        <p class="sys-msg-card__intro">控制系统级通知是否通过站内信、邮件或短信触达账号。</p>
        <el-form :model="form" label-width="0" class="sys-msg-form" ref="formRef">
          <div class="toggle-row">
            <div class="toggle-row__main">
              <el-form-item label="">
                <div class="toggle-head">
                  <span class="toggle-head__label">站内消息</span>
                  <el-switch v-model="form.in_app_enabled" />
                </div>
              </el-form-item>
              <p class="toggle-hint">在平台内展示系统通知、审批待办与重要提醒。</p>
            </div>
          </div>
          <div class="toggle-row">
            <div class="toggle-row__main">
              <el-form-item label="">
                <div class="toggle-head">
                  <span class="toggle-head__label">邮件通知</span>
                  <el-switch v-model="form.email_enabled" />
                </div>
              </el-form-item>
              <p class="toggle-hint">向用户绑定邮箱发送关键事件摘要（需邮件服务配置）。</p>
            </div>
          </div>
          <div class="toggle-row">
            <div class="toggle-row__main">
              <el-form-item label="">
                <div class="toggle-head">
                  <span class="toggle-head__label">短信通知</span>
                  <el-switch v-model="form.sms_enabled" />
                </div>
              </el-form-item>
              <p class="toggle-hint">高优先级告警短信推送，适用于值班与紧急缺陷场景。</p>
            </div>
          </div>
        </el-form>
      </el-card>

      <el-card class="sys-msg-card" shadow="never">
        <template #header>
          <span class="sys-msg-card__title">任务与日报汇总</span>
        </template>
        <p class="sys-msg-card__intro">定时汇总测试进度、待办任务与日报，减少打扰、提高可读性。</p>
        <el-form :model="form" label-width="0" class="sys-msg-form">
          <div class="toggle-row">
            <div class="toggle-row__main">
              <el-form-item label="">
                <div class="toggle-head">
                  <span class="toggle-head__label">日报汇总</span>
                  <el-switch v-model="form.digest_enabled" />
                </div>
              </el-form-item>
              <p class="toggle-hint">在指定时间生成前一日活动摘要（用例执行、缺陷变化等）。</p>
            </div>
          </div>
          <div class="toggle-row toggle-row--time">
            <div class="toggle-row__main">
              <el-form-item label="">
                <div class="toggle-head">
                  <span class="toggle-head__label">汇总时间（HH:mm）</span>
                </div>
              </el-form-item>
              <el-input
                v-model="form.digest_time"
                :disabled="!form.digest_enabled"
                placeholder="例如 08:30"
                class="digest-input"
              />
              <p class="toggle-hint">仅在开启日报汇总时生效；建议使用非业务高峰时段。</p>
            </div>
          </div>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getMessageSettingsApi,
  createMessageSettingApi,
  updateMessageSettingApi,
} from "@/api/system";

const formRef = ref(null);
const saving = ref(false);
const editingId = ref(null);

const form = reactive({
  in_app_enabled: true,
  email_enabled: false,
  sms_enabled: false,
  digest_enabled: false,
  digest_time: "08:30",
});

async function load() {
  try {
    const { data } = await getMessageSettingsApi({ latest: "1" });
    const rows = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : [];
    if (rows.length > 0) {
      editingId.value = rows[0].id;
      Object.assign(form, {
        in_app_enabled: rows[0].in_app_enabled,
        email_enabled: rows[0].email_enabled,
        sms_enabled: rows[0].sms_enabled,
        digest_enabled: rows[0].digest_enabled,
        digest_time: rows[0].digest_time || "08:30",
      });
    }
  } catch (e) {
    ElMessage.error("加载消息设置失败");
    // eslint-disable-next-line no-console
    console.error(e);
  }
}

async function handleSave() {
  saving.value = true;
  try {
    const payload = {
      in_app_enabled: !!form.in_app_enabled,
      email_enabled: !!form.email_enabled,
      sms_enabled: !!form.sms_enabled,
      digest_enabled: !!form.digest_enabled,
      digest_time: form.digest_enabled ? String(form.digest_time || "") : null,
    };
    if (editingId.value) {
      await updateMessageSettingApi(editingId.value, payload);
      ElMessage.success("保存成功");
    } else {
      await createMessageSettingApi(payload);
      ElMessage.success("保存成功");
    }
    await load();
  } catch (e) {
    ElMessage.error("保存失败，请检查后端接口与字段");
    // eslint-disable-next-line no-console
    console.error(e);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.sys-admin-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  box-sizing: border-box;
}

.sys-page-head,
.sys-msg-card {
  border-radius: 12px !important;
  border: 1px solid rgba(0, 255, 255, 0.12) !important;
  background: rgba(18, 26, 44, 0.92) !important;
  --el-card-bg-color: rgba(18, 26, 44, 0.92);
}

.sys-page-head :deep(.el-card__body) {
  padding: 16px 18px;
}

.sys-page-head__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.sys-page-head__title {
  margin: 0 0 6px;
  font-size: 17px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.94);
}

.sys-page-head__sub {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(226, 232, 240, 0.55);
  max-width: 520px;
}

.sys-msg-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sys-msg-card :deep(.el-card__header) {
  padding: 14px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(8, 12, 22, 0.35);
}

.sys-msg-card :deep(.el-card__body) {
  padding: 18px 20px 20px;
}

.sys-msg-card__title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.sys-msg-card__intro {
  margin: 0 0 18px;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(226, 232, 240, 0.5);
}

.toggle-row {
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.toggle-row:last-child {
  border-bottom: none;
}

.toggle-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  max-width: 420px;
}

.toggle-head__label {
  font-size: 14px;
  font-weight: 500;
  color: rgba(226, 232, 240, 0.88);
}

.toggle-hint {
  margin: 6px 0 0;
  max-width: 520px;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(148, 163, 184, 0.85);
}

.sys-msg-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.digest-input {
  max-width: 280px;
  margin-top: 8px;
}

.digest-input :deep(.el-input__wrapper) {
  background: rgba(10, 16, 28, 0.45);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.1);
}
</style>
