<template>
  <div class="main-layout main-layout--cyber main-layout--theme">
    <div class="main-layout__glow main-layout__glow--a" aria-hidden="true" />
    <div class="main-layout__glow main-layout__glow--b" aria-hidden="true" />
    <div class="main-layout__grid" aria-hidden="true" />

    <!-- 顶部导航栏 -->
    <header class="top-nav">
      <div class="top-nav__left">
        <div class="brand-logo">
          <svg viewBox="0 0 36 36" class="brand-logo__icon" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="navLogoGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#00d8ff" />
                <stop offset="100%" stop-color="#1e5a8e" />
              </linearGradient>
            </defs>
            <rect x="2" y="6" width="6" height="24" rx="1.5" fill="url(#navLogoGrad)" />
            <rect x="12" y="14" width="6" height="16" rx="1.5" fill="url(#navLogoGrad)" opacity="0.85" />
            <rect x="22" y="10" width="6" height="20" rx="1.5" fill="url(#navLogoGrad)" opacity="0.7" />
          </svg>
          <span class="brand-logo__text">AITesta</span>
        </div>
        <nav class="top-nav__menu" aria-label="Top section navigation">
          <router-link
            class="top-nav__menu-item"
            :class="{ active: topNavActive === 'project' }"
            to="/projects"
          >
            项目管理
          </router-link>
          <router-link
            class="top-nav__menu-item"
            :class="{ active: topNavActive === 'knowledge' }"
            to="/knowledge"
          >
            知识中心
          </router-link>
          <router-link
            class="top-nav__menu-item"
            :class="{ active: topNavActive === 'help' }"
            to="/help"
          >
            帮助中心
          </router-link>
        </nav>
      </div>
      <div class="top-nav__center">
        <div class="nav-context-selectors" role="group" aria-label="项目与环境选择">
          <el-dropdown trigger="click" popper-class="dark-tech-dropdown nav-context-dropdown" @command="handleProjectCommand">
            <button class="nav-context-selector" type="button" aria-label="项目选择">
              <span class="nav-context-selector__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <rect x="3" y="5" width="18" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.5" />
                  <path d="M9 20h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                </svg>
              </span>
              <span class="nav-context-selector__label">Project:</span>
              <span class="nav-context-selector__value">{{ currentProjectLabel }}</span>
              <el-icon class="nav-context-selector__arrow"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="item in projectOptions"
                  :key="item.id"
                  :command="item.id"
                  :class="{ 'nav-context-dropdown__item--current': String(item.id) === String(selectedProject) }"
                >
                  {{ item.project_name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown trigger="click" popper-class="dark-tech-dropdown nav-context-dropdown" @command="handleEnvCommand">
            <button class="nav-context-selector" type="button" aria-label="环境选择">
              <span class="nav-context-selector__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <rect x="4" y="5" width="16" height="4" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4" />
                  <rect x="4" y="10" width="16" height="4" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4" />
                  <rect x="4" y="15" width="16" height="4" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.4" />
                </svg>
              </span>
              <span class="nav-context-selector__label">Env:</span>
              <span class="nav-context-selector__value">{{ currentEnvLabel }}</span>
              <el-icon class="nav-context-selector__arrow"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="item in envOptions"
                  :key="item.id"
                  :command="item.id"
                  :class="{ 'nav-context-dropdown__item--current': String(item.id) === String(selectedEnv) }"
                >
                  {{ item.name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <div class="top-nav__right">
        <el-input
          v-model="searchKw"
          placeholder="请输入搜索内容"
          class="top-search top-search--cyber"
          clearable
        >
          <template #prefix>
            <span class="top-search__holo" aria-hidden="true">
              <svg class="top-search__holo-svg" viewBox="0 0 24 24" width="20" height="20">
                <defs>
                  <linearGradient id="cyberNavHoloGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#00d8ff" />
                    <stop offset="100%" stop-color="#a78bfa" />
                  </linearGradient>
                </defs>
                <path
                  d="M10 3a7 7 0 105.292 11.908l3.68 3.68a1 1 0 001.415-1.414l-3.68-3.68A7 7 0 0010 3zm0 2a5 5 0 110 10 5 5 0 010-10z"
                  fill="none"
                  stroke="url(#cyberNavHoloGrad)"
                  stroke-width="1.35"
                />
                <circle cx="10" cy="10" r="2" fill="url(#cyberNavHoloGrad)" opacity="0.35" />
                <path
                  d="M4 18 L8 14 M6 20 L10 16"
                  stroke="url(#cyberNavHoloGrad)"
                  stroke-width="0.6"
                  opacity="0.6"
                />
              </svg>
              <span class="top-search__holo-beam" />
            </span>
          </template>
        </el-input>
        <el-badge
          :value="unreadMessageCount > 0 ? unreadMessageCount : ''"
          class="notice-badge notice-badge--cyber"
        >
          <div
            class="notice-bell-cyber"
            role="button"
            tabindex="0"
            title="消息"
            @click="goMessageCenter"
            @keydown.enter.prevent="goMessageCenter"
          >
            <span class="notice-bell-cyber__ring notice-bell-cyber__ring--1" />
            <span class="notice-bell-cyber__ring notice-bell-cyber__ring--2" />
            <span class="notice-bell-cyber__ring notice-bell-cyber__ring--3" />
            <svg class="notice-bell-cyber__svg" viewBox="0 0 24 24" width="22" height="22">
              <defs>
                <linearGradient id="cyberNavBellGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#7c3aed" />
                  <stop offset="50%" stop-color="#c084fc" />
                  <stop offset="100%" stop-color="#e9d5ff" />
                </linearGradient>
              </defs>
              <path
                d="M12 3c-1.76 2.1-2 3.5-2 5a5 5 0 0010 0c0-1.5-.24-2.9-2-5z"
                fill="url(#cyberNavBellGrad)"
                opacity="0.88"
              />
              <path
                d="M7 18h10l-1.2-2.4a6 6 0 00-7.6 0L7 18z"
                fill="url(#cyberNavBellGrad)"
                opacity="0.72"
              />
              <path
                d="M9 18h6v1a3 3 0 01-6 0v-1z"
                fill="#4c1d95"
                opacity="0.6"
              />
              <path
                d="M12 3v2 M10 8h4"
                stroke="#e9d5ff"
                stroke-width="0.8"
                opacity="0.5"
              />
            </svg>
          </div>
        </el-badge>
        <el-icon class="nav-icon-btn" @click="router.go(0)"><Refresh /></el-icon>
        <el-dropdown @command="handleUserCmd">
          <div class="user-info user-info--cyber">
            <div class="user-avatar-shell">
              <span class="user-avatar-shell__orbit user-avatar-shell__orbit--a" aria-hidden="true" />
              <span class="user-avatar-shell__orbit user-avatar-shell__orbit--b" aria-hidden="true" />
              <el-avatar :size="40" :src="avatarSrc" class="user-avatar user-avatar--cyber">
                {{ userInitial }}
              </el-avatar>
              <div class="user-hud" aria-hidden="true">
                <span class="user-hud__line">USER ID: {{ userHudId }}</span>
                <span class="user-hud__line">LEVEL: [{{ userLevelTag }}]</span>
              </div>
            </div>
            <span class="user-name user-name--cyber">{{ username }}</span>
            <el-icon class="user-arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <div
          class="settings-cyber nav-icon-btn"
          role="button"
          tabindex="0"
          title="设置"
          @click="goUserCenter"
          @keydown.enter.prevent="goUserCenter"
        >
          <svg class="settings-cyber__svg" viewBox="0 0 24 24" width="22" height="22">
            <defs>
              <linearGradient id="cyberNavSettingsGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#00d8ff" />
                <stop offset="100%" stop-color="#a855f7" />
              </linearGradient>
            </defs>
            <g>
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="0 12 12"
                to="360 12 12"
                dur="18s"
                repeatCount="indefinite"
              />
              <circle
                cx="12"
                cy="12"
                r="8.2"
                fill="none"
                stroke="url(#cyberNavSettingsGrad)"
                stroke-width="0.55"
                opacity="0.35"
              />
              <circle
                cx="12"
                cy="12"
                r="5.8"
                fill="none"
                stroke="url(#cyberNavSettingsGrad)"
                stroke-width="0.85"
                stroke-dasharray="2.4 2"
                opacity="0.55"
              />
            </g>
            <g>
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="360 12 12"
                to="0 12 12"
                dur="9s"
                repeatCount="indefinite"
              />
              <path
                d="M12 2.2v2.1l1.6.5a6.8 6.8 0 012.5 1.7l1.5-.8 1.6 2.8-1.3 1c.2.6.3 1.2.3 1.8s-.1 1.2-.3 1.8l1.3 1-1.6 2.8-1.5-.8a6.8 6.8 0 01-2.5 1.7l-1.6.5v2.1h-1v-2.1l-1.6-.5a6.8 6.8 0 01-2.5-1.7l-1.5.8-1.6-2.8 1.3-1a6.3 6.3 0 010-3.6l-1.3-1 1.6-2.8 1.5.8a6.8 6.8 0 012.5-1.7l1.6-.5V2.2h1z"
                fill="none"
                stroke="url(#cyberNavSettingsGrad)"
                stroke-width="1.05"
                stroke-linejoin="round"
              />
            </g>
            <circle cx="12" cy="12" r="2.2" fill="#0a1528" stroke="url(#cyberNavSettingsGrad)" stroke-width="0.95" />
          </svg>
        </div>
      </div>
    </header>

    <div class="layout-body">
      <!-- 左侧菜单 -->
      <aside class="side-nav side-nav--tech">
        <el-menu
          ref="sideMenuRef"
          :default-active="activeMenu"
          class="side-menu side-menu--tech"
          :collapse="false"
          @select="onSideMenuSelect"
        >
          <el-menu-item index="/dashboard">
            <el-icon><HomeFilled /></el-icon>
            <span>工作台</span>
          </el-menu-item>
          <el-menu-item index="/test-approach">
            <el-icon><Document /></el-icon>
            <span>测试方案</span>
          </el-menu-item>
          <el-menu-item index="/test-design">
            <el-icon><EditPen /></el-icon>
            <span>测试设计</span>
          </el-menu-item>
          <el-menu-item index="/test-plan">
            <el-icon><Calendar /></el-icon>
            <span>测试计划</span>
          </el-menu-item>
          <el-sub-menu index="test-case">
            <template #title>
              <el-icon><List /></el-icon>
              <span>测试用例</span>
            </template>
            <el-menu-item index="/test-case/functional">功能测试</el-menu-item>
            <el-menu-item index="/test-case/api">接口测试</el-menu-item>
            <el-menu-item index="/execution/api-scenario-generator">接口场景生成</el-menu-item>
            <el-menu-item index="/test-case/performance">性能测试</el-menu-item>
            <el-menu-item index="/test-case/security">安全测试</el-menu-item>
            <el-menu-item index="/test-case/ui-automation">UI 自动化</el-menu-item>
          </el-sub-menu>
          <el-menu-item index="/test-report">
            <el-icon><DataLine /></el-icon>
            <span>测试报告</span>
          </el-menu-item>
          <el-menu-item index="/quality-dashboard">
            <el-icon><DataLine /></el-icon>
            <span>质量分析</span>
          </el-menu-item>
          <el-menu-item index="/performance/environments">
            <el-icon><Tools /></el-icon>
            <span>环境管理</span>
          </el-menu-item>
          <el-menu-item index="/performance/load-monitor">
            <el-icon><DataLine /></el-icon>
            <span>k6 压测看板</span>
          </el-menu-item>
          <el-menu-item index="/server-logs">
            <el-icon><Monitor /></el-icon>
            <span>服务器日志</span>
          </el-menu-item>
          <el-sub-menu index="defect">
            <template #title>
              <el-icon><Warning /></el-icon>
              <span>缺陷管理</span>
            </template>
            <el-menu-item index="/defect/list">缺陷清单</el-menu-item>
            <el-menu-item index="/defect/board">任务看板</el-menu-item>
            <el-menu-item index="/defect/release">发布计划</el-menu-item>
          </el-sub-menu>
          <el-sub-menu v-if="isSystemAdmin" index="system">
            <template #title>
              <el-icon><Tools /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/system/message">消息设置</el-menu-item>
            <el-menu-item index="/system/messages">消息管理</el-menu-item>
            <el-menu-item index="/system/ai-usage">AI 用量与审计</el-menu-item>
            <el-menu-item index="/system/ai-quota">AI 配额策略</el-menu-item>
            <el-menu-item index="/system/audit">
              <el-icon><Tickets /></el-icon>
              <span>审计中心</span>
            </el-menu-item>
            <el-menu-item index="/system/org">组织管理</el-menu-item>
            <el-menu-item index="/system/role">角色管理</el-menu-item>
            <el-menu-item index="/system/user">用户管理</el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else index="/system/message">
            <el-icon><Tools /></el-icon>
            <span>消息设置</span>
          </el-menu-item>
          <el-menu-item v-if="!isSystemAdmin" index="/user/audit">
            <el-icon><Tickets /></el-icon>
            <span>我的审计</span>
          </el-menu-item>
          <el-menu-item index="/ai-assistant">
            <el-icon><MagicStick /></el-icon>
            <span>智能助手</span>
          </el-menu-item>
        </el-menu>
      </aside>

      <!-- 主内容区 -->
      <main class="main-content">
        <el-alert
          v-if="backendHealthMessage"
          :title="backendHealthMessage"
          type="error"
          show-icon
          class="backend-health-alert"
          @close="backendHealthMessage = ''"
        />
        <div class="content-header">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="item in breadcrumb" :key="item">{{ item }}</el-breadcrumb-item>
          </el-breadcrumb>
          <div class="content-header__actions">
            <el-button link size="small" @click="router.go(0)">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
            <el-button v-if="canGoBack" link size="small" @click="router.back()">
              <el-icon><Back /></el-icon> 返回
            </el-button>
          </div>
        </div>
        <div class="content-body">
          <!-- key：切换 /test-case/:type 等路径时强制重建页面实例，避免局部状态残留 -->
          <router-view v-slot="{ Component, route: r }">
            <keep-alive>
              <component
                v-if="r?.meta?.keepAlive"
                :is="Component"
                :key="String(r.name || r.path)"
              />
            </keep-alive>
            <component
              v-if="!r?.meta?.keepAlive"
              :is="Component"
              :key="r.path"
            />
          </router-view>
        </div>
      </main>
    </div>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="520px" destroy-on-close>
      <el-form :model="passwordForm" label-width="110px">
        <el-form-item label="旧密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSaving" @click="submitPassword">
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh, ArrowDown,
  HomeFilled, Document, EditPen, Calendar, List,
  DataLine, Warning, Tools, MagicStick, Back, Monitor, Tickets
} from '@element-plus/icons-vue'
import { TEST_CASE_TYPE_LABEL_ZH } from '@/constants/testCaseTypeLabels'
import { changePasswordApi, getCurrentUserApi, getUserProfileApi, getSystemMessagesApi } from '@/api/user'
import { getProjectsApi } from '@/api/project'
import { getEnvironments } from '@/api/environment'
import { useAppContextStore } from '@/stores/appContextStore'

const router = useRouter()
const route = useRoute()
const appContextStore = useAppContextStore()

/** 不用 el-menu 的 router 模式：其内部依赖 globalProperties.$router，在部分环境下会取不到导致点击无跳转 */
function onSideMenuSelect(index) {
  if (typeof index === 'string' && index.startsWith('/')) {
    router.push(index).catch(() => {})
  }
}

const searchKw = ref('')
const backendHealthMessage = ref('')
const unreadMessageCount = ref(0)
const selectedProject = ref(null)
const selectedEnv = ref(null)
const projectOptions = ref([])
const envOptions = ref([])

function normalizeList(payload) {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  if (Array.isArray(payload?.data)) return payload.data
  return []
}

function syncProjectContextById(projectId) {
  const p = projectOptions.value.find(item => String(item.id) === String(projectId))
  if (!p) {
    appContextStore.setActiveProject({ id: null, name: '' })
    return
  }
  appContextStore.setActiveProject({ id: p.id, name: p.project_name || '' })
}

function syncEnvironmentContextById(environmentId) {
  const e = envOptions.value.find(item => String(item.id) === String(environmentId))
  if (!e) {
    appContextStore.setActiveEnvironment({ id: null, name: '' })
    return
  }
  appContextStore.setActiveEnvironment({ id: e.id, name: e.name || '' })
}

const currentProjectLabel = computed(() => {
  const p = projectOptions.value.find(item => String(item.id) === String(selectedProject.value))
  return p ? `${p.project_name} (Current)` : 'No Project'
})

const currentEnvLabel = computed(() => {
  const e = envOptions.value.find(item => String(item.id) === String(selectedEnv.value))
  return e ? `${e.name} (Current)` : 'No Env'
})

const username = computed(() => localStorage.getItem('username') || 'Admin')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())

/** 顶栏 HUD：用户信息展示（虚构格式，与账号 id / 权限粗略对应） */
const userHudId = computed(() => {
  const id = localStorage.getItem('user_id')
  if (id != null && String(id).trim() !== '') {
    const n = String(id).replace(/\D/g, '') || '0'
    return `USR_${n.padStart(3, '0').slice(-6)}`
  }
  const seed = (username.value || 'U').slice(0, 3).toUpperCase().replace(/\s/g, 'X')
  return `${seed}_001`
})

/** 来自 GET /user/me/profile/ 的 avatar_url（el-avatar 加载失败时自动退回插槽内首字母） */
const userAvatarUrl = ref(null)

const avatarSrc = computed(() => {
  const u = userAvatarUrl.value
  return u && String(u).trim() ? String(u).trim() : undefined
})

const isSystemAdmin = ref(localStorage.getItem('is_system_admin') === '1')

const userLevelTag = computed(() => (isSystemAdmin.value ? 'SYSADMIN' : 'OPERATOR'))

function syncSystemAdminFlag() {
  isSystemAdmin.value = localStorage.getItem('is_system_admin') === '1'
}

async function syncProfileFromServer() {
  if (!localStorage.getItem('token')) return
  try {
    const { data } = await getCurrentUserApi()
    if (data?.code !== 200 || !data?.data) return
    const d = data.data
    if (d.user_id != null) localStorage.setItem('user_id', String(d.user_id))
    if (d.real_name) localStorage.setItem('real_name', String(d.real_name))
    localStorage.setItem('username', d.real_name || d.username || 'User')
    localStorage.setItem('is_system_admin', d.is_system_admin ? '1' : '0')
    syncSystemAdminFlag()
    window.dispatchEvent(new Event('app:permissions'))
  } catch {
    /* 忽略 */
  }
  try {
    const { data: prof } = await getUserProfileApi()
    if (prof?.code === 200 && prof?.data) {
      const url = prof.data.avatar_url
      userAvatarUrl.value = url != null && String(url).trim() ? String(url).trim() : null
    }
  } catch {
    /* 忽略 */
  }
}

function onUserProfileUpdated(ev) {
  const url = ev?.detail?.avatar_url
  if (url === undefined) return
  userAvatarUrl.value = url != null && String(url).trim() ? String(url).trim() : null
}


async function syncUnreadMessageCount() {
  try {
    const { data: res } = await getSystemMessagesApi()
    const list = res?.data
    const rows = Array.isArray(list) ? list : []
    unreadMessageCount.value = rows.filter((m) => !m?.is_read).length
  } catch {
    unreadMessageCount.value = 0
  }
}

watch(
  () => route.fullPath,
  (fullPath) => {
    syncSystemAdminFlag()
    if (fullPath.startsWith('/system/messages')) syncUnreadMessageCount()
  },
)

const sideMenuRef = ref(null)

const activeMenu = computed(() => route.path)

/** 直达子路由时展开「测试用例」分组（Element Plus 仅在挂载时对 defaultOpeneds/initMenu 生效） */
watch(
  () => route.path,
  (path) => {
    if (path.startsWith('/test-case')) {
      nextTick(() => {
        sideMenuRef.value?.open?.('test-case')
      })
    }
  },
  { immediate: true },
)

/** 顶栏「项目管理 / 知识中心 / 帮助中心」与当前路由对齐 */
const topNavActive = computed(() => {
  const p = route.path || ''
  if (p === '/projects' || p.startsWith('/projects/')) return 'project'
  if (p === '/knowledge' || p.startsWith('/knowledge/')) return 'knowledge'
  if (p === '/help' || p.startsWith('/help/')) return 'help'
  return ''
})

const BREADCRUMB_MAP = {
  '/dashboard': ['工作台', ''],
  '/user/center': ['个人中心', ''],
  '/projects': ['项目管理', ''],
  '/test-approach': ['测试方案', ''],
  '/test-design': ['测试设计', '引导页'],
  '/test-plan': ['测试计划', '引导页'],
  '/test-case/functional': ['测试用例', '功能测试'],
  '/test-case/api': ['测试用例', '接口测试'],
  '/execution/api-scenario-generator': ['测试用例', '接口场景生成'],
  '/test-case/performance': ['测试用例', '性能测试'],
  '/test-case/security': ['测试用例', '安全测试'],
  '/test-case/ui-automation': ['测试用例', 'UI 自动化'],
  '/test-report': ['测试报告', '引导页'],
  '/quality-dashboard': ['质量分析', '质量看板'],
  '/performance/environments': ['Workspace', 'Performance', 'Environments'],
  '/performance/load-monitor': ['性能压测', 'k6 实时监控'],
  '/defect/list': ['缺陷清单', '引导页'],
  '/defect/board': ['缺陷管理', '任务看板'],
  '/defect/release': ['缺陷管理', '发布计划'],
  '/ai-assistant': ['智能助手', ''],
  '/server-logs': ['智能运维', '服务器日志'],
  '/system/message': ['系统管理', '消息设置'],
  '/system/messages': ['系统管理', '消息管理'],
  '/system/ai-usage': ['系统管理', 'AI 用量与审计'],
  '/system/ai-quota': ['系统管理', 'AI 配额策略'],
  '/system/audit': ['系统管理', '审计中心'],
  '/system/org': ['系统管理', '组织管理'],
  '/system/role': ['系统管理', '角色管理'],
  '/system/user': ['系统管理', '用户管理'],
  '/user/audit': ['合规与审计', '我的审计'],
  '/knowledge': ['知识中心', ''],
  '/knowledge/ask': ['知识中心', '知识库问答'],
  '/help': ['帮助中心', ''],
}

const breadcrumb = computed(() => {
  const path = route.path
  if (BREADCRUMB_MAP[path]) return BREADCRUMB_MAP[path].filter(Boolean)
  if (path.startsWith('/test-case/')) {
    const sub = BREADCRUMB_MAP[path]
    if (sub) return sub.filter(Boolean)
    const t = String(route.params.type || '')
    return ['测试用例', TEST_CASE_TYPE_LABEL_ZH[t] || t || ''].filter(Boolean)
  }
  if (path.startsWith('/test-design/')) return ['测试设计', '编辑']
  if (path.startsWith('/test-plan/')) return ['测试计划', '测试计划详情']
  if (path.startsWith('/test-report/')) return ['测试报告', '测试报告详情']
  if (path.startsWith('/defect/detail')) return ['缺陷清单', '详情页']
  if (path.startsWith('/defect/release/')) return ['缺陷管理', '发布计划详情']
  return [path].filter(Boolean)
})

const canGoBack = computed(() => {
  const detailRoutes = ['/test-design/', '/test-plan/', '/test-report/', '/defect/detail', '/defect/release/']
  return detailRoutes.some(p => route.path.startsWith(p))
})

function handleUserCmd(cmd) {
  if (cmd === 'logout') {
    ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' }).then(() => {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('is_system_admin')
      localStorage.removeItem('user_id')
      localStorage.removeItem('real_name')
      userAvatarUrl.value = null
      router.push('/login')
    })
    return
  }
  if (cmd === 'profile') {
    router.push('/user/center')
    return
  }
  if (cmd === 'password') {
    passwordDialogVisible.value = true
  }
}

