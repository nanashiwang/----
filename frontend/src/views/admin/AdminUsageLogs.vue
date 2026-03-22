<template>
  <div class="page-shell">
    <section class="page-hero admin-log-hero">
      <div>
        <span class="page-eyebrow">Admin Usage Logs</span>
        <h2>集中查看用户用了什么方法、跑了多少次，以及这些方法带来的收益表现</h2>
        <p>这块只对管理员开放。你可以按模块、用户和方法过滤，快速识别哪些模型、回测路径和因子方向更值得继续迭代。</p>
      </div>

      <div class="hero-runtime glass-surface">
        <span class="section-tag">Admin Only</span>
        <strong>{{ summary.latest_run_at || '暂无日志' }}</strong>
        <small>最近一次实验/回测记录时间</small>
      </div>
    </section>

    <section class="metric-grid">
      <article class="metric-card glass-surface">
        <div class="metric-label">日志总数</div>
        <div class="metric-value">{{ summary.total_runs || 0 }}</div>
        <div class="metric-hint">当前筛选条件下的运行记录</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">成功次数</div>
        <div class="metric-value">{{ summary.success_runs || 0 }}</div>
        <div class="metric-hint">成功产出结果的实验/回测</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">涉及用户</div>
        <div class="metric-value">{{ summary.unique_users || 0 }}</div>
        <div class="metric-hint">至少执行过一次的账号数量</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">主指标为正</div>
        <div class="metric-value">{{ summary.positive_primary_runs || 0 }}</div>
        <div class="metric-hint">主收益指标大于 0 的记录数</div>
      </article>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">筛选条件</div>
            <div class="panel-subtitle">按模块、用户、方法和状态缩小范围，方便管理员快速定位有效策略。</div>
          </div>
          <span class="section-tag">{{ logs.length }} 条记录</span>
        </div>
      </template>

      <div class="filter-grid">
        <el-select v-model="filters.module" clearable placeholder="选择模块">
          <el-option label="全部模块" value="" />
          <el-option label="机器学习实验" value="ml" />
          <el-option label="回测系统" value="backtest" />
        </el-select>

        <el-select v-model="filters.status" clearable placeholder="选择状态">
          <el-option label="全部状态" value="" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>

        <el-input v-model="filters.username" clearable placeholder="按用户名筛选" />
        <el-input v-model="filters.method" clearable placeholder="按方法名筛选" />

        <el-button type="primary" :loading="loading" @click="loadLogs">刷新日志</el-button>
      </div>
    </el-card>

    <section class="admin-log-grid">
      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">方法排名</div>
              <div class="panel-subtitle">按主指标均值排序，便于优先关注更稳的方法组合。</div>
            </div>
          </div>
        </template>

        <el-table :data="summary.method_rankings || []" size="small" stripe max-height="320">
          <el-table-column prop="name" label="方法" min-width="170" />
          <el-table-column prop="module_label" label="模块" width="120" />
          <el-table-column label="主指标" min-width="150">
            <template #default="{ row }">
              {{ row.metric_label || row.metric_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="均值" width="120">
            <template #default="{ row }">
              {{ formatMetric(row.avg_value, row.metric_name) }}
            </template>
          </el-table-column>
          <el-table-column label="最佳值" width="120">
            <template #default="{ row }">
              {{ formatMetric(row.best_value, row.metric_name) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">模块分布</div>
              <div class="panel-subtitle">查看机器学习与回测的使用占比和收益概况。</div>
            </div>
          </div>
        </template>

        <el-table :data="summary.module_breakdown || []" size="small" stripe max-height="320">
          <el-table-column prop="module_label" label="模块" min-width="140" />
          <el-table-column label="主指标" min-width="150">
            <template #default="{ row }">
              {{ row.metric_label || row.metric_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="run_count" label="次数" width="90" />
          <el-table-column label="均值" width="120">
            <template #default="{ row }">
              {{ formatMetric(row.avg_value, row.metric_name) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">详细日志</div>
            <div class="panel-subtitle">保留方法、区间、收益指标和参数摘要，方便后续复盘和提炼更好的因子。</div>
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" stripe max-height="560">
        <el-table-column prop="created_at" label="时间" min-width="170" />
        <el-table-column prop="username" label="用户" width="110" />
        <el-table-column prop="module_label" label="模块" width="130" />
        <el-table-column prop="method" label="方法" min-width="180" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" effect="light">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="主指标" min-width="180">
          <template #default="{ row }">
            <div class="metric-cell">
              <strong>{{ row.primary_metric_label || row.primary_metric_name || '-' }}</strong>
              <span>{{ formatMetric(row.primary_metric_value, row.primary_metric_name) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="辅助指标" min-width="180">
          <template #default="{ row }">
            <div class="metric-cell">
              <strong>{{ row.secondary_metric_label || row.secondary_metric_name || '-' }}</strong>
              <span>{{ formatMetric(row.secondary_metric_value, row.secondary_metric_name) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="区间" min-width="210">
          <template #default="{ row }">
            {{ row.date_range_start || '-' }} 至 {{ row.date_range_end || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="symbols_count" label="标的数" width="90" />
        <el-table-column label="操作" width="96" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="detailVisible" title="日志详情" size="42%">
      <template v-if="activeLog">
        <div class="detail-section">
          <div class="detail-title">基本信息</div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户">{{ activeLog.username }}</el-descriptions-item>
            <el-descriptions-item label="模块">{{ activeLog.module_label }}</el-descriptions-item>
            <el-descriptions-item label="动作">{{ activeLog.action_label }}</el-descriptions-item>
            <el-descriptions-item label="方法">{{ activeLog.method }}</el-descriptions-item>
            <el-descriptions-item label="时间">{{ activeLog.created_at }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ activeLog.status_label }}</el-descriptions-item>
            <el-descriptions-item v-if="activeLog.error_message" label="错误信息">
              {{ activeLog.error_message }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section">
          <div class="detail-title">参数摘要</div>
          <pre class="detail-json">{{ formatJson(activeLog.parameters) }}</pre>
        </div>

        <div class="detail-section">
          <div class="detail-title">结果摘要</div>
          <pre class="detail-json">{{ formatJson(activeLog.result_summary) }}</pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { getAdminUsageLogs } from '../../api/index'

const loading = ref(false)
const logs = ref([])
const summary = ref({
  total_runs: 0,
  success_runs: 0,
  failed_runs: 0,
  unique_users: 0,
  positive_primary_runs: 0,
  latest_run_at: '',
  method_rankings: [],
  module_breakdown: [],
})
const filters = ref({
  module: '',
  status: '',
  username: '',
  method: '',
})
const detailVisible = ref(false)
const activeLog = ref(null)

async function loadLogs() {
  loading.value = true
  try {
    const response = await getAdminUsageLogs({
      limit: 120,
      module: filters.value.module,
      status: filters.value.status,
      username: filters.value.username.trim(),
      method: filters.value.method.trim(),
    })
    logs.value = response.items || []
    summary.value = response.summary || summary.value
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '日志加载失败')
  } finally {
    loading.value = false
  }
}

function isPercentMetric(metricName = '') {
  return ['return', 'ratio', 'rate', 'drawdown'].some(keyword => metricName.includes(keyword))
}

function formatMetric(value, metricName = '') {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  if (isPercentMetric(metricName)) {
    return `${(Number(value) * 100).toFixed(2)}%`
  }
  return Number(value).toFixed(4)
}

function openDetail(row) {
  activeLog.value = row
  detailVisible.value = true
}

function formatJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2)
  } catch {
    return '{}'
  }
}

onMounted(loadLogs)
</script>

<style scoped>
.admin-log-hero {
  align-items: stretch;
}

.admin-log-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.metric-cell {
  display: grid;
  gap: 4px;
}

.metric-cell strong {
  color: rgba(245, 247, 255, 0.92);
  font-size: 12px;
  font-weight: 600;
}

.metric-cell span {
  color: rgba(245, 247, 255, 0.78);
  font-size: 13px;
}

.detail-section + .detail-section {
  margin-top: 20px;
}

.detail-title {
  margin-bottom: 10px;
  color: rgba(245, 247, 255, 0.88);
  font-size: 14px;
  font-weight: 700;
}

.detail-json {
  margin: 0;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  background: rgba(12, 18, 34, 0.74);
  color: rgba(245, 247, 255, 0.86);
  font-size: 12px;
  line-height: 1.7;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1080px) {
  .admin-log-grid {
    grid-template-columns: 1fr;
  }
}
</style>
