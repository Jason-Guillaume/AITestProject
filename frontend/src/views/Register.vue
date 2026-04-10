<template>
  <div class="login-page">
    <div class="login-page__particles" aria-hidden="true">
      <vue-particles id="register-tsparticles" :options="particleOptions" />
    </div>

    <div class="login-page__glow login-page__glow--1" aria-hidden="true" />
    <div class="login-page__glow login-page__glow--2" aria-hidden="true" />

    <div class="login-page__content">
      <aside class="login-hero" aria-hidden="true">
        <div class="login-hero__brain-wrap">
          <svg class="login-hero__brain" viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="regBrainLine" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.9" />
                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.5" />
              </linearGradient>
              <filter id="regBrainGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <g fill="none" stroke="url(#regBrainLine)" stroke-width="0.8" filter="url(#regBrainGlow)" opacity="0.85">
              <path
                d="M160 40 C210 20 260 60 270 110 C285 170 240 230 160 248 C80 230 35 170 50 110 C60 60 110 20 160 40Z"
              />
              <path d="M160 48 L160 232 M90 100 L230 100 M75 160 L245 160 M110 70 L210 210 M210 70 L110 210" />
              <circle cx="160" cy="130" r="28" stroke-width="1.2" />
            </g>
            <text
              x="160"
              y="138"
              text-anchor="middle"
              fill="#e0f2fe"
              font-size="18"
              font-weight="700"
              font-family="system-ui, sans-serif"
              letter-spacing="0.12em"
            >
              AI
            </text>
          </svg>
        </div>

        <ul class="login-hero__labels">
          <li class="login-hero__label login-hero__label--1">
            <FileSearch class="login-hero__label-icon" :size="14" stroke-width="2" />
            <span>DEMAND ANALYSIS</span>
          </li>
          <li class="login-hero__label login-hero__label--2">
            <span>AI GENERATION</span>
          </li>
          <li class="login-hero__label login-hero__label--3">
            <span>AUTOMATED EXECUTION</span>
          </li>
          <li class="login-hero__label login-hero__label--4">
            <span>INTELLIGENT ANALYSIS</span>
          </li>
          <li class="login-hero__label login-hero__label--5">
            <RefreshCw class="login-hero__label-icon" :size="14" stroke-width="2" />
            <span>CONTINUOUS FEEDBACK</span>
          </li>
        </ul>
      </aside>

      <div class="login-card-shell">
        <div class="glass-card" :class="{ 'glass-card--visible': mounted }">
          <header class="glass-card__header">
            <div class="glass-card__logo" aria-hidden="true">
              <svg viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="regAtRing" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#22d3ee" />
                    <stop offset="100%" stop-color="#3b82f6" />
                  </linearGradient>
                </defs>
                <circle cx="28" cy="28" r="26" fill="none" stroke="url(#regAtRing)" stroke-width="1.5" opacity="0.9" />
                <circle cx="28" cy="28" r="22" fill="none" stroke="url(#regAtRing)" stroke-width="0.6" opacity="0.35" />
                <text
                  x="28"
                  y="34"
                  text-anchor="middle"
                  fill="#f8fafc"
                  font-size="16"
                  font-weight="800"
                  font-family="system-ui, sans-serif"
                >
                  AT
                </text>
              </svg>
            </div>
            <h1 class="glass-card__brand">AITesta</h1>
            <p class="glass-card__tagline">全流程 AI 测试平台</p>
            <div class="glass-card__divider" />
            <h2 class="glass-card__title">注册</h2>
            <p class="glass-card__subtitle">创建你的账号</p>
          </header>

          <el-form
            ref="formRef"
            class="glass-form"
            :model="form"
            :rules="rules"
            label-position="top"
            @submit.prevent
          >
            <el-form-item prop="username" class="glass-form__item">
              <el-input
                v-model="form.username"
                size="large"
                clearable
                autocomplete="username"
                placeholder="用户名"
                class="glass-input"
              >
                <template #prefix>
                  <User class="glass-input__icon" :size="18" stroke-width="2" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password" class="glass-form__item">
              <el-input
                v-model="form.password"
                type="password"
                size="large"
                show-password
                clearable
                autocomplete="new-password"
                placeholder="密码"
                class="glass-input"
              >
                <template #prefix>
                  <Lock class="glass-input__icon" :size="18" stroke-width="2" />
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="captcha_code" class="glass-form__item glass-form__item--captcha">
              <div class="captcha-merge">
                <el-input
                  v-model="form.captcha_code"
                  size="large"
                  clearable
                  placeholder="验证码"
                  class="glass-input captcha-merge__input"
                  maxlength="6"
                  @keyup.enter="handleSubmit"
                >
                  <template #prefix>
                    <ShieldCheck class="glass-input__icon" :size="18" stroke-width="2" />
                  </template>
                </el-input>
                <div v-if="captchaImage" class="captcha-merge__panel">
                  <img :src="captchaImage" class="captcha-merge__img" alt="" />
                  <button
                    type="button"
                    class="captcha-merge__refresh"
                    :disabled="captchaLoading"
                    title="刷新验证码"
                    aria-label="刷新验证码"
                    @click="fetchCaptcha"
                  >
                    <RefreshCw class="captcha-merge__refresh-icon" :size="15" stroke-width="2" :class="{ 'is-spinning': captchaLoading }" />
                  </button>
                </div>
                <div v-else class="captcha-merge__panel captcha-merge__panel--placeholder">
                  <span class="captcha-merge__loading-hint">{{ captchaLoading ? "加载中…" : "获取中…" }}</span>
                  <button
                    type="button"
                    class="captcha-merge__refresh"
                    :disabled="captchaLoading"
                    title="刷新验证码"
                    aria-label="刷新验证码"
                    @click="fetchCaptcha"
                  >
                    <RefreshCw class="captcha-merge__refresh-icon" :size="15" stroke-width="2" :class="{ 'is-spinning': captchaLoading }" />
                  </button>
                </div>
              </div>
            </el-form-item>

            <el-form-item class="glass-form__submit">
              <el-button
                class="neon-btn"
                type="primary"
                size="large"
                :loading="loading"
                native-type="button"
                @click="handleSubmit"
              >
                注册
              </el-button>
            </el-form-item>
          </el-form>

          <footer class="glass-card__footer">
            <span class="glass-card__footer-muted">已有账号？</span>
            <button type="button" class="glass-link glass-link--strong" @click="goLogin">去登录</button>
          </footer>

          <div class="glass-card__tech-strip" aria-hidden="true">
            <span class="glass-card__tech-dot" />
            <span class="glass-card__tech-dot" />
            <span class="glass-card__tech-dot" />
            <span class="glass-card__tech-dot" />
            <span class="glass-card__tech-dot" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock, FileSearch, RefreshCw, ShieldCheck } from "lucide-vue-next";
