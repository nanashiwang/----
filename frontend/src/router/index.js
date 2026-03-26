import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    children: [
      { path: '', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'profile', name: 'UserProfile', component: () => import('../views/users/UserProfile.vue') },
      {
        path: 'market/data',
        name: 'MarketDataCenter',
        component: () => import('../views/market/MarketDataCenter.vue'),
        meta: { keepAlive: true },
      },
      {
        path: 'news/articles',
        name: 'NewsArticles',
        component: () => import('../views/news/NewsArticles.vue'),
        meta: { keepAlive: true },
      },
      {
        path: 'news/briefs',
        name: 'NewsBriefs',
        component: () => import('../views/news/NewsBriefs.vue'),
        meta: { keepAlive: true },
      },
      { path: 'settings/llm', name: 'LLMSettings', component: () => import('../views/settings/LLMSettings.vue'), meta: { admin: true } },
      { path: 'settings/tushare', name: 'TushareSettings', component: () => import('../views/settings/TushareSettings.vue'), meta: { admin: true } },
      { path: 'settings/database', name: 'DatabaseSettings', component: () => import('../views/settings/DatabaseSettings.vue'), meta: { admin: true } },
      { path: 'agents', name: 'AgentList', component: () => import('../views/agents/AgentList.vue'), meta: { admin: true } },
      { path: 'agents/:id', name: 'AgentEdit', component: () => import('../views/agents/AgentEdit.vue'), meta: { admin: true } },
      { path: 'sources', name: 'SourceList', component: () => import('../views/sources/SourceList.vue'), meta: { admin: true } },
      { path: 'admin/logs', name: 'AdminUsageLogs', component: () => import('../views/admin/AdminUsageLogs.vue'), meta: { admin: true } },
      { path: 'recommend', name: 'RecommendBoard', component: () => import('../views/recommend/RecommendBoard.vue') },
      { path: 'review', name: 'ReviewList', component: () => import('../views/review/ReviewList.vue') },
      {
        path: 'ml',
        name: 'MachineLearningLab',
        component: () => import('../views/ml/MachineLearningLab.vue'),
        meta: { keepAlive: true },
      },
      {
        path: 'knowledge',
        name: 'KnowledgeBase',
        component: () => import('../views/knowledge/KnowledgeBase.vue'),
        meta: { keepAlive: true },
      },
      {
        path: 'backtest',
        name: 'BacktestPanel',
        component: () => import('../views/backtest/BacktestPanel.vue'),
        meta: { keepAlive: true },
      },
      { path: 'trades', name: 'TradeList', component: () => import('../views/trades/TradeList.vue') },
      { path: 'users', name: 'UserManage', component: () => import('../views/users/UserManage.vue'), meta: { admin: true } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (to.path === '/login' && auth.token) return next('/')
    return next()
  }
  if (!auth.token) return next('/login')
  if (to.meta.admin && auth.user?.role !== 'admin') return next('/')
  next()
})

export default router
