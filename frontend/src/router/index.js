import { createRouter, createWebHistory } from "vue-router";

import MainLayout from "@/layouts/MainLayout.vue";

const routes = [
  // keepAlive 要求组件 <script> 中定义与路由 name 一致的 name 属性，
  // 否则 <keep-alive> 缓存失效。已标记 keepAlive 的路由：
  // Dashboard → name:"Dashboard", TestCase → name:"TestCase",
  // AgentHub → name:"AgentHub", DefectList → name:"DefectList",
  // PipelineList → name:"PipelineList", ServerLogs → name:"ServerLogs"
  { path: "/", redirect: "/dashboard" },

  { path: "/login", name: "Login", component: () => import("@/views/Login.vue"), meta: { public: true } },
  { path: "/register", name: "Register", component: () => import("@/views/Register.vue"), meta: { public: true } },
  // Note: Pipeline routes are now defined as children of the main layout to inherit the common UI.

  // 性能任务页：保持单独布局（不进入 MainLayout）
  {
    path: "/performance/tasks",
    name: "PerformanceTaskManagement",
    component: () => import("@/views/performance/TaskManagement.vue"),
    meta: { public: false },
  },
  {
    path: "/performance/scheduled-task/:id?",
    name: "ScheduledTaskDetail",
    component: () => import("@/views/performance/ScheduledTaskDetail.vue"),
    meta: { public: false },
  },
  {
    path: "/performance/scheduled-tasks",
    name: "ScheduledTaskList",
    component: () => import("@/views/performance/ScheduledTaskList.vue"),
    meta: { public: false },
  },
  {
    path: "/performance/scheduled-task-logs",
    name: "ScheduledTaskLog",
    component: () => import("@/views/performance/ScheduledTaskLog.vue"),
    meta: { public: false },
  },
  {
    path: "/performance/k6-sessions",
    name: "K6SessionList",
    component: () => import("@/views/performance/K6SessionList.vue"),
    meta: { public: false },
  },

  // 业务主布局：侧边栏 + 顶部栏 + router-view
  {
    path: "/",
    component: MainLayout,
    meta: { public: false },
    children: [
      { path: "dashboard", component: () => import("@/views/Dashboard.vue"), meta: { keepAlive: true } },
      { path: "user/center", component: () => import("@/views/UserCenter.vue") },
      { path: "projects", component: () => import("@/views/ProjectManagement.vue") },

      { path: "test-approach", component: () => import("@/views/TestApproach.vue") },
      { path: "test-design", component: () => import("@/views/TestDesign/index.vue") },
      { path: "test-design/:id", component: () => import("@/views/TestDesign/Detail.vue") },
      { path: "test-plan", component: () => import("@/views/TestPlan/index.vue") },
      { path: "test-plan/:id", component: () => import("@/views/TestPlan/Detail.vue") },
      { path: "test-case", redirect: "/test-case/functional" },
      {
        path: "test-case/api",
        name: "ApiTest",
        component: () => import("@/views/ApiTest.vue"),
      },
      {
        path: "execution/api-scenario-generator",
        name: "ApiScenarioGenerator",
        component: () => import("@/views/execution/ApiScenarioGenerator.vue"),
        meta: { hiddenInSidebar: true },
      },
      {
        path: "agent-hub",
        name: "AgentHub",
        component: () => import("@/views/AgentHub.vue"),
        meta: { keepAlive: true },
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
      {
        path: "ui-automation/workbench",
        name: "UiAutomationWorkbench",
        component: () => import("@/views/UiAutomationWorkbench.vue"),
        meta: { hiddenInSidebar: true },
      },
      // Hidden AI Agent Routes - Accessible via Agent Hub
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
      {
        path: "test-case/:type",
        name: "TestCase",
        component: () => import("@/views/TestCase.vue"),
        meta: { keepAlive: true },
      },
      { path: "test-report", component: () => import("@/views/TestReport/index.vue") },
      { path: "test-report/:id", component: () => import("@/views/TestReport/Detail.vue") },
      { path: "quality-dashboard", component: () => import("@/views/QualityDashboard.vue") },

      {
        path: "performance/load-monitor",
        name: "LoadTestMonitor",
        component: () => import("@/views/performance/LoadTestMonitor.vue"),
      },
      {
        path: "cicd",
        name: "CicdPipelines",
        component: () => import("@/views/cicd/Index.vue"),
        meta: { title: "CI/CD" },
      },
      {
        path: "cicd/pipeline/:id",
        name: "CicdPipelineDetail",
        component: () => import("@/views/cicd/PipelineDetail.vue"),
        meta: { title: "流水线日志", hiddenInSidebar: true },
      },
      {
        path: "performance/environments",
        name: "EnvironmentManagement",
        component: () => import("@/views/performance/EnvironmentManagement.vue"),
      },

      { path: "defect/list", component: () => import("@/views/defect/DefectList.vue"), meta: { keepAlive: true } },
      { path: "defect/board", component: () => import("@/views/defect/TaskBoard.vue") },
      { path: "defect/release", component: () => import("@/views/defect/ReleasePlan.vue") },
      { path: "defect/detail", component: () => import("@/views/defect/DefectDetail.vue") },
      { path: "defect/detail/:id", component: () => import("@/views/defect/DefectDetail.vue") },
      { path: "defect/release/:id", component: () => import("@/views/defect/ReleasePlanDetail.vue") },

      { path: "ai-assistant", component: () => import("@/views/AiAssistant.vue") },
      // CI/CD pipeline pages – display within the main layout for a consistent UI.
      {
        path: "pipelines/new",
        name: "PipelineCreate",
        component: () => import("@/views/PipelineCreate.vue"),
        meta: { public: true },
      },
      { path: "pipelines", name: "PipelineList", component: () => import("@/views/PipelineList.vue"), meta: { public: true, keepAlive: true } },
      { path: "pipelines/:id", name: "PipelineDetail", component: () => import("@/views/PipelineDetail.vue"), meta: { public: true } },
      {
        path: "server-logs",
        name: "ServerLogs",
        component: () => import("@/views/server_logs/index.vue"),
        meta: { keepAlive: true },
      },

      // 自动化指挥中心（原 script-hub，旧路径重定向保留书签兼容）
      { path: "script-hub", redirect: "/automation-center/web" },
      {
        path: "script-hub/webui",
        redirect: (to) => ({
          path: "/automation-center/webui",
          query: to.query,
          hash: to.hash,
        }),
      },
      {
        path: "script-hub/pom-reports",
        redirect: (to) => ({
          path: "/automation-center/pom-reports",
          query: to.query,
          hash: to.hash,
        }),
      },
      {
        path: "automation-center",
        component: () => import("@/views/automation-center/AutomationCenterLayout.vue"),
        meta: { title: "自动化指挥中心" },
        redirect: { name: "AutomationCenterWeb" },
        children: [
          { path: "mini-h5", redirect: { name: "AutomationCenterMiniprogram" } },
          {
            path: "web",
            name: "AutomationCenterWeb",
            component: () => import("@/views/automation-center/WebAutomationTree.vue"),
            meta: { platform: "web", title: "Web" },
          },
          {
            path: "mobile",
            name: "AutomationCenterMobile",
            component: () => import("@/views/automation-center/MobileAutomationTree.vue"),
            meta: { platform: "mobile", title: "Mobile" },
          },
          {
            path: "api",
            name: "AutomationCenterApi",
            component: () => import("@/views/automation-center/ApiAutomationTree.vue"),
            meta: { platform: "api", title: "API" },
          },
          {
            path: "miniprogram",
            name: "AutomationCenterMiniprogram",
            component: () => import("@/views/automation-center/MiniprogramAutomationTree.vue"),
            meta: { platform: "miniprogram", title: "小程序" },
          },
          {
            path: "h5",
            name: "AutomationCenterH5",
            component: () => import("@/views/automation-center/H5AutomationTree.vue"),
            meta: { platform: "h5", title: "H5" },
          },
        ],
      },
      {
        path: "automation-center/webui",
        name: "WebUIScriptWorkbench",
        component: () => import("@/views/script/WebUIWorkbench.vue"),
        meta: { hiddenInSidebar: true },
      },
      {
        path: "automation-center/pom-reports",
        name: "UiPomReportManagement",
        component: () => import("@/views/script/UiPomReportManagement.vue"),
        meta: { hiddenInSidebar: true },
      },
      {
        path: "automation-center/recycle-bin",
        name: "AutomationCenterRecycleBin",
        component: () => import("@/views/automation-center/UiScriptRecycleBin.vue"),
        meta: { title: "回收站" },
      },
      {
        path: "automation-center/assets",
        name: "AutomationCenterAssetHub",
        component: () => import("@/views/automation-center/AssetHub.vue"),
        meta: { title: "资产中心" },
      },

      // Analysis Lab（分析实验室）：深度报告多态布局
      {
        path: "analysis-lab",
        name: "AnalysisLab",
        component: () => import("@/views/analysis-lab/AnalysisLabIndex.vue"),
        meta: { title: "Analysis Lab" },
      },
      {
        path: "analysis-lab/reports/:id",
        name: "AnalysisLabReportDepth",
        component: () => import("@/views/analysis-lab/ReportDepthDetail.vue"),
        meta: { title: "Depth Report", hiddenInSidebar: true },
      },
      {
        path: "analysis-lab/report/:id",
        redirect: (to) => ({
          path: `/analysis-lab/reports/${String(to.params.id ?? "")}`,
          query: to.query,
          hash: to.hash,
        }),
      },

      // system / knowledge / help 占位
      { path: "system/message", component: () => import("@/views/system/MessageSetting.vue") },
      { path: "system/messages", component: () => import("@/views/system/MessageManage.vue") },
      { path: "system/org", component: () => import("@/views/system/OrgManagement.vue") },
      { path: "system/role", component: () => import("@/views/system/RoleManagement.vue") },
      { path: "system/user", component: () => import("@/views/system/UserManagement.vue") },
      { path: "system/ai-usage", component: () => import("@/views/system/AiUsageDashboard.vue") },
      { path: "system/ai-quota", component: () => import("@/views/system/AiQuotaPolicies.vue") },
      { path: "system/audit", component: () => import("@/views/system/AuditEvents.vue") },
      { path: "user/audit", component: () => import("@/views/system/AuditEvents.vue") },
      { path: "knowledge", component: () => import("@/views/system/KnowledgeCenter.vue") },
      { path: "knowledge/ask", component: () => import("@/views/system/KnowledgeAsk.vue") },
        { path: "help", component: () => import("@/views/system/HelpCenter.vue") },
      ],
    },

    // 兜底：未知路径跳回首页（避免空白页/刷新 404）
    { path: "/:catchAll(.*)", redirect: "/" },
  ];

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 避免 hash 仅为 "#" 时 Vue Router 开发模式下对 getElementById("") 的告警
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.hash && to.hash.length > 1) return { el: to.hash };
    return { top: 0 };
  },
});

