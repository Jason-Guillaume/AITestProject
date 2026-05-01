<template>
  <div class="agent-hub-page">
    <!-- Header Section -->
    <div class="hub-header">
      <h1 class="hub-title">智能体中心</h1>
      <p class="hub-subtitle">智能'数字员工'中心，让测试降本增效</p>
    </div>

    <!-- Agent Grid -->
    <div class="agent-grid">
      <!-- Agent Cards -->
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
        @click="navigateToAgent(agent.route)"
      >
        <div class="card-glow"></div>

        <!-- Top Section: Avatar + Badge -->
        <div class="card-top">
          <div class="agent-avatar" :style="{ background: agent.avatarGradient }">
            <span class="avatar-icon">{{ agent.icon }}</span>
          </div>
          <div class="ai-badge">AI</div>
        </div>

        <!-- Title -->
        <h3 class="agent-title">{{ agent.name }}</h3>

        <!-- Description -->
        <p class="agent-description">{{ agent.description }}</p>

        <!-- Tags -->
        <div class="agent-tags">
          <span v-for="tag in agent.tags" :key="tag" class="tag-pill">
            {{ tag }}
          </span>
        </div>

        <!-- Action Button -->
        <button class="action-btn">
          <span>立即使用</span>
          <span class="arrow">→</span>
        </button>
      </div>

      <!-- Placeholder Card -->
      <div class="agent-card placeholder-card">
        <div class="placeholder-content">
          <div class="plus-icon">+</div>
          <p class="placeholder-text">更多智能体数字员工<br/>会不断更新上线</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();

// Mock data for 8 AI agents
const agents = [
  {
    id: 1,
    name: 'AI 需求评审助手',
    icon: '📋',
    description: '智能分析需求文档，自动识别功能点、边界条件和潜在风险，生成全面的评审报告和测试建议',
    tags: ['需求分析', '风险识别', '评审报告'],
    route: '/ai-requirement-review',
    avatarGradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  {
    id: 2,
    name: 'AI 测试用例智能体',
    icon: '🧪',
    description: '基于需求文档和业务场景，自动生成结构化测试用例，覆盖正向、逆向和边界场景',
    tags: ['用例生成', '场景覆盖', '智能推荐'],
    route: '/ai-testcase-generator',
    avatarGradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  {
    id: 3,
    name: 'AI 界面 UI 自动化脚本',
    icon: '🖥️',
    description: '输入页面URL和测试场景描述，自动生成完整的Selenium/Playwright UI自动化测试脚本',
    tags: ['UI自动化', '图文识别', 'Selenium'],
    route: '/ui-automation/workbench',
    avatarGradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  {
    id: 4,
    name: 'AI 接口文档分析',
    icon: '📡',
    description: '智能解析Swagger/OpenAPI文档，提取接口信息、参数规则和依赖关系，生成接口测试矩阵',
    tags: ['文档解析', 'API分析', '依赖识别'],
    route: '/ai-api-doc-analysis',
    avatarGradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  },
  {
    id: 5,
    name: 'AI 接口用例设计助手',
    icon: '🔗',
    description: '根据接口文档和业务规则，自动设计接口测试用例，包含参数组合、边界值和异常场景',
    tags: ['接口测试', '用例设计', '参数组合'],
    route: '/ai-api-testcase-design',
    avatarGradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
  },
  {
    id: 6,
    name: 'AI 接口自动化脚本助手',
    icon: '⚡',
    description: '基于接口用例自动生成Python/Java自动化测试脚本，支持断言、数据驱动和场景编排',
    tags: ['脚本生成', '自动化', '场景编排'],
    route: '/ai-api-script-generator',
    avatarGradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)'
  },
  {
    id: 7,
    name: 'AI 测试数据生成智能体',
    icon: '🎲',
    description: '根据数据模型和业务规则，智能生成符合真实场景的测试数据，支持批量生成和数据脱敏',
    tags: ['数据生成', '批量处理', '数据脱敏'],
    route: '/ai-test-data-generator',
    avatarGradient: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
  },
  {
    id: 8,
    name: 'AI 性能数据分析助手',
    icon: '📊',
    description: '分析性能测试结果数据，自动识别性能瓶颈、异常指标和趋势变化，提供优化建议',
    tags: ['性能分析', '瓶颈诊断', '趋势预测'],
    route: '/ai-performance-analysis',
    avatarGradient: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)'
  }
];

const navigateToAgent = (route) => {
  if (route) {
    router.push(route);
  }
};
</script>

<style scoped>
.agent-hub-page {
  min-height: 100vh;
  padding: 32px;
  background: linear-gradient(180deg, #0a0e1a 0%, #1a1f2e 100%);
}

/* Header Section */
.hub-header {
  margin-bottom: 48px;
  text-align: center;
}

.hub-title {
  font-size: 42px;
  font-weight: 700;
  color: #e2e8f0;
  margin: 0 0 12px 0;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #00d8ff 0%, #0ea5e9 50%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hub-subtitle {
  font-size: 16px;
  color: rgba(148, 163, 184, 0.8);
  margin: 0;
  font-weight: 400;
}

/* Agent Grid */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

/* Agent Card */
.agent-card {
  position: relative;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(100, 255, 218, 0.12);
  border-radius: 16px;
  padding: 28px;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(0, 216, 255, 0.08) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
  pointer-events: none;
}

.agent-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 216, 255, 0.4);
  box-shadow: 0 8px 32px rgba(0, 216, 255, 0.2),
              0 0 0 1px rgba(0, 216, 255, 0.1) inset;
}

