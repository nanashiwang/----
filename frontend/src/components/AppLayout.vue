<template>
  <div class="app-frame">
    <div class="app-glow app-glow--one"></div>
    <div class="app-glow app-glow--two"></div>
    <div class="app-glow app-glow--three"></div>

    <el-container class="layout-shell">
      <el-aside width="286px" class="layout-aside">
        <div class="brand-card glass-surface">
          <div class="brand-mark">QA</div>
          <div class="brand-copy">
            <h2>QuantAgent</h2>
            <p>?????????</p>
          </div>
        </div>

        <div class="aside-caption">Workspace Map</div>

        <div class="aside-nav">
          <el-menu
            ref="menuRef"
            :default-active="route.path"
            :default-openeds="defaultOpenGroups"
            class="side-menu"
            router
            @open="handleMenuOpen"
            @close="handleMenuClose"
          >
            <el-sub-menu v-for="group in navGroups" :key="group.index" :index="group.index">
              <template #title>
                <el-icon><component :is="group.icon" /></el-icon>
                <div class="group-copy">
                  <span>{{ group.title }}</span>
                  <small>{{ group.hint }}</small>
                </div>
                <span class="group-count">{{ group.items.length }}</span>
              </template>
              <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path">
                <div class="menu-copy">
                  <span>{{ item.label }}</span>
                  <small>{{ item.desc }}</small>
                </div>
              </el-menu-item>
            </el-sub-menu>

            <el-sub-menu v-if="auth.isAdmin" index="admin">
              <template #title>
                <el-icon><Setting /></el-icon>
                <div class="group-copy">
                  <span>????</span>
                  <small>??????????</small>
                </div>
                <span class="group-count">{{ adminItems.length }}</span>
              </template>
              <el-menu-item v-for="item in adminItems" :key="item.path" :index="item.path">
                <div class="menu-copy">
                  <span>{{ item.label }}</span>
                  <small>{{ item.desc }}</small>
                </div>
              </el-menu-item>
            </el-sub-menu>
          </el-menu>
        </div>
      </el-aside>

      <el-container class="layout-content">
        <el-header class="layout-header">
          <div class="header-copy">
            <div class="header-eyebrow">Quant Command Center</div>
            <h1>{{ currentRouteMeta.title }}</h1>
            <p>{{ currentRouteMeta.description }}</p>
          </div>

          <div class="header-tools">
            <div class="header-pill glass-surface">
              <span>????</span>
              <strong>{{ todayLabel }}</strong>
            </div>

            <el-dropdown @command="handleCommand">
              <div class="account-pill glass-surface">
                <div class="account-avatar">{{ userInitial }}</div>
                <div class="account-copy">
                  <strong>{{ auth.user?.username || 'Guest' }}</strong>
                  <small>{{ auth.isAdmin ? '????????' : '???????' }}</small>
                </div>
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">????</el-dropdown-item>
                  <el-dropdown-item command="logout">????</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="layout-main">
          <router-view v-slot="{ Component, route: viewRoute }">
            <keep-alive :include="keepAliveRouteNames">
              <component
                :is="Component"
                :key="viewRoute.meta.keepAlive ? String(viewRoute.name || viewRoute.path) : viewRoute.fullPath"
              />
            </keep-alive>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  CollectionTag,
  DataAnalysis,
  DataBoard,
  Monitor,
  Operation,
  Setting,
  TrendCharts,
} from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'

const MENU_OPEN_GROUPS_STORAGE_KEY = 'quant-agent-open-menu-groups'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const menuRef = ref(null)

