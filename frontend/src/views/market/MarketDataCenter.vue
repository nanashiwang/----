<template>
  <div class="page-shell">
    <section class="page-hero">
      <div>
        <span class="page-eyebrow">Market Data Center</span>
        <h2>把股票池行情、指标和资金流向放到一个更顺手的工作台里</h2>
        <p>按股票查看拉回来的历史数据，结合图表趋势和明细表格，快速确认同步是否正常、指标是否完整。</p>
      </div>
      <div class="hero-runtime glass-surface">
        <span class="section-tag">Last Sync</span>
        <strong>{{ runtime.last_sync_at || '尚未同步' }}</strong>
        <small>{{ runtime.last_sync_message || '先到 Tushare 配置页保存股票池并执行一次同步。' }}</small>
      </div>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">查询条件</div>
            <div class="panel-subtitle">选择股票和时间区间后刷新，下方图表和表格会联动更新。</div>
          </div>
          <span class="section-tag">{{ dataTypesLabel }}</span>
        </div>
      </template>

      <div class="filter-grid">
        <el-select v-model="filters.ts_code" placeholder="选择股票" clearable>
          <el-option v-for="item in symbols" :key="item" :label="item" :value="item" />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
        />

        <el-button type="primary" @click="loadOverview" :loading="loading">刷新数据</el-button>
      </div>
    </el-card>

    <section class="metric-grid market-metric-grid">
      <article class="metric-card glass-surface">
        <div class="metric-label">最新收盘价</div>
        <div class="metric-value">{{ formatNumber(latestSummary.close) }}</div>
        <div class="metric-hint">{{ latestSummary.trade_date || '暂无数据' }}</div>
      </article>

      <article class="metric-card glass-surface metric-card--accent">
        <div class="metric-label">主基准</div>
        <div class="metric-value metric-value--compact">{{ benchmarkSummary.name || primaryBenchmark || '--' }}</div>
        <div class="metric-hint">{{ benchmarkSummary.index_code || primaryBenchmark || '未配置' }}</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">基准收盘 / 涨跌</div>
        <div class="metric-value">{{ formatBenchmarkSnapshot(benchmarkSummary.close, benchmarkSummary.pct_chg) }}</div>
        <div class="metric-hint">{{ benchmarkSummary.trade_date || '暂无数据' }}</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">PE / PB</div>
        <div class="metric-value">{{ formatPair(latestSummary.pe, latestSummary.pb) }}</div>
        <div class="metric-hint">基础指标快照</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">换手率</div>
        <div class="metric-value">{{ formatNumber(latestSummary.turnover_rate) }}</div>
        <div class="metric-hint">最新一日日线基础指标</div>
      </article>

      <article class="metric-card glass-surface">
        <div class="metric-label">净流入额</div>
        <div class="metric-value">{{ formatNumber(latestSummary.net_mf_amount) }}</div>
        <div class="metric-hint">资金流向数据</div>
      </article>
    </section>

    <section class="market-grid">
      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">价格趋势</div>
              <div class="panel-subtitle">默认展示收盘价与成交量双轴趋势，用来快速判断同步结果是否连续。</div>
            </div>
            <span class="section-tag">{{ records.length }} 条记录</span>
          </div>
        </template>

        <div v-if="priceSeries.length" class="chart-shell">
          <VChart :option="chartOption" autoresize class="market-chart" />
        </div>
        <el-empty v-else description="当前股票暂无可视化数据" />
      </el-card>

      <el-card class="panel-card" shadow="never">
        <template #header>
          <div class="panel-toolbar">
            <div class="panel-toolbar__copy">
              <div class="panel-title">最新快照</div>
              <div class="panel-subtitle">表格会合并日线、基础指标和资金流向，便于核对每个交易日的完整性。</div>
            </div>
            <span class="section-tag">{{ filters.ts_code || '未选择' }}</span>
          </div>
        </template>

        <el-table :data="records" v-loading="loading" max-height="520">
          <el-table-column prop="trade_date" label="日期" width="110" fixed="left" />
          <el-table-column prop="close" label="收盘" width="100" />
          <el-table-column prop="open" label="开盘" width="100" />
          <el-table-column prop="high" label="最高" width="100" />
          <el-table-column prop="low" label="最低" width="100" />
          <el-table-column prop="volume" label="成交量" min-width="120" />
          <el-table-column prop="amount" label="成交额" min-width="120" />
          <el-table-column prop="turnover_rate" label="换手率" width="110" />
          <el-table-column prop="pe" label="PE" width="100" />
          <el-table-column prop="pb" label="PB" width="100" />
          <el-table-column prop="net_mf_amount" label="净流入额" min-width="120" />
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import { getMarketDataOverview } from '../../api/index'

use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

const datasetLabelMap = {
  daily: '日线行情',
  daily_basic: '基础指标',
  moneyflow: '资金流向',
  top_list: '龙虎榜',
  index_daily: '大盘指数',
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
const filters = ref({
  ts_code: '',
})

const dataTypesLabel = computed(() => {
  if (!dataTypes.value.length) {
    return '未配置数据类型'
  }
  return dataTypes.value.map(item => datasetLabelMap[item] || item).join(' / ')
})

const chartOption = computed(() => ({
  tooltip: {
    trigger: 'axis',
  },
  legend: {
    data: ['收盘价', '成交量'],
  },
  grid: {
    left: 28,
    right: 24,
    top: 48,
    bottom: 26,
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: priceSeries.value.map(item => item.trade_date),
    boundaryGap: false,
  },
  yAxis: [
    {
      type: 'value',
      name: '收盘价',
      scale: true,
    },
    {
      type: 'value',
      name: '成交量',
      scale: true,
    },
  ],
  series: [
    {
      name: '收盘价',
      type: 'line',
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 3, color: '#1e7cf2' },
      areaStyle: { color: 'rgba(30,124,242,0.12)' },
      data: priceSeries.value.map(item => item.close),
    },
    {
      name: '成交量',
      type: 'bar',
      yAxisIndex: 1,
      itemStyle: { color: 'rgba(43,195,177,0.55)' },
      data: priceSeries.value.map(item => item.volume),
    },
  ],
}))

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

async function loadOverview() {
  loading.value = true
  try {
    const result = await getMarketDataOverview({
      ts_code: filters.value.ts_code || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      limit: 180,
    })
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
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
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

@media (max-width: 1100px) {
  .market-grid,
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