const SYSTEM_ADMIN_ONLY_PREFIXES = [
  "/system/org",
  "/system/role",
  "/system/user",
  "/system/messages",
  "/system/ai-usage",
  "/system/ai-quota",
  "/system/audit",
];

router.beforeEach((to, _from, next) => {
  const bar = document.getElementById("route-loading-bar");
  if (bar) bar.style.display = "block";

  // Allow pipeline routes without authentication (useful for CI/CD dashboard preview)
  if (to.path.startsWith('/pipelines')) {
    const token = localStorage.getItem("token");
    if (!token) {
      next({ path: "/login", query: { redirect: to.fullPath } });
      return;
    }
    next();
    return;
  }

  const token = localStorage.getItem("token");
  const isPublic = to.meta.public === true;

  if (!isPublic && !token) {
    next({ path: "/login", query: { redirect: to.fullPath } });
    return;
  }
  if (to.path === "/login" && token) {
    next({ path: "/dashboard" });
    return;
  }
  if (
    token &&
    localStorage.getItem("is_system_admin") !== "1" &&
    SYSTEM_ADMIN_ONLY_PREFIXES.some((p) => to.path === p || to.path.startsWith(`${p}/`))
  ) {
    next({ path: "/system/message" });
    return;
  }
  next();
});

router.afterEach(() => {
  const el = document.getElementById("route-loading-bar");
  if (el) el.style.display = "none";
});

export default router;