import { captchaApi, registerApi } from "@/api/auth";

const router = useRouter();
const formRef = ref();
const loading = ref(false);
const mounted = ref(false);

const captchaLoading = ref(false);
const captchaImage = ref("");
const captchaUuid = ref("");

const form = ref({
  username: "",
  password: "",
  captcha_code: "",
  captcha_uuid: "",
});

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
  captcha_code: [{ required: true, message: "请输入验证码", trigger: "blur" }],
};

/** @type {import('@tsparticles/engine').ISourceOptions} */
const particleOptions = {
  fullScreen: { enable: false, zIndex: 0 },
  background: { color: { value: "transparent" } },
  fpsLimit: 90,
  detectRetina: true,
  interactivity: {
    events: {
      onHover: { enable: true, mode: "grab" },
      onClick: { enable: true, mode: "push" },
      resize: { enable: true, delay: 0.25 },
    },
    modes: {
      grab: {
        distance: 160,
        links: { opacity: 0.45, blink: false, color: "#22d3ee" },
      },
      push: { quantity: 2 },
    },
  },
  particles: {
    color: { value: ["#22d3ee", "#38bdf8", "#67e8f9", "#818cf8"] },
    links: {
      enable: true,
      distance: 130,
      color: "#22d3ee",
      opacity: 0.22,
      width: 0.8,
      triangles: { enable: false },
    },
    move: {
      enable: true,
      speed: { min: 0.35, max: 0.95 },
      direction: "none",
      random: true,
      straight: false,
      outModes: { default: "bounce" },
      attract: { enable: false },
    },
    number: { value: 72, density: { enable: true, width: 1080, height: 1080 } },
    opacity: { value: { min: 0.25, max: 0.85 } },
    shape: { type: "circle" },
    size: { value: { min: 1, max: 3.2 } },
    twinkle: {
      particles: {
        enable: true,
        frequency: 0.06,
        opacity: 1,
      },
    },
  },
};

onMounted(() => {
  requestAnimationFrame(() => {
    mounted.value = true;
  });
  fetchCaptcha();
});

