<template>
  <el-card header="回测系统" class="backtest-panel">
    <el-form :model="form" label-width="88px" class="backtest-form">
      <div class="backtest-form__grid">
        <el-form-item label="回测模式">
          <el-select v-model="form.mode">
            <el-option label="推荐复盘" value="review" />
            <el-option label="标准信号回测" value="portfolio" />
          </el-select>
        </el-form-item>

        <el-form-item label="开始日期">
          <el-date-picker v-model="form.start_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        </el-form-item>

        <el-form-item label="结束日期">
          <el-date-picker v-model="form.end_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        </el-form-item>

        <el-form-item label="持有天数">
          <el-input-number v-model="form.hold_days" :min="1" :max="30" />
        </el-form-item>

        <template v-if="form.mode === 'portfolio'">
          <el-form-item label="评分模型">
            <el-select v-model="form.model_type">
              <el-option label="线性因子" value="linear_factor" />
              <el-option label="Sklearn Ridge" value="sklearn_ridge" />
              <el-option label="双模型对照" value="compare" />
            </el-select>
          </el-form-item>

          <el-form-item label="每日持仓数">
            <el-input-number v-model="form.top_n" :min="1" :max="50" />
          </el-form-item>

          <el-form-item label="训练窗口">
            <el-input-number v-model="form.train_window_days" :min="30" :max="720" />
          </el-form-item>

          <el-form-item label="指标数量">
            <el-input-number v-model="form.max_features" :min="1" :max="20" />
          </el-form-item>

          <el-form-item label="手续费">
            <el-input-number v-model="form.fee_rate" :min="0" :max="0.02" :step="0.0001" :precision="4" />
          </el-form-item>

          <el-form-item label="滑点">
            <el-input-number
              v-model="form.slippage_rate"
              :min="0"
              :max="0.02"
              :step="0.0001"
              :precision="4"
            />
          </el-form-item>
        </template>
      </div>

      <el-form-item v-if="form.mode === 'portfolio'" label="股票池">
        <el-input
          v-model="form.symbols"
          type="textarea"
          :rows="2"
          placeholder="可选。留空则使用当前行情设置中的股票池，支持 000001.SZ,600519.SH 这种逗号分隔格式"
        />
      </el-form-item>

      <div class="backtest-actions">
        <el-button type="primary" :loading="loading" @click="run">运行回测</el-button>
      </div>

      <div class="backtest-tip">
        <template v-if="form.mode === 'portfolio'">
          标准信号回测会先在训练窗口里做指标筛选，再用你选择的评分模型打分；若切到“双模型对照”，系统会用相同特征同时跑线性因子和 Sklearn Ridge，便于直接比较。
        </template>
        <template v-else>
          推荐复盘保留原有逻辑，适合快速看已有 recommendations 记录在固定持有天数下的历史表现。
        </template>
      </div>
    </el-form>

    <template v-if="result">
      <el-divider />

      <el-alert v-if="result.error" :title="result.error" type="warning" show-icon />

      <template v-else-if="result.mode === 'portfolio'">
        <div class="result-tags">
          <el-tag effect="plain" type="primary">{{ modelLabel(result.model_type) }}</el-tag>
          <el-tag v-if="result.strategy_name" effect="plain">{{ result.strategy_name }}</el-tag>
        </div>

        <template v-if="result.model_type === 'compare'">
          <el-alert
            class="backtest-block"
            type="success"
            show-icon
            :closable="false"
            :title="`本轮对照实验胜出模型：${modelLabel(result.comparison_summary?.winner)}`"
            :description="`评估口径：${result.comparison_summary?.metric_label || '年化超额收益'}。正值代表 Ridge 相比线性因子更优。`"
          />

          <el-descriptions :column="3" border class="backtest-block">
            <el-descriptions-item label="训练区间">
              {{ result.training_summary?.train_start_date }} ~ {{ result.training_summary?.train_end_date }}
            </el-descriptions-item>
            <el-descriptions-item label="训练样本">
              {{ result.training_summary?.train_samples }}
            </el-descriptions-item>
            <el-descriptions-item label="测试样本">
              {{ result.training_summary?.test_samples }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="backtest-block">
            <div class="section-title">模型对照结果</div>
            <el-table :data="comparisonRows" size="small" stripe>
              <el-table-column prop="model_label" label="模型" min-width="160" />
              <el-table-column label="累计收益" width="120">
                <template #default="{ row }">{{ toPercent(row.cumulative_return) }}</template>
              </el-table-column>
              <el-table-column label="年化收益" width="120">
                <template #default="{ row }">{{ toPercent(row.annualized_return) }}</template>
              </el-table-column>
              <el-table-column label="年化超额" width="120">
                <template #default="{ row }">{{ toPercent(row.annualized_excess_return) }}</template>
              </el-table-column>
              <el-table-column label="最大回撤" width="120">
                <template #default="{ row }">{{ toPercent(row.max_drawdown) }}</template>
              </el-table-column>
              <el-table-column label="Sharpe" width="100">
                <template #default="{ row }">{{ toNumber(row.sharpe) }}</template>
              </el-table-column>
              <el-table-column label="胜率" width="100">
                <template #default="{ row }">{{ toPercent(row.win_rate) }}</template>
              </el-table-column>
              <el-table-column label="训练分数" width="100">
                <template #default="{ row }">{{ toNumber(row.train_score, 4) }}</template>
              </el-table-column>
            </el-table>
          </div>

          <div class="backtest-block">
            <div class="section-title">Ridge 相对线性因子的差值</div>
            <div class="tag-list">
              <el-tag effect="plain">累计收益 {{ signedPercent(result.comparison_summary?.deltas?.cumulative_return) }}</el-tag>
              <el-tag effect="plain">年化收益 {{ signedPercent(result.comparison_summary?.deltas?.annualized_return) }}</el-tag>
              <el-tag effect="plain">年化超额 {{ signedPercent(result.comparison_summary?.deltas?.annualized_excess_return) }}</el-tag>
              <el-tag effect="plain">最大回撤 {{ signedPercent(result.comparison_summary?.deltas?.max_drawdown) }}</el-tag>
              <el-tag effect="plain">Sharpe {{ signedNumber(result.comparison_summary?.deltas?.sharpe, 4) }}</el-tag>
            </div>
          </div>
        </template>

        <template v-else>
        <div class="metric-grid">
          <article class="metric-card">
            <span>总交易数</span>
            <strong>{{ portfolioSummary.trade_count }}</strong>
          </article>
          <article class="metric-card">
            <span>信号日数</span>
            <strong>{{ portfolioSummary.signal_days }}</strong>
          </article>
          <article class="metric-card">
            <span>胜率</span>
            <strong>{{ toPercent(portfolioSummary.win_rate) }}</strong>
          </article>
          <article class="metric-card">
            <span>累计收益</span>
            <strong>{{ toPercent(portfolioSummary.cumulative_return) }}</strong>
          </article>
          <article class="metric-card">
            <span>年化收益</span>
            <strong>{{ toPercent(portfolioSummary.annualized_return) }}</strong>
          </article>
          <article class="metric-card">
            <span>超额收益</span>
            <strong>{{ toPercent(portfolioSummary.excess_return) }}</strong>
          </article>
          <article class="metric-card">
            <span>最大回撤</span>
            <strong>{{ toPercent(portfolioSummary.max_drawdown) }}</strong>
          </article>
          <article class="metric-card">
            <span>Sharpe</span>
            <strong>{{ toNumber(portfolioSummary.sharpe) }}</strong>
          </article>
        </div>
        </template>

        <el-descriptions :column="3" border class="backtest-block">
          <el-descriptions-item label="训练区间">
            {{ result.training_summary?.train_start_date }} ~ {{ result.training_summary?.train_end_date }}
          </el-descriptions-item>
          <el-descriptions-item label="训练样本">
            {{ result.training_summary?.train_samples }}
          </el-descriptions-item>
          <el-descriptions-item label="测试样本">
            {{ result.training_summary?.test_samples }}
          </el-descriptions-item>
          <el-descriptions-item label="训练分数">
            {{ result.training_summary?.train_score == null ? '-' : toNumber(result.training_summary?.train_score, 4) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="backtest-block">
          <div class="section-title">已选指标</div>
          <div class="tag-list">
            <el-tag v-for="item in result.selected_features || []" :key="item" effect="plain">
              {{ item }}
            </el-tag>
          </div>
        </div>

        <div v-if="result.model_type === 'compare'" class="backtest-block">
          <div class="section-title">模型权重对照</div>
          <div class="comparison-grid">
            <article v-for="experiment in portfolioExperiments" :key="experiment.model_type" class="comparison-card">
              <div class="comparison-card__title">{{ modelLabel(experiment.model_type) }}</div>
              <el-table :data="experiment.model_weights || []" size="small" stripe max-height="320">
                <el-table-column prop="feature" label="指标" min-width="150" />
                <el-table-column label="权重" width="110">
                  <template #default="{ row }">
                    {{ toNumber(row.weight, 4) }}
                  </template>
                </el-table-column>
              </el-table>
            </article>
          </div>
        </div>

        <div v-else class="backtest-block">
          <div class="section-title">指标权重</div>
          <el-table :data="result.model_weights || []" size="small" stripe>
            <el-table-column prop="feature" label="指标" min-width="180" />
            <el-table-column label="权重" width="120">
              <template #default="{ row }">
                {{ toNumber(row.weight, 4) }}
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="result.model_type !== 'compare'" class="backtest-block">
          <div class="section-title">交易明细</div>
          <el-table :data="result.trades || []" size="small" stripe max-height="420">
            <el-table-column prop="signal_date" label="信号日" width="110" />
            <el-table-column prop="buy_date" label="买入日" width="110" />
            <el-table-column prop="sell_date" label="卖出日" width="110" />
            <el-table-column prop="ts_code" label="股票" width="120" />
            <el-table-column label="分数" width="100">
              <template #default="{ row }">
                {{ toNumber(row.score, 4) }}
              </template>
            </el-table-column>
            <el-table-column label="仓位" width="100">
              <template #default="{ row }">
                {{ toPercent(row.weight) }}
              </template>
            </el-table-column>
            <el-table-column label="净收益" width="120">
              <template #default="{ row }">
                <span :class="row.net_return >= 0 ? 'is-up' : 'is-down'">
                  {{ toPercent(row.net_return) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>

      <template v-else>
        <div class="metric-grid metric-grid--review">
          <article class="metric-card">
            <span>总交易次数</span>
            <strong>{{ result.total_trades }}</strong>
          </article>
          <article class="metric-card">
            <span>胜率</span>
            <strong>{{ toPercent(result.win_rate) }}</strong>
          </article>
          <article class="metric-card">
            <span>平均收益</span>
            <strong>{{ toPercent(result.avg_return) }}</strong>
          </article>
          <article class="metric-card">
            <span>最大收益</span>
            <strong>{{ toPercent(result.max_return) }}</strong>
          </article>
        </div>

        <el-table v-if="result.details" :data="result.details" size="small" stripe>
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column prop="ts_code" label="股票" width="120" />
          <el-table-column prop="weight" label="权重" width="100" />
          <el-table-column label="收益率" width="120">
            <template #default="{ row }">
              <span :class="row.return_rate >= 0 ? 'is-up' : 'is-down'">
                {{ toPercent(row.return_rate) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </template>
  </el-card>
</template>

<script setup>
import { computed, ref } from 'vue'
import { runBacktest } from '../../api/index'
import dayjs from 'dayjs'

const modelLabelMap = {
  linear_factor: '线性因子',
  sklearn_ridge: 'Sklearn Ridge',
  compare: '双模型对照',
}

const form = ref({
  mode: 'portfolio',
  model_type: 'linear_factor',
  start_date: dayjs().subtract(120, 'day').format('YYYY-MM-DD'),
  end_date: dayjs().subtract(5, 'day').format('YYYY-MM-DD'),
  hold_days: 5,
  top_n: 5,
  train_window_days: 120,
  max_features: 6,
  fee_rate: 0.0005,
  slippage_rate: 0.0005,
  symbols: '',
})
const result = ref(null)
const loading = ref(false)

const portfolioSummary = computed(() => result.value?.summary || {})
const portfolioExperiments = computed(() => result.value?.experiments || [])
const comparisonRows = computed(() =>
  (result.value?.experiments || []).map(item => ({
    model_type: item.model_type,
    model_label: modelLabel(item.model_type),
    cumulative_return: item.summary?.cumulative_return || 0,
    annualized_return: item.summary?.annualized_return || 0,
    annualized_excess_return: item.summary?.annualized_excess_return || 0,
    max_drawdown: item.summary?.max_drawdown || 0,
    sharpe: item.summary?.sharpe || 0,
    win_rate: item.summary?.win_rate || 0,
    train_score: item.training_summary?.train_score || 0,
  })),
)

function modelLabel(modelType) {
  return modelLabelMap[modelType] || modelType || '未知模型'
}

function toPercent(value, precision = 2) {
  const numeric = Number(value || 0)
  return `${(numeric * 100).toFixed(precision)}%`
}

function signedPercent(value, precision = 2) {
  const numeric = Number(value || 0)
  return `${numeric >= 0 ? '+' : ''}${(numeric * 100).toFixed(precision)}%`
}

function toNumber(value, precision = 2) {
  const numeric = Number(value || 0)
  return numeric.toFixed(precision)
}

function signedNumber(value, precision = 2) {
  const numeric = Number(value || 0)
  return `${numeric >= 0 ? '+' : ''}${numeric.toFixed(precision)}`
}

async function run() {
  loading.value = true
  result.value = null
  try {
    result.value = await runBacktest(form.value)
  } catch {
    result.value = { error: '请求失败' }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.backtest-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.backtest-form__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px 16px;
}

.backtest-actions {
  display: flex;
  gap: 12px;
}

.backtest-tip {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.metric-grid--review {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(120, 148, 180, 0.2);
  background: rgba(255, 255, 255, 0.72);
}

.metric-card span {
  color: var(--text-secondary);
  font-size: 12px;
}

.metric-card strong {
  color: var(--text-primary);
  font-size: 20px;
}

.backtest-block {
  margin-top: 18px;
}

.section-title {
  margin-bottom: 10px;
  color: var(--text-primary);
  font-weight: 600;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.comparison-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(120, 148, 180, 0.2);
  background: rgba(255, 255, 255, 0.72);
}

.comparison-card__title {
  margin-bottom: 12px;
  color: var(--text-primary);
  font-weight: 600;
}

.is-up {
  color: #1f9d62;
}

.is-down {
  color: #d04e4e;
}

@media (max-width: 960px) {
  .backtest-form__grid,
  .metric-grid,
  .metric-grid--review,
  .comparison-grid {
    grid-template-columns: 1fr;
  }
}
</style>