const passwordDialogVisible = ref(false)
const passwordSaving = ref(false)
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function goMessageCenter() {
  router.push('/system/messages')
}

function goUserCenter() {
  router.push('/user/center')
}

function handleProjectCommand(value) {
  selectedProject.value = String(value)
  syncProjectContextById(selectedProject.value)
}

function handleEnvCommand(value) {
  selectedEnv.value = String(value)
  syncEnvironmentContextById(selectedEnv.value)
}

async function loadProjectOptions() {
  try {
    const { data } = await getProjectsApi()
    const list = normalizeList(data)
    projectOptions.value = list
    const stored = localStorage.getItem('current_project_id')
    const matched = list.find(item => String(item.id) === String(stored))
    selectedProject.value = matched ? String(matched.id) : (list[0] ? String(list[0].id) : null)
    if (selectedProject.value != null) {
      syncProjectContextById(selectedProject.value)
    } else {
      appContextStore.setActiveProject({ id: null, name: '' })
    }
  } catch {
    projectOptions.value = []
    selectedProject.value = null
  }
}

async function loadEnvironmentOptions() {
  try {
    const { data } = await getEnvironments({ page_size: 500 })
    const list = normalizeList(data)
    envOptions.value = list
    const stored = localStorage.getItem('current_test_environment_id')
    const matched = list.find(item => String(item.id) === String(stored))
    selectedEnv.value = matched ? String(matched.id) : (list[0] ? String(list[0].id) : null)
    if (selectedEnv.value != null) {
      syncEnvironmentContextById(selectedEnv.value)
    } else {
      appContextStore.setActiveEnvironment({ id: null, name: '' })
    }
  } catch {
    envOptions.value = []
    selectedEnv.value = null
  }
}

