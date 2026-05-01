# Agent Hub Refactoring Guide

## Overview
This guide explains how to refactor the Agent Hub page and hide specific AI tool routes from the sidebar while keeping them accessible via URL navigation.

---

## 1. Router Configuration (Already Updated)

The router has been updated in `frontend/src/router/index.js` with the following changes:

### Added Routes with `hiddenInSidebar` Meta
```javascript
// Existing routes marked as hidden
{
  path: "execution/api-scenario-generator",
  name: "ApiScenarioGenerator",
  component: () => import("@/views/execution/ApiScenarioGenerator.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "element-library",
  name: "ElementLibrary",
  component: () => import("@/views/ElementLibrary.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ui-automation/generate",
  name: "UiAutomationGenerator",
  component: () => import("@/views/UiAutomationGenerator.vue"),
  meta: { hiddenInSidebar: true },
},

// New AI Agent routes (all hidden from sidebar)
{
  path: "ai-requirement-review",
  name: "AIRequirementReview",
  component: () => import("@/views/ai-agents/RequirementReview.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ai-testcase-generator",
  name: "AITestcaseGenerator",
  component: () => import("@/views/ai-agents/TestcaseGenerator.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ai-api-doc-analysis",
  name: "AIApiDocAnalysis",
  component: () => import("@/views/ai-agents/ApiDocAnalysis.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ai-api-testcase-design",
  name: "AIApiTestcaseDesign",
  component: () => import("@/views/ai-agents/ApiTestcaseDesign.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ai-api-script-generator",
  name: "AIApiScriptGenerator",
  component: () => import("@/views/ai-agents/ApiScriptGenerator.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ai-test-data-generator",
  name: "AITestDataGenerator",
  component: () => import("@/views/ai-agents/TestDataGenerator.vue"),
  meta: { hiddenInSidebar: true },
},
{
  path: "ai-performance-analysis",
  name: "AIPerformanceAnalysis",
  component: () => import("@/views/ai-agents/PerformanceAnalysis.vue"),
  meta: { hiddenInSidebar: true },
},
```

---

## 2. Sidebar Menu Update (MainLayout.vue)

### Current State
The sidebar menu in `MainLayout.vue` is **hardcoded** using `<el-menu-item>` components. It does not dynamically filter routes.

### Recommended Approach

You have **two options**:

#### **Option A: Keep Hardcoded Menu (Simpler)**
Since your menu is already hardcoded, simply **remove** the specific menu items you want to hide:

**Remove these lines from MainLayout.vue (around line 310-313):**
```vue
<!-- REMOVE THIS -->
<el-menu-item index="/execution/api-scenario-generator">接口场景生成</el-menu-item>
```

The "智能体中心" menu item at line 315-318 should **remain** as the main entry point:
```vue
<el-menu-item index="/agent-hub">
  <el-icon><MagicStick /></el-icon>
  <span>🤖 智能体中心</span>
</el-menu-item>
```

#### **Option B: Dynamic Menu (More Flexible)**
If you want a dynamic menu system that respects `meta.hiddenInSidebar`, you would need to:

1. Define a menu structure in the `<script setup>` section
2. Use `v-for` to render menu items
3. Filter out routes with `meta.hiddenInSidebar: true`

**Example implementation:**
```vue
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const menuItems = computed(() => {
  // Define your menu structure
  return [
    { index: '/dashboard', icon: 'HomeFilled', label: '工作台' },
    { index: '/test-approach', icon: 'Document', label: '测试方案' },
    // ... other items
    { 
      index: 'test-case', 
      icon: 'List', 
      label: '测试用例',
      children: [
        { index: '/test-case/functional', label: '功能测试' },
        { index: '/test-case/api', label: '接口测试' },
        // Don't include hidden routes here
        { index: '/test-case/performance', label: '性能测试' },
        { index: '/test-case/security', label: '安全测试' },
        { index: '/test-case/ui-automation', label: 'UI 自动化' },
      ]
    },
    { index: '/agent-hub', icon: 'MagicStick', label: '🤖 智能体中心' },
    // ... rest of menu
  ]
})
</script>
```

---

## 3. AgentHub.vue Component (Already Updated)

