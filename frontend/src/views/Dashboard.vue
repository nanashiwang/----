<template>
  <div class="page-shell">
    <section class="page-hero dashboard-hero">
      <div class="dashboard-hero__copy">
        <span class="page-eyebrow">Strategy Control Layer</span>
        <h2>把工作流、推荐与知识沉淀到一块更清爽的主屏里</h2>
        <p>
          这里是多智能体量化系统的主入口。你可以快速发起观察、推理、复盘流程，并同步查看最近策略产出与执行状态。
        </p>
      </div>

      <div class="dashboard-hero__status glass-surface">
        <span class="section-tag">Workflow Status</span>
        <strong>{{ wfMsg || '系统待命中，可随时发起工作流。' }}</strong>
        <small>建议在新交易日先运行观察，再触发推理与复盘闭环。</small>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="item in statCards" :key="item.label" class="metric-card glass-surface">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
        <div class="metric-hint">{{ item.hint }}</div>
      </article>
    </section>

    <section class="dashboard-grid">
      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">快捷工作流</div>
              <div class="panel-subtitle">把高频操作收敛为更清晰的启动卡片，减少来回切换。</div>
            </div>
            <span class="section-tag">Multi-Agent</span>
          </div>
        </template>

        <div class="workflow-actions">
          <div v-for="action in workflowActions" :key="action.type" class="workflow-action">
            <div>
              <div class="workflow-action__title">{{ action.title }}</div>
              <div class="workflow-action__desc">{{ action.description }}</div>
            </div>
            <el-button :type="action.buttonType" @click="runWf(action.type)" :loading="wfLoading">
              {{ action.buttonText }}
            </el-button>
          </div>
        </div>

        <div class="soft-divider"></div>

        <div class="status-strip">
          <strong>当前反馈：</strong>
          <span>{{ wfMsg || '暂无新任务，系统等待下一次启动。' }}</span>
        </div>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">最新推荐</div>
              <div class="panel-subtitle">优先查看最新生成的推荐理由与权重，快速判断是否需要进一步复核。</div>
            </div>
            <span class="section-tag">{{ latestRec.length }} 条记录</span>
          </div>
        </template>

        <el-table :data="latestRec" size="large" max-height="360" empty-text="暂无推荐数据">
          <el-table-column prop="ts_code" label="股票" width="120" />
          <el-table-column prop="weight" label="权重" width="120">
            <template #default="{ row }">
              <el-progress :percentage="Math.min(100, Math.round((row.weight || 0) * 100))" :stroke-width="14" />
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="推荐理由" show-overflow-tooltip />
          <el-table-column prop="date" label="日期" width="120" />
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import {
  getHotKnowledge,
  getRecommendations,
  getTrades,
  getWorkflowStatus,
  runWorkflow,
} from '../api/index'

const stats = ref({
  todayRec: 0,
  recentRec: 0,
  recentTrades: 0,
  hotKnowledge: 0,
})
const latestRec = ref([])
const wfLoading = ref(false)
const wfMsg = ref('')

const workflowActions = [
  {
    type: 'observe',
    title: '观察工作流',
    description: '收集市场事件、新闻与异动，形成新的观察输入。',
    buttonText: '立即启动',
    buttonType: 'primary',
  },
  {
    type: 'reason',
    title: '推理工作流',
    description: '基于事件与信号生成推荐观点，形成可执行结论。',
    buttonText: '开始推理',
    buttonType: 'success',
  },
  {
    type: 'review',
    title: '复盘工作流',
    description: '回看已执行策略，整理有效经验与错误样本。',
    buttonText: '执行复盘',
    buttonType: 'warning',
  },
]

const statCards = computed(() => [
  {
    label: '今日推荐',
    value: stats.value.todayRec,
    hint: '当天生成的最新推荐数量',
  },
  {
    label: '近期推荐',
    value: stats.value.recentRec,
    hint: '首页当前载入的推荐记录数',
  },
  {
    label: '近期交易',
    value: stats.value.recentTrades,
    hint: '最近载入的成交记录数量',
  },
  {
    label: '热点知识',
    value: stats.value.hotKnowledge,
    hint: '最近同步的热知识条目数',
  },
])

onMounted(async () => {
  try {
    const [rec, trades, kb] = await Promise.all([
      getRecommendations({ limit: 8 }),
      getTrades({ limit: 8 }),
      getHotKnowledge({ limit: 8 }),
    ])

    latestRec.value = rec
    stats.value.recentRec = rec.length
    stats.value.todayRec = rec.filter(item => item.date === new Date().toISOString().slice(0, 10)).length
    stats.value.recentTrades = trades.length
    stats.value.hotKnowledge = kb.length
  } catch {}
})

async function runWf(type) {
  wfLoading.value = true
  wfMsg.value = '工作流已提交，正在初始化...'

  try {
    const res = await runWorkflow(type)
    wfMsg.value = `工作流 ${res.workflow_id} 已启动，正在等待状态回传。`

    const timer = setInterval(async () => {
      const status = await getWorkflowStatus(res.workflow_id)
      wfMsg.value = `${status.status} · ${status.message || '执行中'}`

      if (status.status === 'completed' || status.status === 'failed') {
        clearInterval(timer)
        wfLoading.value = false
        ElMessage[status.status === 'completed' ? 'success' : 'error'](
          status.message || (status.status === 'completed' ? '工作流执行完成' : '工作流执行失败')
        )
      }
    }, 3000)
  } catch {
    wfMsg.value = '工作流启动失败，请稍后重试。'
    wfLoading.value = false
  }
}
</script>

<style scoped>
.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  gap: 20px;
  align-items: end;
}

.dashboard-hero__status {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px;
}

.dashboard-hero__status strong {
  font-size: 18px;
  line-height: 1.5;
}

.dashboard-hero__status small {
  color: var(--text-secondary);
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .dashboard-hero {
    grid-template-columns: 1fr;
  }
}
</style>
