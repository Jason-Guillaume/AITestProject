<template>
  <div class="script-hub-container">
    <!-- Header -->
    <div class="hub-header">
      <h1 class="hub-title">脚本执行中心</h1>
       <p class="hub-subtitle">统一管理与执行各类自动化测试工程</p>
    </div>

    <!-- Main content -->
    <div class="hub-content">
      <!-- Primary modules (excluding H5) -->
      <div class="modules-grid">
        <div v-for="module in modules.filter(m => m.id !== 'h5')" :key="module.id" class="module-card">
          <!-- Status indicator: small amber dot when module is online/available -->
          <div class="status-indicator" v-if="module.available"></div>
          <div class="card-icon">
            <component :is="module.icon" :size="48" />
          </div>
          <h3 class="card-title">{{ module.title }}</h3>
          <p class="card-description">{{ module.description }}</p>
          <div class="card-action">
            <el-button
              :type="module.available ? 'primary' : 'info'"
              :disabled="!module.available"
              class="action-button"
              @click="handleNavigate(module.route)"
            >
              {{ module.buttonText }}
            </el-button>
          </div>
          <!-- Explanation text for each functional template -->
          <p v-if="module.explanation" class="module-explanation">
            {{ module.explanation }}
          </p>
        </div>
      </div>
      <!-- H5 专属入口，单独展示 -->
      <div class="modules-grid" style="margin-top: 48px;">
        <div v-for="module in modules.filter(m => m.id === 'h5')" :key="module.id" class="module-card">
          <div class="status-indicator" v-if="module.available"></div>
          <div class="card-icon">
            <component :is="module.icon" :size="48" />
          </div>
          <h3 class="card-title">{{ module.title }}</h3>
          <p class="card-description">{{ module.description }}</p>
          <div class="card-action">
            <el-button
              :type="module.available ? 'primary' : 'info'"
              :disabled="!module.available"
              class="action-button"
              @click="handleNavigate(module.route)"
            >
              {{ module.buttonText }}
            </el-button>
          </div>
          <p v-if="module.explanation" class="module-explanation">
            {{ module.explanation }}
          </p>
        </div>
      </div>
    </div>
    <!-- No terminal/log panel needed -->
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  Monitor,
  Connection,
  Iphone,
  TrendCharts,
  Document,
} from '@element-plus/icons-vue'

const router = useRouter()

interface ModuleItem {
  id: string
  title: string
  description: string
  /**
   * Detailed explanation for this functional template.
   * This will be displayed as a centered caption below the action button.
   */
  explanation?: string
  icon: any
  available: boolean
  buttonText: string
  route?: string
}

const modules: ModuleItem[] = [
  {
    id: 'webui',
    title: 'Web UI 自动化',
    description: '支持 Selenium/Playwright 框架，兼容线性脚本与 POM 工程的导入与沙箱执行。',
    explanation: 'Web UI 自动化模块提供浏览器层面的脚本编写与执行，适用于前端功能回归。',
    icon: Monitor,
    available: true,
    buttonText: '进入工作台 ->',
    route: '/script-hub/webui'
  },
  {
    id: 'pom-reports',
    title: 'UI / POM 测试报告',
    description: '执行完成后自动从工作空间提取 HTML 报告并归档，支持列表、预览与下载。',
    explanation: '与 Web UI 工作台执行联动；BeautifulReport、pytest-html 等生成的 .html 可被识别归档。',
    icon: Document,
    available: true,
    buttonText: '进入报告管理',
    route: '/script-hub/pom-reports'
  },
    {
      id: 'api',
      title: '接口自动化 (API)',
      description: '支持 HttpRunner/Pytest 接口工程的编排与高并发执行。',
      explanation: 'API 自动化模块用于发送 HTTP 请求，验证后端接口的正确性与性能。',
      icon: Connection,
      available: false,
      buttonText: '敬请期待'
    },
    {
      id: "app",
      title: "App 自动化",
      description: "支持 Appium 移动端 UI 脚本执行与设备集群调度。",
      explanation: "App 自动化模块利用 Appium 在真实设备或模拟器上执行移动端 UI 测试。",
      icon: Iphone,
      available: false,
      buttonText: "敬请期待"
    },
    {
      id: "performance",
      title: "性能压测脚本",
      description: "支持 JMeter/K6 等压测脚本的分布式压测引擎调用。",
      explanation: "性能压测模块提供对系统在高并发下的响应时间、吞吐量等指标进行评估。",
      icon: TrendCharts,
      available: false,
      buttonText: "敬请期待"
    },
    // 新增 H5 自动化入口（暂未上线）
    {
      id: "h5",
      title: "H5 自动化",
      description: "针对移动端 H5 页面提供基于浏览器的脚本编写与执行。",
      explanation: "H5 自动化模块帮助在移动端浏览器环境中验证页面交互与布局。",
      icon: Monitor,
      available: false,
      buttonText: "敬请期待",
      // route 保留以便后续开启后直接跳转
      route: "/script-hub/h5"
    },
    // 新增 小程序 自动化入口
    {
      id: "miniapp",
      title: "小程序 自动化",
      description: "支持微信/支付宝等小程序脚本的录制、编辑与执行。",
      explanation: "小程序自动化模块提供对原生小程序 UI 与 API 的自动化测试能力。",
      icon: Connection,
      available: false,
      buttonText: "敬请期待"
    }
]

