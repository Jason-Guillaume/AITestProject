<template>
  <div class="script-hub-container">
    <!-- 顶部 Header -->
    <div class="hub-header">
      <h1 class="hub-title">脚本执行中心</h1>
      <p class="hub-subtitle">统一管理与执行各类自动化测试工程</p>
    </div>

    <!-- 主体 Content -->
    <div class="hub-content">
      <el-row :gutter="24">
        <el-col
          v-for="module in modules"
          :key="module.id"
          :xs="24"
          :sm="12"
          :md="12"
          :lg="6"
        >
          <el-card class="module-card" :body-style="{ padding: '24px' }">
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
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  Monitor,
  Connection,
  Iphone,
  TrendCharts
} from '@element-plus/icons-vue'

const router = useRouter()

interface ModuleItem {
  id: string
  title: string
  description: string
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
    icon: Monitor,
    available: true,
    buttonText: '进入工作台 ->',
    route: '/script-hub/webui'
  },
  {
    id: 'api',
    title: '接口自动化 (API)',
    description: '支持 HttpRunner/Pytest 接口工程的编排与高并发执行。',
    icon: Connection,
    available: false,
    buttonText: '敬请期待'
  },
  {
    id: 'app',
    title: 'App 自动化',
    description: '支持 Appium 移动端 UI 脚本执行与设备集群调度。',
    icon: Iphone,
    available: false,
    buttonText: '敬请期待'
  },
  {
    id: 'performance',
    title: '性能压测脚本',
    description: '支持 JMeter/K6 等压测脚本的分布式压测引擎调用。',
    icon: TrendCharts,
    available: false,
    buttonText: '敬请期待'
  }
]

const handleNavigate = (route?: string) => {
  if (route) {
    router.push(route)
  }
}
</script>

<style scoped>
.script-hub-container {
  min-height: 100vh;
  background-color: #141414;
  padding: 40px 24px;
}

/* 顶部 Header 样式 */
.hub-header {
  text-align: center;
  margin-bottom: 48px;
}

.hub-title {
  font-size: 36px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px 0;
  letter-spacing: 2px;
  text-shadow: 0 0 20px rgba(64, 158, 255, 0.5);
}

.hub-subtitle {
  font-size: 16px;
  color: #8c8c8c;
  margin: 0;
  letter-spacing: 1px;
}

/* 主体内容区域 */
.hub-content {
  max-width: 1400px;
  margin: 0 auto;
}

/* 模块卡片样式 */
.module-card {
  background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
  border: 1px solid rgba(64, 158, 255, 0.15);
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  height: 100%;
  display: flex;
  flex-direction: column;
  margin-bottom: 24px;
}

.module-card:hover {
  transform: translateY(-8px);
  border-color: rgba(64, 158, 255, 0.6);
  box-shadow:
    0 8px 24px rgba(64, 158, 255, 0.25),
    0 0 40px rgba(64, 158, 255, 0.15),
    inset 0 0 20px rgba(64, 158, 255, 0.05);
}

/* 卡片图标区域 */
.card-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(64, 158, 255, 0.05) 100%);
  border-radius: 16px;
  border: 1px solid rgba(64, 158, 255, 0.2);
  color: #409eff;
  transition: all 0.3s ease;
}

.module-card:hover .card-icon {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.2) 0%, rgba(64, 158, 255, 0.1) 100%);
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.3);
  transform: scale(1.05);
}

/* 卡片标题 */
.card-title {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  text-align: center;
  margin: 0 0 16px 0;
  letter-spacing: 1px;
}

/* 卡片描述文案 */
.card-description {
  font-size: 14px;
  color: #a0a0a0;
  line-height: 1.8;
  text-align: center;
  margin: 0 0 24px 0;
  min-height: 84px;
}

/* 卡片操作区域 */
.card-action {
  text-align: center;
  margin-top: auto;
}

.action-button {
  width: 100%;
  height: 40px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 1px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.action-button.el-button--primary {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.action-button.el-button--primary:hover {
  background: linear-gradient(135deg, #66b1ff 0%, #409eff 100%);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.5);
  transform: translateY(-2px);
}

.action-button.el-button--info {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #666666;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .hub-title {
    font-size: 32px;
  }
}

@media (max-width: 768px) {
  .script-hub-container {
    padding: 24px 16px;
  }

  .hub-title {
    font-size: 28px;
  }

  .hub-subtitle {
    font-size: 14px;
  }

  .card-description {
    min-height: auto;
  }
}
</style>
