<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <span class="page-eyebrow">Market Data Center</span>
        <h2>??????????????????????????</h2>
        <p>????????????????????????????????????????????</p>
      </div>
      <div class="hero-runtime glass-surface">
        <span class="section-tag">Last Sync</span>
        <strong>{{ runtime.last_sync_at || '????' }}</strong>
        <small>{{ runtime.last_sync_message || '?? Tushare ????????????????' }}</small>
      </div>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">????</div>
            <div class="panel-subtitle">??????????????????????????</div>
          </div>
          <span class="section-tag">{{ dataTypesLabel }}</span>
        </div>
      </template>

      <div class="filter-grid">
        <el-select v-model="filters.ts_code" placeholder="????" clearable>
          <el-option v-for="item in symbols" :key="item" :label="item" :value="item" />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="?"
          start-placeholder="????"
          end-placeholder="????"
          value-format="YYYY-MM-DD"
        />

        <el-button type="primary" @click="handleRefresh" :loading="loading">????</el-button>
      </div>
    </el-card>

    <section class="metric-grid market-metric-grid">
      <article class="metric-card glass-surface">
        <div class="metric-label">?????</div>
        <div class="metric-value">{{ formatNumber(latestSummary.close) }}</div>
        <div class="metric-hint">{{ latestSummary.trade_date || '????' }}</div>
      </article>

      <article class="metric-card glass-surface metric-card--accent">
        <div class="metric-label">???</div>
        <div class="metric-value metric-value--compact">{{ benchmarkSummary.name || primaryBenchmark || '--' }}</div>
        <div class="metric-hint">{{ benchmarkSummary.index_code || primaryBenchmark || '???' }}</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">???? / ??</div>
        <div class="metric-value">{{ formatBenchmarkSnapshot(benchmarkSummary.close, benchmarkSummary.pct_chg) }}</div>
        <div class="metric-hint">{{ benchmarkSummary.trade_date || '????' }}</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">PE / PB</div>
        <div class="metric-value">{{ formatPair(latestSummary.pe, latestSummary.pb) }}</div>
        <div class="metric-hint">??????</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">???</div>
        <div class="metric-value">{{ formatNumber(latestSummary.turnover_rate) }}</div>
        <div class="metric-hint">??????????</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">????</div>
        <div class="metric-value">{{ formatNumber(latestSummary.net_mf_amount) }}</div>
        <div class="metric-hint">??????</div>
      </article>
    </section>

    <section class="market-grid">
      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">????</div>
              <div class="panel-subtitle">?????????????????????????</div>
            </div>
            <span class="section-tag">{{ records.length }} ???</span>
          </div>
        </template>

        <div v-if="priceSeries.length" class="chart-shell">
          <component :is="MarketTrendChart" v-if="showTrendChart" :price-series="priceSeries" class="market-chart" />
          <div v-else class="chart-placeholder glass-surface">
            <span>?????????????????????</span>
          </div>
        </div>
        <el-empty v-else description="???????????" />
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">????</div>
              <div class="panel-subtitle">????????????????????????????????</div>
            </div>
            <span class="section-tag">{{ filters.ts_code || '???' }}</span>
          </div>
        </template>

        <el-table :data="records" v-loading="loading" max-height="520">
          <el-table-column prop="trade_date" label="??" width="110" fixed="left" />
          <el-table-column prop="close" label="??" width="100" />
          <el-table-column prop="open" label="??" width="100" />
          <el-table-column prop="high" label="??" width="100" />
          <el-table-column prop="low" label="??" width="100" />
          <el-table-column prop="volume" label="???" min-width="120" />
          <el-table-column prop="amount" label="???" min-width="120" />
          <el-table-column prop="turnover_rate" label="???" width="110" />
          <el-table-column prop="pe" label="PE" width="100" />
          <el-table-column prop="pb" label="PB" width="100" />
          <el-table-column prop="net_mf_amount" label="????" min-width="120" />
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onActivated, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { getMarketDataOverview } from '../../api/index'

const INITIAL_RECORD_LIMIT = 90
const OVERVIEW_CACHE_TTL = 2 * 60 * 1000
const overviewCache = new Map()

const MarketTrendChart = defineAsyncComponent({
  loader: () => import('../../components/market/MarketTrendChart.vue'),
  suspensible: false,
})

const datasetLabelMap = {
  daily: '????',
  daily_basic: '????',
  moneyflow: '????',
  top_list: '???',
  index_daily: '????',
}

const loading = ref(false)
const symbols = ref([])
const dateRange = ref([])
const dataTypes = ref([])
const records = ref([])
const priceSeries = ref([])
const latestSummary = ref({})
const benchmarkSummary = ref({})
const primaryBenchmark = ref('')
const runtime = ref({})
const showTrendChart = ref(false)
const filters = ref({
  ts_code: '',
})