async function fetchCaptcha() {
  captchaLoading.value = true;
  try {
    const { data } = await captchaApi();
    if (data?.code === 200 && data?.data?.uuid) {
      captchaUuid.value = data.data.uuid;
      captchaImage.value = data.data.image;
      form.value.captcha_uuid = captchaUuid.value;
    } else {
      ElMessage.error(data?.msg || "获取验证码失败");
    }
  } catch (error) {
    const msg =
      error?.response?.data?.msg ||
      error?.response?.data?.detail ||
      "获取验证码失败";
    ElMessage.error(msg);
    // eslint-disable-next-line no-console
    console.error(error);
  } finally {
    captchaLoading.value = false;
  }
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const payload = {
        username: form.value.username.trim(),
        password: form.value.password,
        captcha_code: form.value.captcha_code,
        captcha_uuid: form.value.captcha_uuid,
      };
      const { data } = await registerApi(payload);
      if (data?.code === 200) {
        ElMessage.success(data?.msg || "注册成功，请登录");
        await router.replace("/login");
        return;
      }
      ElMessage.error(data?.msg || "注册失败");
    } catch (error) {
      const msg =
        error?.response?.data?.captcha_code?.[0] ||
        error?.response?.data?.detail ||
        error?.response?.data?.msg ||
        "注册失败，请检查输入";
      ElMessage.error(msg);
      // eslint-disable-next-line no-console
      console.error(error);
    } finally {
      loading.value = false;
    }
  });
}

function goLogin() {
  router.replace("/login");
}
</script>

<style scoped lang="scss">
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background: radial-gradient(ellipse 120% 80% at 50% 20%, #0c1929 0%, #030712 45%, #020617 100%);
  color: #e2e8f0;
}

.login-page__particles {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: auto;

  :deep(#register-tsparticles) {
    width: 100%;
    height: 100%;
  }
}

.login-page__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  z-index: 1;
  opacity: 0.35;

  &--1 {
    width: min(55vw, 480px);
    height: min(55vw, 480px);
    top: -8%;
    left: -5%;
    background: radial-gradient(circle, rgba(34, 211, 238, 0.45) 0%, transparent 70%);
    animation: floatGlow 14s ease-in-out infinite;
  }

  &--2 {
    width: min(45vw, 380px);
    height: min(45vw, 380px);
    bottom: 5%;
    right: 10%;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%);
    animation: floatGlow 18s ease-in-out infinite reverse;
  }
}

@keyframes floatGlow {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }
  50% {
    transform: translate(24px, -18px) scale(1.06);
  }
}

.login-page__content {
  position: relative;
  z-index: 2;
  min-height: 100vh;
  display: flex;
  align-items: stretch;
  justify-content: center;
  gap: clamp(24px, 4vw, 64px);
  padding: clamp(24px, 4vw, 48px);
  box-sizing: border-box;
}

.login-hero {
  display: none;
  flex: 1 1 0;
  min-width: 0;
  position: relative;
  align-items: center;
  justify-content: center;
  max-width: 640px;
}

@media (min-width: 1024px) {
  .login-hero {
    display: flex;
  }
}

.login-hero__brain-wrap {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: brainFloat 8s ease-in-out infinite;
}

@keyframes brainFloat {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-12px);
  }
}

.login-hero__brain {
  width: min(52vw, 340px);
  max-height: 48vh;
  filter: drop-shadow(0 0 24px rgba(34, 211, 238, 0.25));
}

.login-hero__labels {
  position: absolute;
  inset: 0;
  list-style: none;
  margin: 0;
  padding: 0;
  pointer-events: none;
}

.login-hero__label {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: rgba(226, 232, 240, 0.85);
  background: rgba(15, 23, 42, 0.45);
  border: 1px solid rgba(34, 211, 238, 0.28);
  border-radius: 6px;
  backdrop-filter: blur(10px);
  box-shadow: 0 0 20px rgba(34, 211, 238, 0.08);
  white-space: nowrap;
  animation: labelPulse 5s ease-in-out infinite;

  &-icon {
    color: #22d3ee;
    flex-shrink: 0;
  }

  &--1 {
    top: 12%;
    left: 4%;
    animation-delay: 0s;
  }
  &--2 {
    top: 10%;
    right: 8%;
    animation-delay: 0.6s;
  }
  &--3 {
    top: 44%;
    right: 2%;
    animation-delay: 1.2s;
  }
  &--4 {
    bottom: 28%;
    right: 6%;
    animation-delay: 0.3s;
  }
  &--5 {
    bottom: 12%;
    left: 18%;
    animation-delay: 0.9s;
  }
}