The `AgentHub.vue` file has been completely refactored with:

### Features
- ✅ Clean cyberpunk dark theme design
- ✅ Responsive grid layout (320px minimum card width)
- ✅ 8 AI agent cards with mock data
- ✅ Hover effects with neon glow and lift animation
- ✅ Circular avatar with gradient backgrounds
- ✅ AI badge with glowing effect
- ✅ Tag pills with cyan/blue styling
- ✅ Action button with arrow animation
- ✅ Placeholder card with dashed border
- ✅ Navigation to individual agent routes

### Mock Data Structure
```javascript
const agents = [
  {
    id: 1,
    name: 'AI 需求评审助手',
    icon: '📋',
    description: '智能分析需求文档...',
    tags: ['需求分析', '风险识别', '评审报告'],
    route: '/ai-requirement-review',
    avatarGradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  // ... 7 more agents
]
```

---

## 4. Implementation Steps

### Step 1: Update Sidebar (Choose Option A or B)
**Option A (Recommended):**
```vue
<!-- In MainLayout.vue, around line 308-313 -->
<!-- Remove or comment out: -->
<!-- <el-menu-item index="/execution/api-scenario-generator">接口场景生成</el-menu-item> -->
```

### Step 2: Create AI Agent Component Placeholders
Create placeholder components for the 7 new AI agents in `frontend/src/views/ai-agents/`:

```bash
mkdir -p frontend/src/views/ai-agents
```

Create these files:
- `RequirementReview.vue`
- `TestcaseGenerator.vue`
- `ApiDocAnalysis.vue`
- `ApiTestcaseDesign.vue`
- `ApiScriptGenerator.vue`
- `TestDataGenerator.vue`
- `PerformanceAnalysis.vue`

**Template for each placeholder:**
```vue
<template>
  <div class="ai-agent-page">
    <h1>AI 需求评审助手</h1>
    <p>功能开发中...</p>
  </div>
</template>

<script setup>
// Agent logic here
</script>

<style scoped>
.ai-agent-page {
  padding: 32px;
  color: #e2e8f0;
}
</style>
```

### Step 3: Test Navigation
1. Start your dev server
2. Navigate to `/agent-hub`
3. Click on each agent card
4. Verify routing works correctly
5. Check that hidden routes don't appear in sidebar

---

## 5. Design Specifications Summary

### Color Palette
- **Background:** `#0a0e1a` to `#1a1f2e` gradient
- **Card Background:** `rgba(255, 255, 255, 0.03)`
- **Border:** `rgba(100, 255, 218, 0.12)`
- **Primary Accent:** `#00d8ff` (cyan)
- **Text Primary:** `#e2e8f0`
- **Text Muted:** `rgba(148, 163, 184, 0.9)`

### Hover Effects
- **Transform:** `translateY(-4px)`
- **Border:** `rgba(0, 216, 255, 0.4)`
- **Box Shadow:** `0 8px 32px rgba(0, 216, 255, 0.2)`
- **Glow Effect:** Radial gradient overlay

### Typography
- **Title:** 42px, gradient text
- **Subtitle:** 16px, muted
- **Card Title:** 20px, bold
- **Description:** 14px, line-clamp-2

---

## 6. Next Steps

1. ✅ Router updated with hidden routes
2. ✅ AgentHub.vue refactored with cyberpunk design
3. ⏳ Update MainLayout.vue sidebar (remove hidden menu items)
4. ⏳ Create placeholder components for 7 new AI agents
5. ⏳ Implement actual AI agent functionality
6. ⏳ Test navigation flow end-to-end

---

## 7. File Checklist

- ✅ `frontend/src/router/index.js` - Routes with meta flags
- ✅ `frontend/src/views/AgentHub.vue` - Refactored hub page
- ⏳ `frontend/src/layouts/MainLayout.vue` - Sidebar cleanup
- ⏳ `frontend/src/views/ai-agents/*.vue` - 7 new agent pages

---

## Questions?

If you need help with:
- Creating the placeholder agent components
- Implementing dynamic sidebar filtering
- Adjusting the design/styling
- Adding more agents to the hub

Just let me know!
