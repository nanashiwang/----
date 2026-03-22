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
            <p>量化交易协同控制台</p>
          </div>
        </div>

        <div class="aside-caption">Workspace</div>

        <div class="aside-nav">
          <el-menu :default-active="route.path" class="side-menu" router unique-opened>
            <el-menu-item index="/">
              <el-icon><DataBoard /></el-icon>
              <div class="menu-copy">
                <span>指挥台</span>
                <small>系统概览与工作流入口</small>
              </div>
            </el-menu-item>

            <el-sub-menu v-for="group in navGroups" :key="group.index" :index="group.index">
              <template #title>
                <el-icon><component :is="group.icon" /></el-icon>
                <span>{{ group.title }}</span>
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
                <span>系统管理</span>
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

        <div class="aside-footer glass-surface">
          <span>会话状态</span>
          <strong>{{ auth.isAdmin ? '管理员模式' : '标准模式' }}</strong>
          <small>当前界面已切换为更轻盈的玻璃化视觉层。</small>
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
              <span>今日节奏</span>
              <strong>{{ todayLabel }}</strong>
            </div>

            <el-dropdown @command="handleCommand">
              <div class="account-pill glass-surface">
                <div class="account-avatar">{{ userInitial }}</div>
                <div class="account-copy">
                  <strong>{{ auth.user?.username || 'Guest' }}</strong>
                  <small>{{ auth.isAdmin ? '拥有系统管理权限' : '浏览与执行权限' }}</small>
                </div>
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="layout-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, DataAnalysis, DataBoard, Setting, TrendCharts } from '@element-plus/icons-vue'

import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navGroups = [
  {
    index: 'trade',
    title: '交易中心',
    icon: TrendCharts,
    items: [
      { path: '/recommend', label: '推荐看板', desc: '查看策略输出与权重分布' },
      { path: '/trades', label: '交易记录', desc: '录入与回看真实成交' },
      { path: '/backtest', label: '回测系统', desc: '检验策略在历史区间的表现' },
    ],
  },
  {
    index: 'analysis',
    title: '分析复盘',
    icon: DataAnalysis,
    items: [
      { path: '/review', label: '复盘分析', desc: '沉淀正确与错误决策样本' },
      { path: '/knowledge', label: '知识库', desc: '维护热知识与冷知识资产' },
    ],
  },
]

const adminItems = [
  { path: '/settings/llm', label: 'LLM 配置', desc: '模型接入、Key 与验证' },
  { path: '/settings/tushare', label: 'Tushare 配置', desc: '行情数据授权与检查' },
  { path: '/settings/database', label: '数据库配置', desc: '查看当前数据源连接信息' },
  { path: '/agents', label: 'Agent 管理', desc: '控制各智能体角色与启停' },
  { path: '/sources', label: '资讯源管理', desc: '维护新闻与情报采集源' },
  { path: '/users', label: '用户管理', desc: '管理登录账号与权限范围' },
]

const routeMeta = {
  '/': { title: '指挥台', description: '把推荐、交易、知识和工作流状态汇聚到一个更清晰的主视图。' },
  '/recommend': { title: '推荐看板', description: '用更直观的方式查看策略结果、权重变化与当日推荐。' },
  '/trades': { title: '交易记录', description: '跟踪真实交易数据，并把执行动作沉淀为可追溯的记录。' },
  '/backtest': { title: '回测系统', description: '快速验证参数区间，帮助策略在上线前更早暴露风险。' },
  '/review': { title: '复盘分析', description: '把正确与错误案例聚合起来，形成更高质量的经验闭环。' },
  '/knowledge': { title: '知识库', description: '管理模型沉淀出的高价值知识，让判断依据持续积累。' },
  '/settings/llm': { title: 'LLM 配置', description: '集中维护模型供应商、网关地址与调用连通性。' },
  '/settings/tushare': { title: 'Tushare 配置', description: '检查行情数据接入状态，保证策略输入稳定。' },
  '/settings/database': { title: '数据库配置', description: '查看应用当前使用的存储链路与配置来源。' },
  '/agents': { title: 'Agent 管理', description: '统一管理多智能体的提示词、模型配置与启停状态。' },
  '/sources': { title: '资讯源管理', description: '维护新闻采集源，让观察层输入更加稳定可靠。' },
  '/users': { title: '用户管理', description: '维护账号、角色与系统访问边界。' },
}