const navGroups = [
  {
    index: 'overview',
    title: '????',
    hint: '??????????????',
    icon: DataBoard,
    items: [
      { path: '/', label: '???', desc: '???????????????' },
      { path: '/profile', label: '????', desc: '????????????????' },
    ],
  },
  {
    index: 'execution',
    title: '????',
    hint: '??????????????',
    icon: TrendCharts,
    items: [
      { path: '/recommend', label: '????', desc: '?????????????' },
      { path: '/trades', label: '????', desc: '????????????' },
    ],
  },
  {
    index: 'validation',
    title: '????',
    hint: '??????????????',
    icon: DataAnalysis,
    items: [
      { path: '/backtest', label: '????', desc: '?????????????' },
      { path: '/review', label: '????', desc: '???????????' },
    ],
  },
  {
    index: 'research',
    title: '????',
    hint: '????????????',
    icon: Operation,
    items: [
      { path: '/ml', label: '??????', desc: '???????????????' },
    ],
  },
  {
    index: 'intelligence',
    title: '????',
    hint: '??????????????',
    icon: Monitor,
    items: [
      { path: '/market/data', label: '??????', desc: '??????????????????' },
      { path: '/news/articles', label: '????', desc: '???????????????????' },
      { path: '/news/briefs', label: '????', desc: '???????????????' },
    ],
  },
  {
    index: 'knowledge',
    title: '????',
    hint: '?????????????',
    icon: CollectionTag,
    items: [
      { path: '/knowledge', label: '???', desc: '??????????????' },
    ],
  },
]

const adminItems = [
  { path: '/settings/llm', label: 'LLM ??', desc: '?????Key ??????' },
  { path: '/settings/tushare', label: 'Tushare ??', desc: '?????????' },
  { path: '/settings/database', label: '?????', desc: '????????????' },
  { path: '/agents', label: 'Agent ??', desc: '????????????????' },
  { path: '/sources', label: '?????', desc: '??????????' },
  { path: '/users', label: '????', desc: '???????????' },
  { path: '/admin/logs', label: '????', desc: '????????????' },
]

function getStoredOpenGroups() {
  if (typeof window === 'undefined') {
    return []
  }
  try {
    const raw = window.localStorage.getItem(MENU_OPEN_GROUPS_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string') : []
  } catch {
    return []
  }
}

const openMenuGroups = ref(getStoredOpenGroups())
const keepAliveRouteNames = computed(() =>
  router
    .getRoutes()
    .filter(item => item.meta?.keepAlive && typeof item.name === 'string')
    .map(item => item.name)
)

const routeMeta = {
  '/profile': { title: '????', description: '??????????????????????????' },
  '/': { title: '???', description: '????????????????????????????' },
  '/recommend': { title: '????', description: '????????????????????????' },
  '/trades': { title: '????', description: '?????????????????????????' },
  '/backtest': { title: '????', description: '????????????????????????' },
  '/review': { title: '????', description: '?????????????????????????' },
  '/ml': { title: '??????', description: '???????????????????????????????' },
  '/market/data': { title: '??????', description: '??????????????????????????????????' },
  '/news/articles': { title: '????', description: '??????????????????????????????' },
  '/news/briefs': { title: '????', description: '?????????????????????????' },
  '/knowledge': { title: '???', description: '????????????????????????' },
  '/settings/llm': { title: 'LLM ??', description: '?????????????????????' },
  '/settings/tushare': { title: 'Tushare ??', description: '????????????????????' },
  '/settings/database': { title: '?????', description: '???????????????????' },
  '/agents': { title: 'Agent ??', description: '???????????????????????' },
  '/sources': { title: '?????', description: '?????????????????????' },
  '/users': { title: '????', description: '???????????????' },
  '/admin/logs': { title: '????', description: '??????????????????????????' },
}

function resolveRouteMeta(path) {
  if (path.startsWith('/agents/')) {
    return { title: 'Agent ??', description: '??????????????????' }
  }
  return routeMeta[path] || { title: 'QuantAgent', description: '?????????????????' }
}

const allMenuGroupIndexes = computed(() => {
  const indexes = navGroups.map(group => group.index)
  if (auth.isAdmin) {
    indexes.push('admin')
  }
  return indexes
})

function isMenuItemActive(itemPath, currentPath) {
  if (itemPath === currentPath) {
    return true
  }
  if (itemPath === '/') {
    return currentPath === '/'
  }
  return currentPath.startsWith(`${itemPath}/`)
}

const currentRouteGroup = computed(() => {
  for (const group of navGroups) {
    if (group.items.some(item => isMenuItemActive(item.path, route.path))) {
      return group.index
    }
  }

  if (auth.isAdmin && adminItems.some(item => isMenuItemActive(item.path, route.path))) {
    return 'admin'
  }

  return ''
})

const defaultOpenGroups = computed(() => {
  return normalizeOpenGroups([
    ...openMenuGroups.value,
    ...(currentRouteGroup.value ? [currentRouteGroup.value] : []),
  ])
})

const currentRouteMeta = computed(() => resolveRouteMeta(route.path))
const userInitial = computed(() => (auth.user?.username || 'Q').slice(0, 1).toUpperCase())
const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date())

