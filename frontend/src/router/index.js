import { createRouter, createWebHistory } from "vue-router";

import MainLayout from "@/layouts/MainLayout.vue";

const routes = [
  { path: "/", redirect: "/dashboard" },

  { path: "/login", name: "Login", component: () => import("@/views/Login.vue"), meta: { public: true } },
  { path: "/register", name: "Register", component: () => import("@/views/Register.vue"), meta: { public: true } },

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
      { path: "dashboard", component: () => import("@/views/Dashboard.vue") },
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
      },
      {
        path: "test-case/:type",
        name: "TestCase",
        component: () => import("@/views/TestCase.vue"),
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
        path: "performance/environments",
        name: "EnvironmentManagement",
        component: () => import("@/views/performance/EnvironmentManagement.vue"),
      },

      { path: "defect/list", component: () => import("@/views/defect/DefectList.vue") },
      { path: "defect/board", component: () => import("@/views/defect/TaskBoard.vue") },
      { path: "defect/release", component: () => import("@/views/defect/ReleasePlan.vue") },
      { path: "defect/detail", component: () => import("@/views/defect/DefectDetail.vue") },
      { path: "defect/detail/:id", component: () => import("@/views/defect/DefectDetail.vue") },
      { path: "defect/release/:id", component: () => import("@/views/defect/ReleasePlanDetail.vue") },

      { path: "ai-assistant", component: () => import("@/views/AiAssistant.vue") },
      {
        path: "server-logs",
        name: "ServerLogs",
        component: () => import("@/views/server_logs/index.vue"),
        meta: { keepAlive: true },
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
  { path: "/:pathMatch(.*)*", redirect: "/dashboard" },
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

export default router;
