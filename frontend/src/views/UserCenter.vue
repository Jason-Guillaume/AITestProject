<template>
  <div class="user-center cyber-page">
    <header class="uc-header">
      <h1 class="uc-title">个人中心</h1>
      <p class="uc-sub">基础资料可即时保存；用户名与登录密码变更需管理员邮件审批。</p>
    </header>

    <!-- 基础信息 -->
    <section class="glass-card uc-section">
      <div class="uc-section__head">
        <span class="uc-section__label">基础信息</span>
        <span class="uc-section__hint">即时生效</span>
      </div>

      <div class="uc-basic">
        <div class="uc-avatar-wrap">
          <input
            ref="avatarInputRef"
            type="file"
            class="uc-avatar-input"
            accept="image/jpeg,image/png,image/webp,image/gif"
            @change="onAvatarFile"
          />
          <button type="button" class="uc-avatar" @click="avatarInputRef?.click()">
            <img v-if="avatarPreview || profile.avatar_url" :src="avatarPreview || profile.avatar_url" alt="" />
            <div v-else class="uc-avatar__placeholder">
              <el-icon :size="36"><User /></el-icon>
            </div>
            <span class="uc-avatar__edit">更换头像</span>
          </button>
          <p class="uc-avatar-tip">点击选择图片，与下方资料一并保存</p>
        </div>

        <el-form ref="basicFormRef" :model="basicForm" label-position="top" class="uc-form">
          <el-form-item label="显示名称">
            <el-input v-model="basicForm.real_name" placeholder="真实姓名 / 显示名" class="uc-input" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="basicForm.phone_number" placeholder="手机号码" class="uc-input" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="basicForm.email" placeholder="电子邮箱" class="uc-input" />
          </el-form-item>
          <el-form-item label="登录用户名（只读）">
            <el-input v-model="profile.username" disabled class="uc-input uc-input--disabled" />
          </el-form-item>
          <div class="uc-actions">
            <el-button type="primary" class="uc-btn-primary" :loading="savingBasic" @click="saveBasic">
              保存资料
            </el-button>
            <el-button class="uc-btn-ghost" :loading="loadingProfile" @click="loadAll">刷新</el-button>
          </div>
        </el-form>
      </div>
    </section>

    <!-- 账号安全 -->
    <section class="glass-card uc-section">
      <div class="uc-section__head">
        <span class="uc-section__label">账号安全</span>
        <span class="uc-section__hint">管理员审批后生效</span>
      </div>

      <div class="uc-security-grid">
        <div class="security-card">
          <div class="security-card__icon"><el-icon><Key /></el-icon></div>
          <div class="security-card__body">
            <h3 class="security-card__title">登录用户名</h3>
            <p class="security-card__desc">修改后需管理员审核，审核通过后将更新为新的登录名。</p>
            <div v-if="pendingStatus.pending_username" class="pending-badge">Pending Admin Approval</div>
            <el-button
              class="uc-btn-outline"
              :disabled="pendingStatus.pending_username"
              @click="openUsernameModal"
            >
              修改用户名
            </el-button>
          </div>
        </div>
        <div class="security-card">
          <div class="security-card__icon"><el-icon><Lock /></el-icon></div>
          <div class="security-card__body">
            <h3 class="security-card__title">登录密码</h3>
            <p class="security-card__desc">新密码以安全形式提交，审批通过后生效。</p>
            <div v-if="pendingStatus.pending_password" class="pending-badge">Pending Admin Approval</div>
            <el-button
              class="uc-btn-outline"
              :disabled="pendingStatus.pending_password"
              @click="openPasswordModal"
            >
              修改密码
            </el-button>
          </div>
        </div>
      </div>
    </section>

    <!-- 修改用户名 -->
    <el-dialog
      v-model="usernameModalVisible"
      title="修改用户名"
      width="440px"
      destroy-on-close
      class="cyber-dialog-dark"
      @closed="usernameForm.new_username = ''"
    >
      <p class="uc-security-notice">
        Security Notice: Modifying your username or password requires Administrator approval. An email
        notification will be sent to the admin.
      </p>
      <p class="uc-security-notice-zh">
        安全提示：修改用户名或密码需经管理员审批，系统将向管理员发送邮件通知。
      </p>
      <el-form label-position="top" class="uc-modal-form">
        <el-form-item label="新用户名">
          <el-input v-model="usernameForm.new_username" placeholder="请输入新用户名" class="uc-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="uc-btn-ghost" @click="usernameModalVisible = false">取消</el-button>
        <el-button type="primary" class="uc-btn-primary" :loading="submittingSensitive" @click="submitUsername">
          提交申请
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改密码 -->
    <el-dialog
      v-model="passwordModalVisible"
      title="修改登录密码"
      width="440px"
      destroy-on-close
      class="cyber-dialog-dark"
      @closed="resetPasswordForm"
    >
      <p class="uc-security-notice">
        Security Notice: Modifying your username or password requires Administrator approval. An email
        notification will be sent to the admin.
      </p>
      <p class="uc-security-notice-zh">
        安全提示：修改用户名或密码需经管理员审批，系统将向管理员发送邮件通知。
      </p>
      <el-form label-position="top" class="uc-modal-form">
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="至少 6 位" class="uc-input" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="再次输入" class="uc-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button class="uc-btn-ghost" @click="passwordModalVisible = false">取消</el-button>
        <el-button type="primary" class="uc-btn-primary" :loading="submittingSensitive" @click="submitPasswordRequest">
          提交申请
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Key, Lock } from '@element-plus/icons-vue'
import {
  getUserProfileApi,
  patchUserProfileApi,
  getSensitiveChangeStatusApi,
  submitSensitiveChangeApi,
} from '@/api/user'