const handleNavigate = (route?: string) => {
  if (route) {
    router.push(route)
  }
}
</script>

<style scoped>
/* Design System Variables scoped to the container */
.script-hub-container {
  --c-cyan: #00d8ff;        /* Primary accent – cyber‑cyan */
  --bg-from: #0a0e1a;      /* Background gradient – deep sci‑fi blue‑gray */
  --bg-to: #1a1f2e;
  --run-accent: #ffbf00;   /* Running/active state accent – neon‑amber */

  /* Layout and background */
  min-height: 100vh;
  background: linear-gradient(180deg, var(--bg-from) 0%, var(--bg-to) 100%);
  color: #e2e8f0; /* light text for contrast */
}

/* Header – similar vibe to AgentHub */
/* Header and subtitle */
.hub-title {
  font-size: 36px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--c-cyan) 0%, #0ea5e9 70%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 12px 0;
  letter-spacing: 2px;
  text-shadow: 0 0 20px rgba(0, 216, 255, 0.5);
}

.hub-subtitle {
  font-size: 16px;
  color: rgba(148, 163, 184, 0.8);
  margin: 0;
  letter-spacing: 1px;
}

/* Center header texts */
.hub-header {
  text-align: center;
  margin-bottom: 24px;
}

/* Main modules grid – irregular spans */
.hub-content {
  display: grid;
  gap: 24px;
  grid-template-columns: 1fr;
  max-width: 1600px;
  margin: 0 auto;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin-top: 32px; /* push modules down a bit */
  justify-items: center; /* center each card within its grid cell */
}

/* Card redesign – command‑panel style */
.module-card {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(0, 216, 255, 0.12);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
  backdrop-filter: blur(8px);
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 0.35s;
}

.module-card:hover {
  transform: translateY(-4px);
  border-color: var(--c-cyan);
  box-shadow: 0 8px 32px rgba(0, 216, 255, 0.2),
    inset 0 0 0 1px rgba(0, 216, 255, 0.1);
}

/* Status indicator – breathing light */
.status-indicator {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--run-accent);
  box-shadow: 0 0 6px var(--run-accent);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.6; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.2); }
  100% { opacity: 0.6; transform: scale(0.9); }
}

/* Icon container – sci‑fi glow */
.card-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.1) 0%, rgba(0, 216, 255, 0.05) 100%);
  border: 1px solid rgba(0, 216, 255, 0.2);
  color: var(--c-cyan);
  transition: transform 0.3s ease, background 0.3s ease;
}

.module-card:hover .card-icon {
  background: linear-gradient(135deg, rgba(0, 216, 255, 0.2) 0%, rgba(0, 216, 255, 0.1) 100%);
  box-shadow: 0 0 20px rgba(0, 216, 255, 0.3);
  transform: scale(1.05);
}

/* Title & description use light colors */
  .card-title {
    font-size: 20px;
    font-weight: 600;
    color: #f1f5f9;
    text-align: center;
    margin: 0 0 12px;
  }

  .card-description {
    font-size: 14px;
    color: rgba(148, 163, 184, 0.9);
    line-height: 1.6;
    text-align: center;
    margin: 0 0 20px;
    min-height: 60px;
  }

  /* New explanation text style – slightly smaller and lighter */
  .module-explanation {
    font-size: 13px;
    color: rgba(148, 163, 184, 0.7);
    text-align: center;
    margin-top: 8px;
  }

/* Action button – mechanical feel */
.action-button {
  width: 100%;
  padding: 10px 0;
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  border: none;
  border-radius: 10px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: background 0.3s ease, transform 0.2s ease;
}

.action-button:hover {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 216, 255, 0.3);
}

/* Log panel removed as per user request (no longer needed) */

/* Responsive tweaks */
@media (max-width: 1200px) {
  .hub-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .script-hub-container {
    padding: 24px 16px;
  }
  .hub-title { font-size: 28px; }
  .hub-subtitle { font-size: 14px; }
}
</style>