function resolveRouteMeta(path) {
  if (path.startsWith('/agents/')) {
    return { title: 'Agent 详情', description: '编辑单个智能体的角色配置与行为策略。' }
  }
  return routeMeta[path] || { title: 'QuantAgent', description: '现代化的多智能体量化交易控制界面。' }
}

const currentRouteMeta = computed(() => resolveRouteMeta(route.path))
const userInitial = computed(() => (auth.user?.username || 'Q').slice(0, 1).toUpperCase())
const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date())

function handleCommand(command) {
  if (command === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-frame {
  position: relative;
  min-height: 100vh;
  padding: 24px;
  overflow: hidden;
}

.app-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.65;
  pointer-events: none;
}

.app-glow--one {
  width: 340px;
  height: 340px;
  top: -80px;
  right: 12%;
  background: rgba(30, 124, 242, 0.22);
}

.app-glow--two {
  width: 280px;
  height: 280px;
  bottom: 12%;
  left: -40px;
  background: rgba(43, 195, 177, 0.2);
}

.app-glow--three {
  width: 220px;
  height: 220px;
  top: 34%;
  left: 32%;
  background: rgba(255, 184, 92, 0.18);
}

.layout-shell {
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 48px);
  border-radius: 34px;
  overflow: hidden;
  background: rgba(248, 251, 255, 0.44);
  border: 1px solid rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  box-shadow: 0 28px 80px rgba(50, 77, 108, 0.2);
}

.layout-aside {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px 18px;
  background:
    linear-gradient(180deg, rgba(10, 24, 38, 0.84), rgba(16, 34, 52, 0.72)),
    rgba(12, 26, 41, 0.56);
  color: #f3f8ff;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.brand-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.14);
  box-shadow: none;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(30, 124, 242, 0.96), rgba(43, 195, 177, 0.88));
  color: #fff;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.brand-copy h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}

.brand-copy p {
  margin: 6px 0 0;
  color: rgba(243, 248, 255, 0.62);
  font-size: 12px;
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

.aside-footer {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: none;
}

.aside-footer span,
.aside-footer small {
  color: rgba(243, 248, 255, 0.66);
}

.aside-footer strong {
  color: #ffffff;
  font-size: 16px;
}

.layout-content {
  background: transparent;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
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
  margin: 10px 0 8px;
  font-size: clamp(28px, 3vw, 38px);
  line-height: 1.04;
  letter-spacing: -0.05em;
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
  padding: 14px 16px;
  min-width: 168px;
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
  padding: 12px 14px;
  cursor: pointer;
}

.account-avatar {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
  color: #fff;
  font-weight: 800;
}

.account-copy {
  display: flex;
  flex-direction: column;
}

.layout-main {
  padding: 28px 30px 30px;
  background: transparent;
}

.menu-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-copy span {
  font-weight: 700;
}

.menu-copy small {
  color: inherit;
  opacity: 0.6;
  font-size: 12px;
}

:deep(.side-menu) {
  border: none;
  background: transparent;
}

:deep(.side-menu .el-sub-menu__title),
:deep(.side-menu .el-menu-item) {
  height: auto;
  min-height: 52px;
  line-height: 1.25;
  margin-bottom: 8px;
  padding: 14px 16px !important;
  border-radius: 18px;
  color: rgba(243, 248, 255, 0.82);
  transition: background 0.2s ease, transform 0.2s ease, color 0.2s ease;
}

:deep(.side-menu .el-sub-menu__title:hover),
:deep(.side-menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  transform: translateX(2px);
}

:deep(.side-menu .el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(30, 124, 242, 0.9), rgba(43, 195, 177, 0.88));
  color: #ffffff;
  box-shadow: 0 16px 28px rgba(30, 124, 242, 0.28);
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
  .layout-shell {
    flex-direction: column;
  }

  .layout-aside {
    width: 100% !important;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