.agent-card:hover .card-glow {
  opacity: 1;
}

/* Card Top Section */
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.agent-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  transition: transform 0.3s ease;
}

.agent-card:hover .agent-avatar {
  transform: scale(1.08) rotate(5deg);
}

.avatar-icon {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.ai-badge {
  padding: 4px 12px;
  background: rgba(0, 216, 255, 0.15);
  border: 1px solid rgba(0, 216, 255, 0.4);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #00d8ff;
  letter-spacing: 1px;
  text-shadow: 0 0 8px rgba(0, 216, 255, 0.5);
}

/* Title */
.agent-title {
  font-size: 20px;
  font-weight: 600;
  color: #f1f5f9;
  margin: 0 0 12px 0;
  line-height: 1.3;
}

/* Description */
.agent-description {
  font-size: 14px;
  color: rgba(148, 163, 184, 0.9);
  line-height: 1.6;
  margin: 0 0 20px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  min-height: 44px;
}

/* Tags */
.agent-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}

.tag-pill {
  padding: 5px 12px;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 12px;
  font-size: 12px;
  color: #06b6d4;
  font-weight: 500;
  white-space: nowrap;
}

/* Action Button */
.action-btn {
  width: 100%;
  padding: 12px 20px;
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
  border: none;
  border-radius: 10px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
}

.action-btn:hover {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.5);
  transform: translateY(-2px);
}

.action-btn .arrow {
  font-size: 18px;
  transition: transform 0.3s ease;
}

.action-btn:hover .arrow {
  transform: translateX(4px);
}

/* Placeholder Card */
.placeholder-card {
  background: rgba(255, 255, 255, 0.02);
  border: 2px dashed rgba(100, 255, 218, 0.2);
  cursor: default;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
}

.placeholder-card:hover {
  transform: none;
  border-color: rgba(100, 255, 218, 0.3);
  box-shadow: none;
}

.placeholder-content {
  text-align: center;
}

.plus-icon {
  font-size: 64px;
  color: rgba(100, 255, 218, 0.3);
  margin-bottom: 16px;
  font-weight: 300;
}

.placeholder-text {
  font-size: 15px;
  color: rgba(148, 163, 184, 0.7);
  line-height: 1.6;
  margin: 0;
}

/* Responsive Design */
@media (max-width: 1400px) {
  .agent-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 768px) {
  .agent-hub-page {
    padding: 20px;
  }

  .hub-title {
    font-size: 32px;
  }

  .hub-subtitle {
    font-size: 14px;
  }

  .agent-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
</style>