const dataTypesLabel = computed(() => {
  if (!dataTypes.value.length) {
    return '???????'
  }
  return dataTypes.value.map(item => datasetLabelMap[item] || item).join(' / ')
})

function buildOverviewParams(limit = INITIAL_RECORD_LIMIT) {
  return {
    ts_code: filters.value.ts_code || undefined,
    start_date: dateRange.value?.[0] || undefined,
    end_date: dateRange.value?.[1] || undefined,
    limit,
  }
}

function buildCacheKey(params) {
  return JSON.stringify({
    ts_code: params.ts_code || '',
    start_date: params.start_date || '',
    end_date: params.end_date || '',
    limit: params.limit,
  })
}

function readOverviewCache(params) {
  const cacheKey = buildCacheKey(params)
  const entry = overviewCache.get(cacheKey)
  if (!entry) {
    return null
  }
  if (Date.now() - entry.timestamp > OVERVIEW_CACHE_TTL) {
    overviewCache.delete(cacheKey)
    return null
  }
  return entry.payload
}

function writeOverviewCache(params, payload) {
  overviewCache.set(buildCacheKey(params), {
    timestamp: Date.now(),
    payload,
  })
}

function scheduleChartRender() {
  showTrendChart.value = false
  if (!priceSeries.value.length) {
    return
  }

  const render = () => {
    showTrendChart.value = true
  }

  if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
    window.requestIdleCallback(render, { timeout: 300 })
    return
  }

  if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
    window.requestAnimationFrame(render)
    return
  }

  render()
}

function applyOverview(result) {
  symbols.value = result.symbols || []
  dataTypes.value = result.data_types || []
  records.value = result.records || []
  priceSeries.value = result.price_series || []
  latestSummary.value = result.latest_summary || {}
  benchmarkSummary.value = result.benchmark_summary || {}
  primaryBenchmark.value = result.primary_benchmark || ''
  runtime.value = result.runtime || {}

  if (!filters.value.ts_code && result.ts_code) {
    filters.value.ts_code = result.ts_code
  }

  scheduleChartRender()
}

function formatNumber(value) {
  if (value === null || value === undefined || value === '') {
    return '--'
  }
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed.toFixed(2) : value
}

function formatPair(left, right) {
  if (left === null || left === undefined || right === null || right === undefined) {
    return '--'
  }
  return `${formatNumber(left)} / ${formatNumber(right)}`
}

function formatBenchmarkSnapshot(close, pctChg) {
  if (close === null || close === undefined || close === '') {
    return '--'
  }
  const closeText = formatNumber(close)
  if (pctChg === null || pctChg === undefined || pctChg === '') {
    return closeText
  }
  return `${closeText} / ${formatNumber(pctChg)}%`
}

async function loadOverview(options = {}) {
  const params = buildOverviewParams(options.limit)
  const useCache = options.useCache !== false
  const cached = useCache ? readOverviewCache(params) : null

  if (cached) {
    applyOverview(cached)
    return cached
  }

  loading.value = true
  try {
    const result = await getMarketDataOverview(params)
    applyOverview(result)
    writeOverviewCache(params, result)
    return result
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '?????????????????????')
    throw error
  } finally {
    loading.value = false
  }
}

function safeLoadOverview(options = {}) {
  return loadOverview(options).catch(() => null)
}

function handleRefresh() {
  void safeLoadOverview({ useCache: false })
}

onMounted(() => {
  void safeLoadOverview()
})

onActivated(() => {
  if (!records.value.length && !loading.value) {
    void safeLoadOverview()
    return
  }
  scheduleChartRender()
})
</script>

<style scoped>
.hero-runtime {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 22px;
  min-width: 300px;
}

.hero-runtime strong {
  font-size: 18px;
}

.hero-runtime small {
  color: var(--text-secondary);
  line-height: 1.6;
}

.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1.2fr auto;
  gap: 14px;
  align-items: center;
}

.market-metric-grid {
  margin-top: 20px;
}

.metric-card--accent {
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.82), rgba(238, 246, 255, 0.68)),
    radial-gradient(circle at top right, rgba(40, 112, 204, 0.14), transparent 56%);
}

.metric-value--compact {
  font-size: 24px;
}

.market-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.25fr);
  gap: 20px;
}

.chart-shell {
  height: 380px;
}

.market-chart {
  height: 100%;
}

.chart-placeholder {
  display: grid;
  place-items: center;
  height: 100%;
  border-radius: var(--radius-xl);
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}

@media (max-width: 1100px) {
  .market-grid,
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