function normalizeOpenGroups(groups) {
  const validIndexes = new Set(allMenuGroupIndexes.value)
  return Array.from(new Set(groups.filter(group => validIndexes.has(group))))
}

function persistOpenGroups(groups) {
  const normalized = normalizeOpenGroups(groups)
  openMenuGroups.value = normalized
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(MENU_OPEN_GROUPS_STORAGE_KEY, JSON.stringify(normalized))
  }
}

function handleMenuOpen(index) {
  persistOpenGroups([...openMenuGroups.value, index])
}

function handleMenuClose(index) {
  persistOpenGroups(openMenuGroups.value.filter(group => group !== index))
}

function handleCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
    return
  }
  if (command === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

watch(
  () => auth.isAdmin,
  () => {
    persistOpenGroups(openMenuGroups.value)
  },
  { immediate: true }
)

watch(
  () => route.path,
  async () => {
    if (!currentRouteGroup.value) {
      return
    }

    if (!openMenuGroups.value.includes(currentRouteGroup.value)) {
      persistOpenGroups([...openMenuGroups.value, currentRouteGroup.value])
    }

    await nextTick()
    menuRef.value?.open?.(currentRouteGroup.value)
  },
  { immediate: true }
)
</script>

<style scoped>
.app-frame {
  position: relative;
  height: 100vh;
  min-height: 100vh;
  padding: 24px;
  overflow: hidden;
}

.app-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(100px);
  opacity: 0.5;
  pointer-events: none;
  animation: float-glow 25s ease-in-out infinite;
}

.app-glow--one {
  width: 400px;
  height: 400px;
  top: -100px;
  right: 10%;
  background: rgba(0, 102, 255, 0.2);
}

.app-glow--two {
  width: 320px;
  height: 320px;
  bottom: 10%;
  left: -60px;
  background: rgba(0, 212, 170, 0.18);
  animation-delay: -8s;
}

.app-glow--three {
  width: 260px;
  height: 260px;
  top: 35%;
  left: 30%;
  background: rgba(255, 159, 64, 0.15);
  animation-delay: -15s;
}

@keyframes float-glow {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.5;
  }
  33% {
    transform: translate(30px, -30px) scale(1.08);
    opacity: 0.65;
  }
  66% {
    transform: translate(-20px, 25px) scale(0.92);
    opacity: 0.45;
  }
}

.layout-shell {
  position: relative;
  z-index: 1;
  height: calc(100vh - 48px);
  min-height: calc(100vh - 48px);
  border-radius: var(--radius-2xl);
  overflow: hidden;
  background: rgba(250, 252, 255, 0.5);
  border: 1.5px solid rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(40px) saturate(180%);
  -webkit-backdrop-filter: blur(40px) saturate(180%);
  box-shadow: 0 32px 96px rgba(50, 77, 108, 0.16);
}

.layout-aside {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
  min-height: 0;
  padding: 24px 20px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(8, 20, 35, 0.88), rgba(14, 30, 48, 0.78)),
    rgba(10, 22, 38, 0.6);
  color: #f5f9ff;
  border-right: 1.5px solid rgba(255, 255, 255, 0.08);
}

.brand-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.12);
  border: 1.5px solid rgba(255, 255, 255, 0.16);
  border-radius: var(--radius-lg);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transition: all var(--transition-base);
}

.brand-card:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(0, 102, 255, 0.98), rgba(0, 212, 170, 0.92));
  color: #fff;
  font-weight: 800;
  font-size: 20px;
  letter-spacing: 0.05em;
  box-shadow: 0 8px 20px rgba(0, 102, 255, 0.3);
}

.brand-copy h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.brand-copy p {
  margin: 6px 0 0;
  color: rgba(245, 249, 255, 0.65);
  font-size: 12px;
  font-weight: 500;
}

.aside-caption {
  padding: 4px 10px 0;
  color: rgba(243, 248, 255, 0.48);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.16em;
}

