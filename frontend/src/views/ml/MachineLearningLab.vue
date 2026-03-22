<template>
  <div class="page-shell">
    <section class="page-hero machine-hero">
      <div>
        <span class="page-eyebrow">Machine Learning Lab</span>
        <h2>把特征、标签、模型、调优和预测结果放到一个统一实验台里</h2>
        <p>
          第一版固定为日线同周期。训练窗口和预测窗口强制前后分离，避免未来数据泄漏；你可以在候选自变量里手工勾选，也可以让系统再做一轮特征筛选。
        </p>
      </div>

      <div class="hero-runtime glass-surface">
        <span class="section-tag">{{ options.cycle_label || '日线同周期' }}</span>
        <strong>{{ dateBoundsLabel }}</strong>
        <small>{{ runtimeHint }}</small>
      </div>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">实验配置</div>
            <div class="panel-subtitle">选择日期、自变量、因变量、模型和调优方式，然后直接输出预测结果。</div>
          </div>
          <span class="section-tag">{{ form.feature_columns.length }} 个候选特征</span>
        </div>
      </template>

      <el-form label-position="top" class="lab-form">
        <div class="form-grid">
          <el-form-item label="训练开始日期">
            <el-date-picker
              v-model="form.train_start_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>

          <el-form-item label="训练结束日期">
            <el-date-picker
              v-model="form.train_end_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>

          <el-form-item label="预测开始日期">
            <el-date-picker
              v-model="form.predict_start_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>

          <el-form-item label="预测结束日期">
            <el-date-picker
              v-model="form.predict_end_date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>

          <el-form-item label="因变量">
            <el-select v-model="form.label_column">
              <el-option
                v-for="item in options.label_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="模型方法">
            <el-select v-model="form.model_type">
              <el-option
                v-for="item in options.model_options"
                :key="item.value"
                :label="item.label"
                :value="item.value"
                :disabled="item.disabled"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="调优方式">
            <el-select v-model="form.tuning_method">
              <el-option
                v-for="item in filteredTuningOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
                :disabled="item.disabled"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="持有天数">
            <el-input-number v-model="form.hold_days" :min="1" :max="30" />
          </el-form-item>

          <el-form-item label="输出每日 Top N">
            <el-input-number v-model="form.prediction_top_n" :min="1" :max="100" />
          </el-form-item>

          <el-form-item label="最多保留特征">
            <el-input-number v-model="form.max_features" :min="1" :max="20" :disabled="!form.use_feature_selection" />
          </el-form-item>

          <el-form-item label="调优试验次数">
            <el-input-number
              v-model="form.tuning_trials"
              :min="5"
              :max="200"
              :disabled="form.tuning_method !== 'optuna'"
            />
          </el-form-item>

          <el-form-item label="自动筛特征">
            <el-switch v-model="form.use_feature_selection" />
          </el-form-item>
        </div>

        <el-form-item label="股票范围">
          <el-select
            v-model="form.symbols"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="留空则使用当前时间窗口内全部入库股票"
          >
            <el-option v-for="item in options.symbols" :key="item" :label="item" :value="item" />
          </el-select>
          <div class="field-hint">支持从已入库股票中选择，也支持手动输入新的 `ts_code`。</div>
        </el-form-item>

        <el-form-item label="候选自变量">
          <div class="feature-toolbar">
            <div class="feature-toolbar__actions">
              <el-button size="small" @click="selectAllFeatures">全选默认特征</el-button>
              <el-button size="small" @click="clearFeatures">清空选择</el-button>
            </div>
            <span class="feature-toolbar__count">已选 {{ form.feature_columns.length }} 个</span>
          </div>

          <el-checkbox-group v-model="form.feature_columns" class="feature-grid">
            <el-checkbox v-for="item in options.feature_options" :key="item.value" :label="item.value" class="feature-check">
              <div class="feature-option">
                <strong>{{ item.label }}</strong>
                <span>{{ item.description }}</span>
              </div>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <div class="status-strip">
          当前模型：<strong>{{ selectedModel?.label || '未选择' }}</strong>；
          当前调优：<strong>{{ selectedTuning?.label || '未选择' }}</strong>；
          周期：<strong>{{ options.cycle_label || '日线同周期' }}</strong>。
        </div>

        <div class="action-row">
          <el-button type="primary" :loading="loading" @click="runExperiment">运行实验</el-button>
          <el-button @click="applyDefaults">恢复默认</el-button>
        </div>
      </el-form>
    </el-card>

    <el-alert
      v-if="result?.error"
      :title="result.error"
      type="warning"
      show-icon
      :closable="false"
    />

    <template v-if="hasResult">
      <section class="metric-grid">
        <article class="metric-card glass-surface">
          <div class="metric-label">训练样本</div>
          <div class="metric-value">{{ result.sample_summary?.train_samples || 0 }}</div>
          <div class="metric-hint">训练窗口可用样本数</div>
        </article>
        <article class="metric-card glass-surface">
          <div class="metric-label">预测样本</div>
          <div class="metric-value">{{ result.sample_summary?.prediction_samples || 0 }}</div>
          <div class="metric-hint">预测窗口候选样本数</div>
        </article>
        <article class="metric-card glass-surface">
          <div class="metric-label">筛后特征</div>
          <div class="metric-value">{{ result.sample_summary?.selected_feature_count || 0 }}</div>
          <div class="metric-hint">最终参与训练的特征数量</div>
        </article>
        <article class="metric-card glass-surface">
          <div class="metric-label">输出结果</div>
          <div class="metric-value">{{ result.prediction_summary?.row_count || 0 }}</div>
          <div class="metric-hint">按每日 Top N 过滤后的预测记录</div>
        </article>
      </section>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">训练摘要</div>
              <div class="panel-subtitle">这里汇总样本区间、训练指标、验证指标和调优结果。</div>
            </div>
            <span class="section-tag">{{ selectedModel?.label || result.params?.model_type }}</span>
          </div>
        </template>

        <el-descriptions :column="3" border>
          <el-descriptions-item label="训练区间">
            {{ result.training_summary?.train_start_date }} ~ {{ result.training_summary?.train_end_date }}
          </el-descriptions-item>
          <el-descriptions-item label="预测区间">
            {{ result.training_summary?.predict_start_date }} ~ {{ result.training_summary?.predict_end_date }}
          </el-descriptions-item>
          <el-descriptions-item label="训练得分">
            {{ formatNumber(result.training_summary?.train_score, 4) }}
          </el-descriptions-item>
          <el-descriptions-item label="训练 RankIC">
            {{ formatNumber(result.training_summary?.train_metrics?.rank_ic, 4) }}
          </el-descriptions-item>
          <el-descriptions-item label="验证 RankIC">
            {{ formatNumber(result.training_summary?.validation_metrics?.rank_ic, 4) }}
          </el-descriptions-item>
          <el-descriptions-item label="方向准确率">
            {{ formatPercent(result.training_summary?.validation_metrics?.directional_accuracy) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="soft-divider"></div>

        <div class="result-tags">
          <el-tag effect="plain">调优方式 {{ result.tuning_summary?.method || 'none' }}</el-tag>
          <el-tag effect="plain">平均预测分 {{ formatNumber(result.prediction_summary?.avg_prediction_score, 4) }}</el-tag>
          <el-tag effect="plain">平均未来收益 {{ formatPercent(result.prediction_summary?.avg_future_return) }}</el-tag>
          <el-tag effect="plain">正收益占比 {{ formatPercent(result.prediction_summary?.positive_future_return_ratio) }}</el-tag>
        </div>

        <div v-if="bestParamTags.length" class="result-tags">
          <el-tag v-for="item in bestParamTags" :key="item.key" effect="plain" type="success">
            {{ item.key }} = {{ item.value }}
          </el-tag>
        </div>

        <div class="status-strip">{{ result.tuning_summary?.message || '本次未执行参数调优。' }}</div>
      </el-card>

      <section class="result-grid">
        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="panel-toolbar">
              <div class="panel-toolbar__copy">
                <div class="panel-title">特征筛选结果</div>
                <div class="panel-subtitle">展示候选特征的缺失率、波动和 IC 表现。</div>
              </div>
            </div>
          </template>

          <el-table :data="result.feature_stats || []" max-height="420">
            <el-table-column prop="feature" label="特征" min-width="140">
              <template #default="{ row }">{{ featureLabel(row.feature) }}</template>
            </el-table-column>
            <el-table-column label="缺失率" width="110">
              <template #default="{ row }">{{ formatPercent(row.missing_rate) }}</template>
            </el-table-column>
            <el-table-column label="标准差" width="110">
              <template #default="{ row }">{{ formatNumber(row.std, 4) }}</template>
            </el-table-column>
            <el-table-column label="RankIC" width="110">
              <template #default="{ row }">{{ formatNumber(row.ic, 4) }}</template>
            </el-table-column>
            <el-table-column prop="usable_samples" label="样本数" width="100" />
          </el-table>
        </el-card>

        <el-card class="panel-card" shadow="never">
          <template #header>
            <div class="panel-toolbar">
              <div class="panel-toolbar__copy">
                <div class="panel-title">模型权重 / 重要性</div>
                <div class="panel-subtitle">线性模型展示权重，树模型展示特征重要性。</div>
              </div>
            </div>
          </template>

          <el-table :data="result.model_weights || []" max-height="420">
            <el-table-column prop="feature_label" label="特征" min-width="160" />
            <el-table-column prop="feature" label="字段" min-width="140" />
            <el-table-column label="权重" width="120">
              <template #default="{ row }">{{ formatNumber(row.weight, 4) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </section>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">预测结果</div>
              <div class="panel-subtitle">按交易日内预测分排序，仅展示每日 Top N 的输出。</div>
            </div>
            <span class="section-tag">{{ result.predictions?.length || 0 }} 条结果</span>
          </div>
        </template>

        <el-table :data="result.predictions || []" max-height="520">
          <el-table-column prop="trade_date" label="信号日" width="110" fixed="left" />
          <el-table-column prop="ts_code" label="股票" width="120" />
          <el-table-column prop="daily_rank" label="日内排名" width="100" />
          <el-table-column label="预测分" width="110">
            <template #default="{ row }">{{ formatNumber(row.prediction_score, 4) }}</template>
          </el-table-column>
          <el-table-column label="实际标签" width="110">
            <template #default="{ row }">{{ formatNumber(row.actual_label, 4) }}</template>
          </el-table-column>
          <el-table-column label="未来收益" width="110">
            <template #default="{ row }">{{ formatPercent(row.future_return) }}</template>
          </el-table-column>
          <el-table-column label="未来超额" width="110">
            <template #default="{ row }">{{ formatPercent(row.future_excess_return) }}</template>
          </el-table-column>
          <el-table-column prop="buy_date" label="买入日" width="110" />
          <el-table-column prop="sell_date" label="卖出日" width="110" />
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { getMLExperimentOptions, runMLExperiment } from '../../api/index'

const loading = ref(false)
const options = ref({
  cycle_label: '日线同周期',
  date_bounds: {},
  symbols: [],
  feature_options: [],
  label_options: [],
  model_options: [],
  tuning_options: [],
  defaults: {},
  runtime: {},
})
const result = ref(null)
const form = ref(buildEmptyForm())

const dateBoundsLabel = computed(() => {
  const minDate = options.value.date_bounds?.min_date
  const maxDate = options.value.date_bounds?.max_date
  if (!minDate || !maxDate) {
    return '当前尚未检测到可用样本区间'
  }
  return `${minDate} ~ ${maxDate}`
})

const runtimeHint = computed(() => {
  if (!options.value.runtime?.sklearn_available) {
    return '当前环境未就绪，线性因子可正常使用，sklearn 模型会自动禁用。'
  }
  if (!options.value.runtime?.optuna_available) {
    return 'sklearn 已可用，Optuna 暂未安装，可先用网格搜索。'
  }
  return '线性因子、sklearn 和 Optuna 调优都已可用。'
})

const selectedModel = computed(() =>
  (options.value.model_options || []).find(item => item.value === form.value.model_type),
)
const selectedTuning = computed(() =>
  (options.value.tuning_options || []).find(item => item.value === form.value.tuning_method),
)
const bestParamTags = computed(() =>
  Object.entries(result.value?.tuning_summary?.best_params || {}).map(([key, value]) => ({
    key,
    value,
  })),
)
const filteredTuningOptions = computed(() => {
  const supportsTuning = selectedModel.value?.meta?.supports_tuning
  return (options.value.tuning_options || []).map(item => ({
    ...item,
    disabled: item.disabled || (item.value !== 'none' && !supportsTuning),
  }))
})
const hasResult = computed(() => Boolean(result.value && !result.value.error))

function buildEmptyForm() {
  return {
    symbols: [],
    feature_columns: [],
    label_column: 'future_excess_return',
    model_type: 'linear_factor',
    tuning_method: 'none',
    train_start_date: '',
    train_end_date: '',
    predict_start_date: '',
    predict_end_date: '',
    hold_days: 5,
    use_feature_selection: true,
    max_features: 8,
    prediction_top_n: 20,
    tuning_trials: 20,
  }
}

function applyDefaults() {
  const defaults = options.value.defaults || {}
  form.value = {
    ...buildEmptyForm(),
    ...defaults,
    symbols: Array.isArray(defaults.symbols) ? [...defaults.symbols] : [],
    feature_columns: Array.isArray(defaults.feature_columns) ? [...defaults.feature_columns] : [],
  }
}

function selectAllFeatures() {
  form.value.feature_columns = (options.value.feature_options || []).map(item => item.value)
}

function clearFeatures() {
  form.value.feature_columns = []
}

function featureLabel(feature) {
  return (options.value.feature_options || []).find(item => item.value === feature)?.label || feature
}

function formatNumber(value, precision = 2) {
  const numeric = Number(value || 0)
  return Number.isFinite(numeric) ? numeric.toFixed(precision) : '--'
}

function formatPercent(value, precision = 2) {
  const numeric = Number(value || 0)
  return `${(numeric * 100).toFixed(precision)}%`
}

async function loadOptions() {
  try {
    const response = await getMLExperimentOptions()
    options.value = response
    applyDefaults()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '机器学习实验配置加载失败')
  }
}

async function runExperiment() {
  if (!form.value.feature_columns.length) {
    ElMessage.warning('请至少选择一个自变量')
    return
  }
  if (!form.value.train_start_date || !form.value.train_end_date || !form.value.predict_start_date || !form.value.predict_end_date) {
    ElMessage.warning('请先完整选择训练区间和预测区间')
    return
  }

  loading.value = true
  result.value = null
  try {
    result.value = await runMLExperiment(form.value)
    if (result.value?.error) {
      ElMessage.warning(result.value.error)
    } else {
      ElMessage.success('机器学习实验已完成')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '机器学习实验运行失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => form.value.model_type,
  () => {
    const currentTuning = filteredTuningOptions.value.find(item => item.value === form.value.tuning_method)
    if (!currentTuning || currentTuning.disabled) {
      form.value.tuning_method = 'none'
    }
  },
)

onMounted(loadOptions)
</script>

<style scoped>
.machine-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(260px, 0.7fr);
  gap: 20px;
  align-items: start;
}

.hero-runtime {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 22px;
}

.hero-runtime strong {
  font-size: 18px;
}

.hero-runtime small,
.field-hint {
  color: var(--text-secondary);
  line-height: 1.7;
}

.lab-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px 16px;
}

.feature-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 12px;
}

.feature-toolbar__actions {
  display: flex;
  gap: 10px;
}

.feature-toolbar__count {
  color: var(--text-secondary);
  font-size: 12px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.feature-check {
  margin-right: 0;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.82);
}

.feature-option {
  display: flex;
  flex-direction: column;
  gap: 6px;
  white-space: normal;
}

.feature-option strong {
  color: var(--text-primary);
}

.feature-option span {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.action-row {
  display: flex;
  gap: 12px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

@media (max-width: 1200px) {
  .machine-hero,
  .form-grid,
  .result-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }

  .feature-toolbar,
  .action-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