@keyframes labelPulse {
  0%,
  100% {
    opacity: 0.85;
    box-shadow: 0 0 16px rgba(34, 211, 238, 0.06);
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 28px rgba(34, 211, 238, 0.14);
  }
}

.login-card-shell {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 440px;
}

@media (min-width: 1024px) {
  .login-card-shell {
    justify-content: flex-end;
    width: auto;
    min-width: 400px;
  }
}

.glass-card {
  position: relative;
  width: 100%;
  padding: 40px 36px 32px;
  border-radius: 20px;
  background: linear-gradient(
    145deg,
    rgba(15, 23, 42, 0.55) 0%,
    rgba(30, 41, 59, 0.42) 50%,
    rgba(15, 23, 42, 0.5) 100%
  );
  border: 1px solid rgba(34, 211, 238, 0.35);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    inset 0 -1px 0 rgba(0, 0, 0, 0.2),
    0 0 0 1px rgba(0, 0, 0, 0.15),
    0 25px 50px -12px rgba(0, 0, 0, 0.5),
    0 0 80px rgba(34, 211, 238, 0.06);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  opacity: 0;
  transform: translateY(20px);
  transition:
    opacity 0.65s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.65s cubic-bezier(0.22, 1, 0.36, 1);

  &--visible {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 480px) {
  .glass-card {
    padding: 32px 22px 26px;
    border-radius: 16px;
  }
}

.glass-card__tech-strip {
  position: absolute;
  top: 14px;
  right: 16px;
  display: flex;
  gap: 6px;
}

.glass-card__tech-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.35);
  border: 1px solid rgba(34, 211, 238, 0.15);
}

.glass-card__header {
  text-align: center;
  margin-bottom: 22px;
}

.glass-card__logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 12px;
  filter: drop-shadow(0 0 12px rgba(34, 211, 238, 0.35));

  svg {
    width: 100%;
    height: 100%;
  }
}

.glass-card__brand {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 0.04em;
  color: #f8fafc;
  text-shadow: 0 0 40px rgba(34, 211, 238, 0.25);
}

.glass-card__tagline {
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 500;
  color: rgba(148, 163, 184, 0.95);
  letter-spacing: 0.02em;
}

.glass-card__divider {
  height: 1px;
  margin: 22px 0 16px;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(34, 211, 238, 0.35) 20%,
    rgba(34, 211, 238, 0.35) 80%,
    transparent
  );
}

.glass-card__title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #e2e8f0;
  letter-spacing: 0.2em;
}

.glass-card__subtitle {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 500;
  color: rgba(148, 163, 184, 0.88);
  letter-spacing: 0.04em;
}

.glass-form :deep(.el-form-item__label) {
  display: none;
}

.glass-form__item {
  margin-bottom: 16px;

  &--captcha {
    margin-bottom: 18px;
  }
}

.glass-form__item--captcha :deep(.el-form-item__content) {
  line-height: normal;
}

.glass-form__submit {
  margin-bottom: 0;
  margin-top: 4px;
}

.glass-input {
  --el-input-text-color: #f1f5f9;
  --el-input-placeholder-color: rgba(148, 163, 184, 0.75);
  --el-input-icon-color: #94a3b8;
  --el-input-bg-color: transparent;
  --el-input-border-color: transparent;
  --el-input-hover-border-color: transparent;
  --el-input-focus-border-color: transparent;
  --el-input-transparent-border: 0;
  --el-input-border: 0;
}

.glass-input__icon {
  color: #64748b;
  flex-shrink: 0;
  transition: color 0.25s ease;
}

.glass-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.45) !important;
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
  padding-left: 12px;
  transition:
    box-shadow 0.28s ease,
    background 0.28s ease;
}

.glass-input :deep(.el-input__wrapper:hover:not(.is-focus)) {
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.22),
    inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}

.glass-input :deep(.el-input__wrapper.is-focus) {
  background: rgba(15, 23, 42, 0.65) !important;
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.85),
    0 0 0 4px rgba(34, 211, 238, 0.12),
    0 0 24px rgba(34, 211, 238, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
}

.glass-input :deep(.el-input__wrapper.is-focus) .glass-input__icon {
  color: #22d3ee;
}

.glass-input :deep(.el-input__inner) {
  color: #f1f5f9;
}

.glass-input :deep(.el-input__suffix .el-icon) {
  color: #94a3b8;
}