.aside-nav {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.layout-content {
  min-width: 0;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: transparent;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-shrink: 0;
  padding: 26px 30px 0;
  height: auto;
}

.header-copy {
  min-width: 0;
}

.header-eyebrow {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.18em;
}

.header-copy h1 {
  margin: 10px 0 10px;
  font-size: clamp(28px, 3vw, 40px);
  line-height: 1.08;
  letter-spacing: -0.04em;
  font-weight: 800;
  background: linear-gradient(135deg, var(--text-primary), var(--brand-primary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-copy p {
  margin: 0;
  max-width: 720px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.header-tools {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-pill {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 18px;
  min-width: 180px;
  transition: all var(--transition-base);
}

.header-pill:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.header-pill span,
.account-copy small {
  color: var(--text-secondary);
  font-size: 12px;
}

.header-pill strong {
  font-size: 14px;
}

.account-pill {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all var(--transition-base);
}

.account-pill:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.account-avatar {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
  color: #fff;
  font-weight: 800;
  font-size: 16px;
  box-shadow: 0 6px 16px rgba(0, 102, 255, 0.3);
}

.account-copy {
  display: flex;
  flex-direction: column;
}

.layout-main {
  flex: 1;
  min-height: 0;
  padding: 28px 30px 30px;
  overflow: auto;
  overscroll-behavior: contain;
  background: transparent;
}

.group-copy,
.menu-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.group-copy span,
.menu-copy span {
  font-weight: 700;
}

.group-copy small,
.menu-copy small {
  color: inherit;
  opacity: 0.62;
  font-size: 12px;
}

.group-count {
  margin-left: auto;
  min-width: 26px;
  height: 26px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(245, 249, 255, 0.72);
  font-size: 11px;
  font-weight: 700;
}

:deep(.side-menu) {
  border: none;
  background: transparent;
}

:deep(.side-menu .el-sub-menu__title),
:deep(.side-menu .el-menu-item) {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  height: auto;
  min-height: 60px;
  line-height: 1.3;
  margin-bottom: 8px;
  padding: 16px 18px !important;
  border-radius: var(--radius-lg);
  color: rgba(245, 249, 255, 0.85);
  transition: all var(--transition-base);
}

:deep(.side-menu .el-sub-menu__title:hover),
:deep(.side-menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transform: translateX(3px);
}

:deep(.side-menu .el-sub-menu.is-active > .el-sub-menu__title) {
  background: rgba(255, 255, 255, 0.14);
  color: #ffffff;
  border: 1.5px solid rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

:deep(.side-menu .el-sub-menu.is-active > .el-sub-menu__title .group-count) {
  background: rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.95);
}

:deep(.side-menu .el-menu-item.is-active) {
  border: 1.5px solid rgba(255, 255, 255, 0.18);
  background: linear-gradient(135deg, rgba(0, 102, 255, 0.92), rgba(0, 212, 170, 0.9));
  color: #ffffff;
  box-shadow:
    0 12px 28px rgba(0, 102, 255, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transform: translateX(5px);
}

:deep(.side-menu .el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 10px;
  top: 50%;
  width: 4px;
  height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.98);
  transform: translateY(-50%);
}

:deep(.side-menu .el-menu-item.is-active .menu-copy) {
  padding-left: 10px;
}

:deep(.side-menu .el-menu-item.is-active .menu-copy span) {
  color: #ffffff;
  font-weight: 800;
}

:deep(.side-menu .el-menu-item.is-active .menu-copy small) {
  color: rgba(255, 255, 255, 0.82);
  opacity: 1;
}

:deep(.side-menu .el-sub-menu .el-menu) {
  border: none;
  background: transparent;
}

:deep(.side-menu .el-sub-menu__icon-arrow) {
  color: rgba(243, 248, 255, 0.58);
}

@media (max-width: 1200px) {
  .app-frame {
    padding: 14px;
  }

  .layout-shell {
    border-radius: 26px;
  }

  .layout-aside {
    width: 244px !important;
  }
}

@media (max-width: 960px) {
  .app-frame {
    height: auto;
    overflow: visible;
  }

  .layout-shell {
    flex-direction: column;
    height: auto;
  }

  .layout-aside {
    position: static;
    width: 100% !important;
    height: auto;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  .layout-content,
  .layout-main {
    height: auto;
    overflow: visible;
  }

  .layout-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-tools {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .layout-main {
    padding: 22px;
  }
}
</style>