const loadingProfile = ref(false)
const savingBasic = ref(false)
const submittingSensitive = ref(false)

const avatarInputRef = ref(null)
const basicFormRef = ref(null)

const profile = reactive({
  id: null,
  username: '',
  real_name: '',
  phone_number: '',
  email: '',
  avatar_url: null,
})

const basicForm = reactive({
  real_name: '',
  phone_number: '',
  email: '',
})

const avatarPreview = ref(null)
const pendingAvatarFile = ref(null)

const pendingStatus = reactive({
  pending_username: false,
  pending_password: false,
})

const usernameModalVisible = ref(false)
const passwordModalVisible = ref(false)

const usernameForm = reactive({
  new_username: '',
})

const passwordForm = reactive({
  new_password: '',
  confirm_password: '',
})

function applyProfileData(data) {
  if (!data) return
  profile.id = data.id
  profile.username = data.username ?? ''
  profile.real_name = data.real_name ?? ''
  profile.phone_number = data.phone_number ?? ''
  profile.email = data.email ?? ''
  profile.avatar_url = data.avatar_url ?? null
  basicForm.real_name = profile.real_name
  basicForm.phone_number = profile.phone_number
  basicForm.email = profile.email
}

async function loadProfile() {
  loadingProfile.value = true
  try {
    const { data: res } = await getUserProfileApi()
    const payload = res?.data ?? res
    applyProfileData(payload)
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '加载资料失败')
  } finally {
    loadingProfile.value = false
  }
}

async function loadPendingStatus() {
  try {
    const { data: res } = await getSensitiveChangeStatusApi()
    const d = res?.data ?? res
    pendingStatus.pending_username = !!d?.pending_username
    pendingStatus.pending_password = !!d?.pending_password
  } catch {
    pendingStatus.pending_username = false
    pendingStatus.pending_password = false
  }
}

async function loadAll() {
  await loadProfile()
  await loadPendingStatus()
}