.captcha-merge {
  display: flex;
  align-items: stretch;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.45);
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition: box-shadow 0.28s ease, background 0.28s ease;
}

.captcha-merge:focus-within {
  background: rgba(15, 23, 42, 0.65);
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.85),
    0 0 0 4px rgba(34, 211, 238, 0.12),
    0 0 24px rgba(34, 211, 238, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.captcha-merge:focus-within .captcha-merge__input :deep(.glass-input__icon) {
  color: #22d3ee;
}

.captcha-merge__input {
  flex: 1;
  min-width: 0;
}

.captcha-merge__input :deep(.el-input__wrapper) {
  border-radius: 12px 0 0 12px;
  box-shadow: none !important;
  background: transparent !important;
}

.captcha-merge__input :deep(.el-input__wrapper:hover:not(.is-focus)) {
  box-shadow: none !important;
  background: transparent !important;
}

.captcha-merge__input :deep(.el-input__wrapper.is-focus) {
  box-shadow: none !important;
}

.captcha-merge__panel {
  position: relative;
  flex: 0 0 128px;
  width: 128px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 32px 6px 10px;
  border-left: 1px solid rgba(34, 211, 238, 0.18);
  background: rgba(15, 23, 42, 0.35);
  transition: border-color 0.2s ease, background 0.2s ease;
}

.captcha-merge:focus-within .captcha-merge__panel {
  border-left-color: rgba(34, 211, 238, 0.35);
  background: rgba(15, 23, 42, 0.5);
}

.captcha-merge__panel--placeholder {
  min-height: 40px;
}

.captcha-merge__loading-hint {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.9);
}

.captcha-merge__img {
  display: block;
  width: 100%;
  height: 32px;
  object-fit: contain;
  border-radius: 6px;
  background: rgba(248, 250, 252, 0.95);
  box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.15);
}

.captcha-merge__refresh {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 26px;
  height: 26px;
  padding: 0;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  color: #94a3b8;
  background: rgba(30, 41, 59, 0.85);
  border: 1px solid rgba(34, 211, 238, 0.2);
  transition:
    color 0.2s ease,
    box-shadow 0.25s ease,
    transform 0.35s ease,
    background 0.2s ease;
}

.captcha-merge__refresh:hover:not(:disabled) {
  color: #22d3ee;
  box-shadow: 0 0 14px rgba(34, 211, 238, 0.35);
  transform: rotate(180deg);
}

.captcha-merge__refresh:active:not(:disabled) {
  transform: rotate(360deg) scale(0.94);
}

.captcha-merge__refresh:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.captcha-merge__refresh-icon.is-spinning {
  animation: captcha-spin 0.85s linear infinite;
}

@keyframes captcha-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 480px) {
  .captcha-merge__panel,
  .captcha-merge__panel--placeholder {
    flex: 0 0 108px;
    width: 108px;
    padding-right: 30px;
  }
}

.glass-link {
  padding: 0;
  border: none;
  background: none;
  font-size: 13px;
  color: rgba(34, 211, 238, 0.85);
  cursor: pointer;
  transition: color 0.2s ease, text-shadow 0.2s ease;

  &:hover {
    color: #67e8f9;
    text-shadow: 0 0 12px rgba(34, 211, 238, 0.4);
  }

  &--strong {
    font-weight: 600;
  }
}

.neon-btn.el-button--primary {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #f8fafc !important;
  border: none !important;
  border-radius: 12px;
  background: linear-gradient(105deg, #2563eb 0%, #0891b2 45%, #22d3ee 100%) !important;
  box-shadow:
    0 0 20px rgba(34, 211, 238, 0.35),
    0 0 40px rgba(59, 130, 246, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    filter 0.25s ease !important;
}

.neon-btn.el-button--primary:hover,
.neon-btn.el-button--primary:focus {
  transform: translateY(-2px);
  filter: brightness(1.08);
  background: linear-gradient(105deg, #3b82f6 0%, #0e7490 42%, #67e8f9 100%) !important;
  box-shadow:
    0 0 32px rgba(34, 211, 238, 0.55),
    0 0 56px rgba(59, 130, 246, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
}

.neon-btn.el-button--primary:active {
  transform: translateY(0);
}

.neon-btn.el-button--primary.is-loading,
.neon-btn.el-button--primary:disabled {
  transform: none;
  filter: none;
}

.glass-card__footer {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
}

.glass-card__footer-muted {
  color: rgba(148, 163, 184, 0.85);
  margin-right: 4px;
}
</style>
