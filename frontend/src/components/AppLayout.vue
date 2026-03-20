<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">多Agent量化交易</div>
      <el-menu :default-active="route.path" router :collapse="false" background-color="#001529" text-color="#ffffffa6" active-text-color="#fff">
        <el-menu-item index="/">
          <el-icon><DataBoard /></el-icon><span>仪表盘</span>
        </el-menu-item>

        <el-sub-menu index="recommend-group">
          <template #title><el-icon><TrendCharts /></el-icon><span>交易中心</span></template>
          <el-menu-item index="/recommend">推荐看板</el-menu-item>
          <el-menu-item index="/trades">交易记录</el-menu-item>
          <el-menu-item index="/backtest">回测系统</el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="analysis-group">
          <template #title><el-icon><DataAnalysis /></el-icon><span>分析复盘</span></template>
          <el-menu-item index="/review">复盘分析</el-menu-item>
          <el-menu-item index="/knowledge">知识库</el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="auth.isAdmin" index="admin-group">
          <template #title><el-icon><Setting /></el-icon><span>系统管理</span></template>
          <el-menu-item index="/settings/llm">LLM配置</el-menu-item>
          <el-menu-item index="/settings/tushare">Tushare配置</el-menu-item>
          <el-menu-item index="/settings/database">数据库配置</el-menu-item>
          <el-menu-item index="/agents">Agent管理</el-menu-item>
          <el-menu-item index="/sources">资讯源管理</el-menu-item>
          <el-menu-item index="/users">用户管理</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span></span>
        <el-dropdown @command="handleCommand">
          <span class="user-info">{{ auth.user?.username }} <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function handleCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #001529; overflow-y: auto; }
.logo { color: #fff; font-size: 16px; font-weight: bold; text-align: center; padding: 20px 0; border-bottom: 1px solid #ffffff1a; }
.header { display: flex; justify-content: space-between; align-items: center; background: #fff; border-bottom: 1px solid #eee; }
.user-info { cursor: pointer; display: flex; align-items: center; gap: 4px; }
.main { background: #f5f7fa; }
</style>