function onAvatarFile(ev) {
  const file = ev.target?.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  pendingAvatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

async function saveBasic() {
  savingBasic.value = true
  try {
    let body
    if (pendingAvatarFile.value) {
      const fd = new FormData()
      fd.append('real_name', basicForm.real_name)
      fd.append('phone_number', basicForm.phone_number)
      fd.append('email', basicForm.email)
      fd.append('avatar', pendingAvatarFile.value)
      body = fd
    } else {
      body = {
        real_name: basicForm.real_name,
        phone_number: basicForm.phone_number,
        email: basicForm.email,
      }
    }
    const { data: res } = await patchUserProfileApi(body)
    const payload = res?.data ?? res
    applyProfileData(payload)
    pendingAvatarFile.value = null
    if (avatarPreview.value) {
      URL.revokeObjectURL(avatarPreview.value)
      avatarPreview.value = null
    }
    if (avatarInputRef.value) avatarInputRef.value.value = ''
    ElMessage.success(res?.msg || '保存成功')
    window.dispatchEvent(
      new CustomEvent('app:user-profile-updated', {
        detail: { avatar_url: payload?.avatar_url ?? null },
      })
    )
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || e?.response?.data?.detail || '保存失败')
  } finally {
    savingBasic.value = false
  }
}

function openUsernameModal() {
  usernameForm.new_username = ''
  usernameModalVisible.value = true
}

function openPasswordModal() {
  resetPasswordForm()
  passwordModalVisible.value = true
}

function resetPasswordForm() {
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
}

async function submitUsername() {
  const name = (usernameForm.new_username || '').trim()
  if (!name) {
    ElMessage.warning('请输入新用户名')
    return
  }
  if (name === profile.username) {
    ElMessage.warning('与当前用户名相同')
    return
  }
  submittingSensitive.value = true
  try {
    const { data: res } = await submitSensitiveChangeApi({
      request_type: 'username',
      new_username: name,
    })
    ElMessage.success(res?.msg || '已提交申请')
    usernameModalVisible.value = false
    await loadPendingStatus()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || '提交失败')
  } finally {
    submittingSensitive.value = false
  }
}

async function submitPasswordRequest() {
  const p1 = passwordForm.new_password || ''
  const p2 = passwordForm.confirm_password || ''
  if (p1.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (p1 !== p2) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  submittingSensitive.value = true
  try {
    const { data: res } = await submitSensitiveChangeApi({
      request_type: 'password',
      new_password: p1,
    })
    ElMessage.success(res?.msg || '已提交申请')
    passwordModalVisible.value = false
    resetPasswordForm()
    await loadPendingStatus()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || '提交失败')
  } finally {
    submittingSensitive.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.user-center {
  max-width: 960px;
  margin: 0 auto;
  padding: 8px 0 32px;
  --uc-cyan: #00d8ff;
  --uc-cyan-dim: rgba(0, 216, 255, 0.35);
  --uc-text: #e2e8f0;
  --uc-muted: rgba(226, 232, 240, 0.55);
  --uc-glass: rgba(20, 28, 47, 0.6);
  --uc-border: rgba(0, 255, 255, 0.15);
}

.uc-header {
  margin-bottom: 20px;
}

.uc-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 700;
  color: var(--uc-text);
  letter-spacing: 0.02em;
  text-shadow: 0 0 18px rgba(0, 216, 255, 0.25);
}

.uc-sub {
  margin: 0;
  font-size: 13px;
  color: var(--uc-muted);
}

.glass-card {
  background: var(--uc-glass);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--uc-border);
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 20px;
  transition:
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

.glass-card:hover {
  border-color: rgba(0, 255, 255, 0.22);
  box-shadow: 0 0 24px rgba(0, 216, 255, 0.08);
}

.uc-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.uc-section__label {
  font-size: 15px;
  font-weight: 600;
  color: var(--uc-text);
}

.uc-section__hint {
  font-size: 12px;
  color: var(--uc-cyan);
  text-shadow: 0 0 12px var(--uc-cyan-dim);
}

.uc-basic {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 28px;
  align-items: start;
}

@media (max-width: 720px) {
  .uc-basic {
    grid-template-columns: 1fr;
  }
}

.uc-avatar-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.uc-avatar-wrap {
  text-align: center;
}

.uc-avatar {
  position: relative;
  width: 132px;
  height: 132px;
  padding: 0;
  border: 1px solid rgba(0, 255, 255, 0.2);
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  background: rgba(10, 16, 29, 0.5);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.uc-avatar:hover {
  border-color: rgba(0, 216, 255, 0.55);
  box-shadow: 0 0 20px rgba(0, 216, 255, 0.2);
}

.uc-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.uc-avatar__placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(0, 216, 255, 0.35);
}

.uc-avatar__edit {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 6px;
  font-size: 11px;
  color: #0a101d;
  background: linear-gradient(180deg, transparent, rgba(0, 216, 255, 0.85));
}

.uc-avatar-tip {
  margin: 10px 0 0;
  font-size: 11px;
  color: var(--uc-muted);
}

.uc-form :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.78);
}