function onProjectsUpdated() {
  loadProjectOptions()
}

function onEnvironmentsUpdated() {
  loadEnvironmentOptions()
}

function onBackendUnhealthy(ev) {
  backendHealthMessage.value = ev?.detail?.message || '后端服务异常，请稍后重试'
}

function onBackendHealthy() {
  backendHealthMessage.value = ''
}

async function submitPassword() {
  passwordSaving.value = true
  try {
    const payload = {
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
      confirm_password: passwordForm.value.confirm_password,
    }
    await changePasswordApi(payload)
    ElMessage.success('密码修改成功，请重新登录')
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('is_system_admin')
    localStorage.removeItem('user_id')
    localStorage.removeItem('real_name')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '修改失败')
  } finally {
    passwordSaving.value = false
    passwordDialogVisible.value = false
  }
}

onMounted(async () => {
  syncSystemAdminFlag()
  window.addEventListener('app:permissions', syncSystemAdminFlag)
  window.addEventListener('app:user-profile-updated', onUserProfileUpdated)
  window.addEventListener('app:projects-updated', onProjectsUpdated)
  window.addEventListener('app:environments-updated', onEnvironmentsUpdated)
  window.addEventListener('app:backend-unhealthy', onBackendUnhealthy)
  window.addEventListener('app:backend-healthy', onBackendHealthy)
  await Promise.all([loadProjectOptions(), loadEnvironmentOptions()])
  await syncProfileFromServer()
  await syncUnreadMessageCount()
})

