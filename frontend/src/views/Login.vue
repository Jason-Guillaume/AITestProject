<!--
  依赖安装（若 package.json 中尚未添加）:
  npm install lucide-vue-next @tsparticles/vue3 tsparticles @tsparticles/slim

  并在 main.js 中注册 tsparticles 插件（与本项目一致）:
  import Particles from "@tsparticles/vue3";
  import { loadSlim } from "@tsparticles/slim";
  createApp(App).use(Particles, { init: async (engine) => { await loadSlim(engine); } })
-->
<template>
  <div class="login-page">
    <!-- 全屏粒子神经网络背景 -->
    <div class="login-page__particles" aria-hidden="true">
      <vue-particles id="login-tsparticles" :options="particleOptions" />
    </div>

    <!-- 氛围光斑 -->
    <div class="login-page__glow login-page__glow--1" aria-hidden="true" />
    <div class="login-page__glow login-page__glow--2" aria-hidden="true" />

    <div class="login-page__content">
      <!-- 左侧：科技标签 + 装饰（大屏显示） -->
      <aside class="login-hero" aria-hidden="true">
        <div class="login-hero__brain-wrap">
          <svg class="login-hero__brain" viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="brainLine" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.9" />
                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.5" />
              </linearGradient>
              <filter id="brainGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="b" />
                <feMerge>
                  <feMergeNode in="b" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <g fill="none" stroke="url(#brainLine)" stroke-width="0.8" filter="url(#brainGlow)" opacity="0.85">
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

      <!-- 右侧玻璃拟态登录卡片 -->
      <div class="login-card-shell">
        <div class="glass-card" :class="{ 'glass-card--visible': mounted }">
          <header class="glass-card__header">
            <div class="glass-card__logo" aria-hidden="true">
              <svg viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="atRing" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#22d3ee" />
                    <stop offset="100%" stop-color="#3b82f6" />
                  </linearGradient>
                </defs>
                <circle cx="28" cy="28" r="26" fill="none" stroke="url(#atRing)" stroke-width="1.5" opacity="0.9" />
                <circle cx="28" cy="28" r="22" fill="none" stroke="url(#atRing)" stroke-width="0.6" opacity="0.35" />
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
            <h2 class="glass-card__title">登录</h2>
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
                autocomplete="current-password"
                placeholder="密码"
                class="glass-input"
                @keyup.enter="handleSubmit"
              >
                <template #prefix>
                  <Lock class="glass-input__icon" :size="18" stroke-width="2" />
                </template>
              </el-input>
            </el-form-item>

            <div class="glass-form__row">
              <label class="glass-check">
                <input v-model="rememberMe" type="checkbox" class="glass-check__input" />
                <span class="glass-check__box" />
                <span class="glass-check__text">记住我</span>
              </label>
              <button type="button" class="glass-link" @click="onForgotPassword">忘记密码？</button>
            </div>

            <el-form-item class="glass-form__submit">
              <el-button
                class="neon-btn"
                type="primary"
                size="large"
                :loading="loading"
                native-type="button"
                @click="handleSubmit"
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>

          <footer class="glass-card__footer">
            <span class="glass-card__footer-muted">没有账号？</span>
            <button type="button" class="glass-link glass-link--strong" @click="goRegister">立即注册</button>
          </footer>

          <!-- 顶部装饰：极简 tech 图标条 -->
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
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock, FileSearch, RefreshCw } from "lucide-vue-next";
import { loginApi } from "@/api/auth";

const route = useRoute();
const router = useRouter();
const formRef = ref();
const loading = ref(false);
const mounted = ref(false);
const rememberMe = ref(!!localStorage.getItem("login_remember_username"));

const form = ref({
  username: localStorage.getItem("saved_username") || "",
  password: "",
});

const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
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
});

function onForgotPassword() {
  ElMessage.info("请联系管理员重置密码");
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const { data } = await loginApi({
        username: form.value.username.trim(),
        password: form.value.password,
      });
      if (data?.code === 200 && data?.data?.token) {
        if (rememberMe.value) {
          localStorage.setItem("login_remember_username", "1");
          localStorage.setItem("saved_username", form.value.username.trim());
        } else {
          localStorage.removeItem("login_remember_username");
          localStorage.removeItem("saved_username");
        }
        localStorage.setItem("token", data.data.token);
        if (data?.data?.user_id) localStorage.setItem("user_id", String(data.data.user_id));
        if (data?.data?.real_name) localStorage.setItem("real_name", String(data.data.real_name));
        const display = data?.data?.real_name || data?.data?.username || "Admin";
        localStorage.setItem("username", display);
        localStorage.setItem("is_system_admin", data?.data?.is_system_admin ? "1" : "0");
        ElMessage.success(data.msg || "登录成功");
        let redirect = "/dashboard";
        const q = route.query.redirect;
        if (typeof q === "string" && q.startsWith("/") && !q.startsWith("//")) {
          redirect = q;
        }
        await router.replace(redirect);
        return;
      }
      ElMessage.error(data?.msg || "登录失败");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail[0]
            : err?.response?.data?.msg || "登录失败，请检查账号密码";
      ElMessage.error(msg);
    } finally {
      loading.value = false;
    }
  });
}

function goRegister() {
  router.push("/register");
}

/** 顶栏头像占位图加载失败时用内联 SVG，避免裂图 */
function onAvatarImgError(e) {
  const svg =
    "data:image/svg+xml," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect fill="%230f172a" width="128" height="128"/><circle fill="%2322d3ee" opacity=".25" cx="64" cy="48" r="28"/><path fill="%2394a3b8" d="M24 122c8-36 72-36 80 0z"/></svg>'
    );
  e.target.src = svg;
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

  :deep(#login-tsparticles) {
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
  margin-bottom: 28px;
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

.glass-form :deep(.el-form-item__label) {
  display: none;
}

.glass-form__item {
  margin-bottom: 18px;
}

.glass-form__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 22px;
  margin-top: -4px;
}

.glass-form__submit {
  margin-bottom: 0;
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

.glass-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: rgba(203, 213, 225, 0.9);
}

.glass-check__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.glass-check__box {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid rgba(34, 211, 238, 0.35);
  background: rgba(15, 23, 42, 0.5);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.glass-check__input:checked + .glass-check__box {
  background: linear-gradient(135deg, #22d3ee, #3b82f6);
  border-color: rgba(34, 211, 238, 0.8);
  box-shadow: 0 0 12px rgba(34, 211, 238, 0.35);
}

.glass-check__input:focus-visible + .glass-check__box {
  outline: 2px solid #22d3ee;
  outline-offset: 2px;
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
  margin-top: 22px;
  text-align: center;
  font-size: 13px;
}

.glass-card__footer-muted {
  color: rgba(148, 163, 184, 0.85);
  margin-right: 4px;
}
</style>