.uc-input :deep(.el-input__wrapper) {
  background: rgba(10, 16, 28, 0.5);
  box-shadow: none;
  border: 1px solid rgba(0, 255, 255, 0.12);
  border-radius: 8px;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.uc-input :deep(.el-input__wrapper.is-focus) {
  border-color: rgba(0, 216, 255, 0.45);
  box-shadow: 0 0 0 1px rgba(0, 216, 255, 0.18);
}

.uc-input :deep(.el-input__inner) {
  color: var(--uc-text);
}

.uc-input--disabled :deep(.el-input__wrapper) {
  background: rgba(8, 12, 22, 0.35);
  opacity: 0.85;
}

.uc-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.uc-btn-primary {
  border: none;
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.35), rgba(30, 90, 140, 0.55));
  color: #e2e8f0;
}

.uc-btn-primary:hover {
  box-shadow: 0 0 16px rgba(0, 216, 255, 0.25);
}

.uc-btn-ghost {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(0, 255, 255, 0.2);
  color: rgba(226, 232, 240, 0.9);
}

.uc-btn-ghost:hover {
  border-color: rgba(0, 216, 255, 0.4);
  color: var(--uc-cyan);
}

.uc-security-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.security-card {
  display: flex;
  gap: 14px;
  padding: 16px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(12, 18, 32, 0.45);
}

.security-card__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--uc-cyan);
  background: rgba(0, 216, 255, 0.1);
  border: 1px solid rgba(0, 216, 255, 0.2);
  flex-shrink: 0;
}

.security-card__title {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--uc-text);
}

.security-card__desc {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--uc-muted);
  line-height: 1.5;
}

.uc-btn-outline {
  width: 100%;
  max-width: 200px;
  background: transparent;
  border: 1px solid rgba(0, 255, 255, 0.25);
  color: rgba(226, 232, 240, 0.92);
}

.uc-btn-outline:hover:not(:disabled) {
  border-color: rgba(0, 216, 255, 0.5);
  color: var(--uc-cyan);
  box-shadow: 0 0 14px rgba(0, 216, 255, 0.12);
}

.uc-btn-outline:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pending-badge {
  display: inline-block;
  margin-bottom: 10px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-radius: 6px;
  color: #ffb020;
  background: rgba(255, 176, 32, 0.12);
  border: 1px solid rgba(255, 176, 32, 0.45);
  box-shadow:
    0 0 12px rgba(255, 176, 32, 0.25),
    0 0 24px rgba(255, 115, 0, 0.12);
}

.uc-security-notice {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(255, 200, 120, 0.95);
  border-left: 3px solid rgba(255, 176, 32, 0.7);
  padding-left: 10px;
}

.uc-security-notice-zh {
  margin: 0 0 16px;
  font-size: 12px;
  line-height: 1.55;
  color: rgba(226, 232, 240, 0.65);
}

.uc-modal-form :deep(.el-form-item__label) {
  color: rgba(226, 232, 240, 0.78);
}
</style>