onUnmounted(() => {
  window.removeEventListener('app:permissions', syncSystemAdminFlag)
  window.removeEventListener('app:user-profile-updated', onUserProfileUpdated)
  window.removeEventListener('app:projects-updated', onProjectsUpdated)
  window.removeEventListener('app:environments-updated', onEnvironmentsUpdated)
  window.removeEventListener('app:backend-unhealthy', onBackendUnhealthy)
  window.removeEventListener('app:backend-healthy', onBackendHealthy)
})
</script>

<style scoped>
/* ========== 布局主题变量（深色科技 / 霓虹青品牌） ========== */
.main-layout--theme {
  /* 全局导航基底：略深于模块树抽屉与工作区，形成分层 */
  --layout-bg-from: #0a0f1e;
  --layout-bg-to: #141c2f;
  --layout-text: #e8eaef;
  --layout-text-muted: #9ca3b8;
  --layout-text-subtle: #6b7280;
  --layout-brand-primary: #00d8ff;
  --layout-brand-primary-dim: color-mix(in srgb, var(--layout-brand-primary) 55%, #141c2f);
  --layout-brand-glow: color-mix(in srgb, var(--layout-brand-primary) 35%, transparent);
  --layout-brand-border: color-mix(in srgb, var(--layout-brand-primary) 28%, transparent);
  --layout-brand-surface: color-mix(in srgb, var(--layout-brand-primary) 10%, transparent);
}

.main-layout {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(168deg, var(--layout-bg-from) 0%, var(--layout-bg-to) 52%, #101827 100%);
}

.main-layout--cyber {
  color: var(--layout-text);
}

.main-layout__glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  pointer-events: none;
  z-index: 0;
  opacity: 0.2;
}

.main-layout__glow--a {
  width: min(60vw, 520px);
  height: min(60vw, 520px);
  top: -12%;
  left: -8%;
  background: radial-gradient(circle, var(--layout-brand-glow) 0%, transparent 68%);
}

.main-layout__glow--b {
  width: min(50vw, 420px);
  height: min(50vw, 420px);
  bottom: -5%;
  right: -5%;
  background: radial-gradient(circle, rgba(30, 90, 142, 0.4) 0%, transparent 70%);
}

.main-layout__grid {
  position: absolute;
  inset: 0;
  z-index: 0;
  opacity: 0.06;
  background-image:
    linear-gradient(var(--layout-brand-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--layout-brand-border) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
}

/* ===== 顶部导航（深色玻璃 / Tech-Noir） ===== */
.top-nav {
  position: relative;
  z-index: 2;
  height: 72px;
  min-height: 72px;
  overflow: visible;
  background: rgba(10, 15, 30, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--layout-brand-border);
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.4),
    0 0 40px var(--layout-brand-surface),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 28px;
  flex-shrink: 0;
}

.top-nav__left {
  display: flex;
  align-items: center;
  gap: 28px;
  flex-shrink: 1;
  min-width: 0;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 6px;
}

.brand-logo__icon {
  width: 32px;
  height: 32px;
}

.brand-logo__text {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.06em;
  background: linear-gradient(
    105deg,
    var(--layout-brand-primary) 0%,
    var(--layout-brand-primary-dim) 45%,
    #7dd3fc 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  white-space: nowrap;
  filter: drop-shadow(0 0 10px var(--layout-brand-glow));
}

.top-nav__menu {
  display: flex;
  align-items: stretch;
  gap: 22px;
}

.top-nav__menu-item {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 6px 14px;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.02em;
  /* 默认：低调偏冷灰、略透明，背景全透明融入顶栏玻璃 */
  color: color-mix(in srgb, var(--layout-text-muted) 78%, var(--layout-brand-primary) 6%);
  opacity: 0.88;
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: 0;
  text-decoration: none;
  white-space: nowrap;
  transition:
    color 0.3s ease,
    opacity 0.3s ease,
    font-weight 0.3s ease,
    text-shadow 0.3s ease,
    background-color 0.3s ease;
}

.top-nav__menu-item::after {
  content: '';
  position: absolute;
  left: 8%;
  right: 8%;
  bottom: 4px;
  height: 2px;
  border-radius: 2px;
  pointer-events: none;
  background: linear-gradient(
    90deg,
    transparent,
    var(--layout-brand-primary) 20%,
    var(--layout-brand-primary) 80%,
    transparent
  );
  opacity: 0;
  transform: scaleX(0.35);
  transform-origin: center;
  box-shadow: 0 0 14px color-mix(in srgb, var(--layout-brand-primary) 55%, transparent);
  transition:
    opacity 0.3s ease,
    transform 0.3s ease,
    box-shadow 0.3s ease;
}

.top-nav__menu-item:hover {
  opacity: 1;
  color: var(--layout-brand-primary);
  text-shadow:
    0 0 10px color-mix(in srgb, var(--layout-brand-primary) 45%, transparent),
    0 0 22px color-mix(in srgb, var(--layout-brand-primary) 22%, transparent);
  background-color: color-mix(in srgb, var(--layout-brand-primary) 7%, transparent);
}

.top-nav__menu-item:hover::after {
  opacity: 0.55;
  transform: scaleX(0.92);
}

.top-nav__menu-item.active {
  opacity: 1;
  color: var(--layout-brand-primary);
  font-weight: 700;
  text-shadow:
    0 0 12px color-mix(in srgb, var(--layout-brand-primary) 50%, transparent),
    0 0 26px color-mix(in srgb, var(--layout-brand-primary) 28%, transparent);
  background-color: transparent;
}

.top-nav__menu-item.active::after {
  opacity: 1;
  transform: scaleX(1);
  box-shadow:
    0 0 18px color-mix(in srgb, var(--layout-brand-primary) 65%, transparent),
    0 0 36px color-mix(in srgb, var(--layout-brand-primary) 25%, transparent);
}

.top-nav__center {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-width: 320px;
}

.nav-context-selectors {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: min(760px, 52vw);
  width: 100%;
}

.nav-context-selectors :deep(.el-dropdown) {
  flex: 1 1 0;
  min-width: 0;
}

.nav-context-selector {
  width: 100%;
  min-width: 0;
  height: 38px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid color-mix(in srgb, var(--layout-brand-primary) 30%, rgba(167, 139, 250, 0.32));
  border-radius: 12px;
  background: linear-gradient(
    152deg,
    color-mix(in srgb, #0b1224 92%, transparent),
    color-mix(in srgb, #161f38 78%, transparent)
  );
  color: #d2d8e3;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.045) inset,
    0 0 20px color-mix(in srgb, var(--layout-brand-primary) 11%, transparent),
    inset 0 1px 0 rgba(167, 139, 250, 0.07);
  cursor: pointer;
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

.nav-context-selector:hover {
  border-color: color-mix(in srgb, var(--layout-brand-primary) 46%, rgba(192, 132, 252, 0.4));
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--layout-brand-primary) 16%, transparent) inset,
    0 0 28px color-mix(in srgb, var(--layout-brand-primary) 18%, transparent);
}

.nav-context-selector__icon {
  display: inline-flex;
  color: color-mix(in srgb, var(--layout-brand-primary) 76%, #dbeafe);
  flex-shrink: 0;
}

.nav-context-selector__label {
  font-size: 13px;
  color: #d7dbe3;
  flex-shrink: 0;
}

.nav-context-selector__value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #22d3ee;
  text-shadow: 0 0 10px color-mix(in srgb, var(--layout-brand-primary) 55%, transparent);
}

.nav-context-selector__arrow {
  margin-left: auto;
  color: #9fb4cf;
  font-size: 12px;
  flex-shrink: 0;
}

/* ========== 顶栏赛博控件：下拉 / 搜索 / 铃铛 / 用户 / 设置 ========== */
@keyframes cyberNavGearRotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@keyframes cyberNavStreamScroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

@keyframes cyberNavFiber {
  0% {
    background-position: 0% 50%;
  }
  100% {
    background-position: 200% 50%;
  }
}

@keyframes cyberNavScanPulse {
  0%,
  100% {
    opacity: 0.32;
  }
  50% {
    opacity: 0.62;
  }
}

@keyframes cyberNavHoloBeam {
  0%,
  100% {
    opacity: 0.2;
    transform: scaleX(0.65);
  }
  50% {
    opacity: 0.95;
    transform: scaleX(1);
  }
}

@keyframes cyberNavBellPulse {
  0%,
  100% {
    filter: drop-shadow(0 0 3px rgba(124, 58, 237, 0.45));
  }
  50% {
    filter: drop-shadow(0 0 12px rgba(192, 132, 252, 0.75));
  }
}

@keyframes cyberNavRingExpand {
  0% {
    transform: scale(0.62);
    opacity: 0.5;
  }
  100% {
    transform: scale(1.45);
    opacity: 0;
  }
}

/* ========== 顶栏：项目 + 环境 统一上下文切换条 ========== */
.context-switcher {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  min-width: 0;
  width: min(520px, 44vw);
  max-width: 520px;
}

.tech-select-wrapper {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 0;
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
  gap: 16px;
  /* Header Select 暗色主题变量（可复用） */
  --header-select-bg-from: color-mix(in srgb, #161b22 94%, transparent);
  --header-select-bg-to: color-mix(in srgb, #1b2230 88%, transparent);
  --header-select-text: #c9d1d9;
  --header-select-placeholder: #8b949e;
  --header-select-border: color-mix(in srgb, #30363d 80%, #4b5563 20%);
  --header-select-border-hover: color-mix(in srgb, var(--layout-brand-primary) 38%, #30363d);
  --header-select-border-focus: color-mix(in srgb, var(--layout-brand-primary) 66%, #a78bfa 18%);
  --header-select-focus-glow: color-mix(in srgb, var(--layout-brand-primary) 26%, transparent);
}

.tech-select-wrapper :deep(.el-input__wrapper) {
  min-height: 38px;
  padding: 4px 12px;
  border-radius: 14px;
  background: linear-gradient(152deg, var(--header-select-bg-from), var(--header-select-bg-to)) !important;
  box-shadow: 0 0 0 1px var(--header-select-border) inset !important;
  border: none !important;
  transition:
    background-color 0.2s ease,
    box-shadow 0.2s ease !important;
}

.tech-select-wrapper :deep(.el-input__wrapper:hover) {
  box-shadow:
    0 0 0 1px var(--header-select-border-hover) inset,
    0 0 20px color-mix(in srgb, var(--layout-brand-primary) 14%, transparent) !important;
}

.tech-select-wrapper :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 1px var(--header-select-border-focus) inset,
    0 0 0 2px color-mix(in srgb, var(--header-select-focus-glow) 45%, transparent),
    0 0 18px var(--header-select-focus-glow) !important;
}

.tech-select-wrapper :deep(.el-input__inner) {
  color: var(--header-select-text) !important;
  -webkit-text-fill-color: var(--header-select-text) !important;
}

.tech-select-wrapper :deep(.el-select__input-wrapper),
.tech-select-wrapper :deep(.el-select__input) {
  color: var(--header-select-text) !important;
  -webkit-text-fill-color: var(--header-select-text) !important;
}

.tech-select-wrapper :deep(.el-select__selected-item) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  font-weight: 500;
  font-size: 13px;
  color: var(--header-select-text) !important;
  -webkit-text-fill-color: var(--header-select-text) !important;
  opacity: 1 !important;
}

.tech-select-wrapper :deep(.el-select__placeholder),
.tech-select-wrapper :deep(.el-select__placeholder span) {
  color: var(--header-select-placeholder) !important;
  -webkit-text-fill-color: var(--header-select-placeholder) !important;
  opacity: 1 !important;
}

.tech-select-wrapper :deep(.el-select__selected-item.is-transparent),
.tech-select-wrapper :deep(.el-select__placeholder.is-transparent) {
  color: var(--header-select-placeholder) !important;
  -webkit-text-fill-color: var(--header-select-placeholder) !important;
  opacity: 1 !important;
}

.tech-select-wrapper :deep(.el-select__selection),
.tech-select-wrapper :deep(.el-select__selected-item),
.tech-select-wrapper :deep(.el-select__placeholder),
.tech-select-wrapper :deep(.el-select__input-wrapper) {
  filter: none !important;
  mix-blend-mode: normal !important;
}

.tech-select-wrapper :deep(.el-select__caret) {
  width: 12px !important;
  opacity: 1 !important;
  color: var(--header-select-text) !important;
}

.tech-select-wrapper :deep(.el-input__suffix-inner),
.tech-select-wrapper :deep(.el-input__suffix) {
  color: var(--header-select-text) !important;
}


.tech-select-wrapper :deep(.el-select__selection) {
  overflow: hidden;
}

.context-switcher__pill {
  display: flex;
  flex-direction: row;
  align-items: center;
  width: 100%;
  min-height: 44px;
  padding: 0;
  border-radius: 12px;
  background: transparent;
  border: none;
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  transition: none;
}

.context-switcher__pill--dual {
  gap: 16px;
}

.context-switcher__selectors {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 16px;
  width: 100%;
  min-width: 0;
}

.context-switcher__pill:hover {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
}

.context-switcher__segment {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0;
  min-width: 0;
  flex: 1 1 0;
  padding: 0;
}

.context-switcher__segment-shell {
  flex: 1 1 0;
  min-width: 0;
  width: auto;
}

.context-switcher__segment-shell,
.tech-select-wrapper :deep(.current-env-select--navbar) {
  position: relative;
  min-height: 38px;
  border-radius: 14px;
  background: linear-gradient(152deg, var(--header-select-bg-from), var(--header-select-bg-to));
  border: 1px solid var(--header-select-border);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.045) inset,
    0 0 14px color-mix(in srgb, #0ea5e9 8%, transparent),
    inset 0 1px 0 rgba(148, 163, 184, 0.05);
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.22s ease;
  overflow: hidden;
}

.context-switcher__segment-shell:hover,
.tech-select-wrapper :deep(.current-env-select--navbar:hover) {
  border-color: var(--header-select-border-hover);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--layout-brand-primary) 15%, transparent) inset,
    0 0 28px color-mix(in srgb, var(--layout-brand-primary) 16%, transparent);
}

.context-switcher__segment-shell:focus-within {
  border-color: var(--header-select-border-focus);
  box-shadow:
    0 0 0 1px var(--header-select-border-focus) inset,
    0 0 0 2px color-mix(in srgb, var(--header-select-focus-glow) 42%, transparent),
    0 0 22px var(--header-select-focus-glow);
}

.context-switcher__segment-shell::after,
.tech-select-wrapper :deep(.current-env-select--navbar)::after {
  display: none;
}

.context-switcher__segment--project {
  cursor: default;
}

.context-switcher__mini-label {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.88);
  line-height: 1;
  user-select: none;
}

.context-switcher__status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow:
    0 0 0 1px rgba(34, 211, 238, 0.22),
    0 0 10px rgba(34, 211, 238, 0.72);
  flex-shrink: 0;
}

.context-switcher__active-tag {
  max-width: min(220px, 24vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.2;
  color: #dbeafe;
  background: color-mix(in srgb, var(--layout-brand-primary) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--layout-brand-primary) 24%, transparent);
  box-shadow: 0 0 12px color-mix(in srgb, var(--layout-brand-primary) 18%, transparent);
}

.context-switcher__field {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1 1 auto;
}

.context-switcher__divider {
  display: none;
}

.context-switcher__select {
  width: 100%;
  min-width: 0;
}

.context-switcher__gear {
  display: none;
}

.context-switcher__gear--lead {
  margin-right: -2px;
}

.context-switcher__gear-rot {
  transform-box: fill-box;
  transform-origin: center;
  animation: cyberNavGearRotate 14s linear infinite;
}

.context-switcher__streams {
  display: none;
}

.context-switcher__streams-inner {
  display: inline-flex;
  flex-wrap: nowrap;
  white-space: nowrap;
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 9px;
  letter-spacing: 0.03em;
  color: color-mix(in srgb, var(--layout-brand-primary) 55%, #94a3b8);
  animation: cyberNavStreamScroll 18s linear infinite;
}

.context-switcher__stream-chunk {
  margin-right: 1.1rem;
}

.top-nav__right {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-shrink: 1;
  min-width: 0;
}

.top-search {
  width: clamp(120px, 14vw, 200px);
}

.top-search--cyber :deep(.el-input__wrapper) {
  position: relative;
  min-height: 38px;
  overflow: visible;
  border-radius: 14px;
  background: linear-gradient(
    152deg,
    color-mix(in srgb, #0b1224 92%, transparent),
    color-mix(in srgb, #161f38 78%, transparent)
  );
  border: 1px solid color-mix(in srgb, var(--layout-brand-primary) 30%, rgba(167, 139, 250, 0.32));
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.045) inset,
    0 0 20px color-mix(in srgb, var(--layout-brand-primary) 11%, transparent),
    inset 0 1px 0 rgba(167, 139, 250, 0.07);
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.top-search--cyber :deep(.el-input__wrapper):hover {
  border-color: color-mix(in srgb, var(--layout-brand-primary) 45%, rgba(192, 132, 252, 0.4));
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--layout-brand-primary) 15%, transparent) inset,
    0 0 28px color-mix(in srgb, var(--layout-brand-primary) 16%, transparent);
}

.top-search--cyber :deep(.el-input__wrapper)::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  pointer-events: none;
  background: linear-gradient(
    110deg,
    transparent 0%,
    color-mix(in srgb, var(--layout-brand-primary) 50%, transparent) 25%,
    transparent 40%,
    color-mix(in srgb, #a78bfa 48%, transparent) 58%,
    transparent 72%,
    color-mix(in srgb, var(--layout-brand-primary) 42%, transparent) 88%,
    transparent 100%
  );
  background-size: 280% 100%;
  animation: cyberNavFiber 5.2s linear infinite;
  opacity: 0.34;
  z-index: 0;
}

.top-search--cyber :deep(.el-input__wrapper)::after {
  content: '';
  pointer-events: none;
  position: absolute;
  left: 40px;
  right: 11px;
  top: 6px;
  bottom: 6px;
  border-radius: 8px;
  background-image:
    linear-gradient(rgba(0, 216, 255, 0.13) 1px, transparent 1px),
    linear-gradient(90deg, rgba(167, 139, 250, 0.1) 1px, transparent 1px);
  background-size: 10px 10px;
  z-index: 1;
  opacity: 0.52;
  animation: cyberNavScanPulse 3.2s ease-in-out infinite;
}

.top-search--cyber :deep(.el-input__inner) {
  position: relative;
  z-index: 2;
}

.top-search--cyber :deep(.el-input__inner::placeholder) {
  color: var(--layout-text-subtle);
}

.top-search__holo {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  z-index: 3;
  margin-right: 2px;
}

.top-search__holo-svg {
  filter: drop-shadow(0 0 5px color-mix(in srgb, var(--layout-brand-primary) 50%, transparent))
    drop-shadow(0 0 11px color-mix(in srgb, #a78bfa 32%, transparent));
}

.top-search__holo-beam {
  position: absolute;
  bottom: -3px;
  left: 50%;
  width: 30px;
  height: 2px;
  margin-left: -15px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--layout-brand-primary), transparent);
  animation: cyberNavHoloBeam 2.7s ease-in-out infinite;
  pointer-events: none;
}

.nav-icon-btn {
  font-size: 20px;
  color: var(--layout-text-muted);
  cursor: pointer;
  transition: color 0.25s ease, filter 0.25s ease, transform 0.2s ease;
}

.nav-icon-btn:hover {
  color: var(--layout-brand-primary);
  filter: drop-shadow(0 0 8px var(--layout-brand-glow));
}

.notice-badge--cyber :deep(.el-badge__content) {
  background: linear-gradient(180deg, #ff9340, #ff6500) !important;
  border: 1px solid rgba(255, 224, 160, 0.55) !important;
  color: #1a0c02 !important;
  font-weight: 800 !important;
  font-size: 10px !important;
  min-width: 19px !important;
  height: 19px !important;
  line-height: 17px !important;
  padding: 0 5px !important;
  box-shadow:
    0 0 14px rgba(255, 100, 0, 0.85),
    0 0 28px rgba(255, 120, 40, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.4) !important;
}

.notice-badge:not(.notice-badge--cyber) :deep(.el-badge__content) {
  font-size: 10px;
}

.notice-bell-cyber {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  outline: none;
  color: inherit;
  animation: cyberNavBellPulse 2.85s ease-in-out infinite;
}

.notice-bell-cyber:focus-visible {
  border-radius: 10px;
  box-shadow: 0 0 0 2px color-mix(in srgb, #a855f7 55%, transparent);
}

.notice-bell-cyber__ring {
  position: absolute;
  inset: 2px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, #a855f7 58%, transparent);
  pointer-events: none;
}

.notice-bell-cyber__ring--1 {
  animation: cyberNavRingExpand 2.45s ease-out infinite;
}

.notice-bell-cyber__ring--2 {
  animation: cyberNavRingExpand 2.45s ease-out 0.58s infinite;
}

.notice-bell-cyber__ring--3 {
  animation: cyberNavRingExpand 2.45s ease-out 1.16s infinite;
}

.notice-bell-cyber__svg {
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 0 9px rgba(124, 58, 237, 0.5));
}

.settings-cyber {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  filter: drop-shadow(0 0 5px color-mix(in srgb, var(--layout-brand-primary) 35%, transparent))
    drop-shadow(0 0 10px color-mix(in srgb, #a855f7 28%, transparent));
  transition: transform 0.28s ease, filter 0.28s ease;
}

.settings-cyber:hover {
  transform: scale(1.08) rotate(-10deg);
  filter: drop-shadow(0 0 14px color-mix(in srgb, var(--layout-brand-primary) 55%, transparent))
    drop-shadow(0 0 18px color-mix(in srgb, #a855f7 38%, transparent));
}

.settings-cyber:focus-visible {
  border-radius: 10px;
  outline: none;
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--layout-brand-primary) 45%, transparent);
}

.settings-cyber__svg {
  display: block;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition:
    background 0.25s ease,
    box-shadow 0.25s ease;
}

.user-info--cyber {
  gap: 12px;
  padding: 6px 10px 22px;
  border-radius: 12px;
}

.user-info:hover {
  background: var(--layout-brand-surface);
  box-shadow: 0 0 0 1px var(--layout-brand-border);
}

.user-avatar-shell {
  position: relative;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar-shell__orbit {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  animation: cyberNavGearRotate 18s linear infinite;
}

.user-avatar-shell__orbit--a {
  inset: -4px;
  border: 1px dashed color-mix(in srgb, var(--layout-brand-primary) 62%, transparent);
  opacity: 0.7;
}

.user-avatar-shell__orbit--b {
  inset: -8px;
  border: 1px solid color-mix(in srgb, #a78bfa 42%, transparent);
  opacity: 0.38;
  animation-direction: reverse;
  animation-duration: 26s;
}

.user-avatar {
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--layout-brand-primary), #1e5a8e);
  font-size: 14px;
  font-weight: 600;
}

.user-avatar--cyber {
  border: 2px solid color-mix(in srgb, var(--layout-brand-primary) 78%, transparent) !important;
  box-shadow:
    0 0 18px color-mix(in srgb, var(--layout-brand-primary) 38%, transparent),
    inset 0 0 14px rgba(0, 216, 255, 0.12) !important;
}

.user-avatar :deep(img) {
  object-fit: cover;
}

.user-hud {
  position: absolute;
  left: -2px;
  right: -2px;
  bottom: 2px;
  padding: 14px 4px 3px;
  border-radius: 0 0 10px 10px;
  background: linear-gradient(180deg, transparent, rgba(8, 12, 22, 0.82));
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-family: ui-monospace, monospace;
  font-size: 6px;
  line-height: 1.2;
  letter-spacing: 0.04em;
  color: color-mix(in srgb, var(--layout-brand-primary) 75%, #e2e8f0);
  text-shadow: 0 0 8px color-mix(in srgb, var(--layout-brand-primary) 35%, transparent);
  pointer-events: none;
  opacity: 0.92;
}

.user-hud__line {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.user-name {
  font-size: 14px;
  line-height: 1.2;
  color: var(--layout-text);
}

.user-name--cyber {
  font-weight: 600;
  letter-spacing: 0.035em;
  text-shadow:
    0 0 12px color-mix(in srgb, var(--layout-brand-primary) 32%, transparent),
    0 0 26px color-mix(in srgb, var(--layout-brand-primary) 14%, transparent);
}

.user-arrow {
  font-size: 13px;
  color: var(--layout-text-subtle);
}

/* ===== 布局主体 ===== */
.layout-body {
  position: relative;
  z-index: 1;
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ===== 左侧菜单：与主内容区同系渐变，无突兀色块 ===== */
.side-nav--tech {
  position: relative;
  z-index: 4;
  width: 188px;
  flex-shrink: 0;
  background: linear-gradient(
    180deg,
    #0a0f1e 0%,
    color-mix(in srgb, var(--layout-bg-to) 72%, #111827) 100%
  );
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-right: 1px solid var(--layout-brand-border);
  box-shadow: inset -1px 0 0 rgba(0, 216, 255, 0.06);
  overflow-y: auto;
  overflow-x: hidden;
}

.side-menu--tech {
  border-right: none;
  font-size: 13px;
  background: transparent !important;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: transparent;
}

.side-menu--tech :deep(.el-menu-item),
.side-menu--tech :deep(.el-sub-menu__title) {
  height: 42px;
  line-height: 42px;
  font-size: 13px;
  border-radius: 0 10px 10px 0;
  margin-right: 8px;
  border-left: 3px solid transparent;
  color: var(--layout-text-muted) !important;
  background: transparent !important;
  transition:
    color 0.28s ease,
    background 0.28s ease,
    border-color 0.28s ease,
    box-shadow 0.28s ease,
    text-shadow 0.28s ease;
}

/* 图标：默认浅灰，悬停霓虹青 + 过渡 */
.side-menu--tech :deep(.el-menu-item .el-icon),
.side-menu--tech :deep(.el-sub-menu__title .el-icon) {
  color: #aeb9c9 !important;
  transition: color 0.28s ease, filter 0.28s ease;
}

.side-menu--tech :deep(.el-menu-item:hover .el-icon),
.side-menu--tech :deep(.el-sub-menu__title:hover .el-icon) {
  color: var(--layout-brand-primary) !important;
  filter: drop-shadow(0 0 6px var(--layout-brand-glow));
}

.side-menu--tech :deep(.el-menu-item:hover),
.side-menu--tech :deep(.el-sub-menu__title:hover) {
  background: rgba(0, 216, 255, 0.05) !important;
  color: var(--layout-text) !important;
}

/* 激活项：无实心底，左侧霓虹条 + 文字微光（router 由 el-menu router 驱动，类名仍为 .is-active） */
.side-menu--tech :deep(.el-menu-item.is-active) {
  background: transparent !important;
  font-weight: 600;
  color: #f0f4f8 !important;
  border-left-color: var(--layout-brand-primary);
  box-shadow:
    inset 4px 0 18px -4px rgba(0, 216, 255, 0.45),
    -2px 0 20px rgba(0, 216, 255, 0.12);
  text-shadow: 0 0 14px rgba(0, 216, 255, 0.35);
}

.side-menu--tech :deep(.el-menu-item.is-active .el-icon) {
  color: var(--layout-brand-primary) !important;
  filter: drop-shadow(0 0 8px var(--layout-brand-glow));
}

.side-menu--tech :deep(.el-menu-item.is-active:hover) {
  background: rgba(0, 216, 255, 0.04) !important;
}

.side-menu--tech :deep(.el-sub-menu .el-menu-item) {
  height: 38px;
  line-height: 38px;
  padding-left: 48px !important;
  font-size: 13px;
  border-left: 3px solid transparent;
}

.side-menu--tech :deep(.el-sub-menu .el-menu-item.is-active) {
  background: transparent !important;
  font-weight: 600;
  color: #f0f4f8 !important;
  border-left-color: var(--layout-brand-primary);
  box-shadow:
    inset 4px 0 18px -4px rgba(0, 216, 255, 0.45),
    -2px 0 20px rgba(0, 216, 255, 0.12);
  text-shadow: 0 0 14px rgba(0, 216, 255, 0.35);
}

.side-menu--tech :deep(.el-sub-menu.is-opened > .el-sub-menu__title) {
  color: var(--layout-text) !important;
}

/* 子路由匹配时父级「缺陷管理 / 系统管理」标题轻量高亮（仍无实心底） */
.side-menu--tech :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #e8eaef !important;
  text-shadow: 0 0 12px rgba(0, 216, 255, 0.22);
}

/* ===== 主内容 ===== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.backend-health-alert {
  margin: 10px 20px 0;
}

.content-header {
  position: relative;
  z-index: 1;
  height: 42px;
  padding: 0 20px;
  background: color-mix(in srgb, var(--layout-bg-to) 58%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--layout-brand-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.content-header :deep(.el-breadcrumb__inner),
.content-header :deep(.el-breadcrumb__separator) {
  color: var(--layout-text-muted);
  font-weight: 500;
}

.content-header :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--layout-text);
}

.content-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content-header__actions :deep(.el-button) {
  color: var(--layout-text-muted);
}

.content-header__actions :deep(.el-button:hover) {
  color: var(--layout-brand-primary);
}

.content-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 20px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--layout-bg-from) 55%, transparent) 0%,
    color-mix(in srgb, var(--layout-bg-to) 88%, #0a101d) 100%
  );
}
</style>
