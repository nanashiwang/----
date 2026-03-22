<template>
  <div class="page-shell">
    <section class="page-hero page-hero--compact">
      <span class="page-eyebrow">Data Source Access</span>
      <h2>Tushare 配置</h2>
      <p>统一维护 Tushare 接入参数、行情拉取策略与手动同步状态，让连接、调度、补数和进度展示放在同一处完成。</p>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">连接参数</div>
            <div class="panel-subtitle">用于校验 Tushare 授权与自定义网关，影响所有行情数据调用入口。</div>
          </div>
          <span class="section-tag">Tushare Pro</span>
        </div>
      </template>

      <el-form :model="connectionForm" label-width="120px" class="settings-form">
        <el-form-item label="Token">
          <el-input
            v-model="connectionForm.token"
            type="password"
            show-password
            :placeholder="tokenPlaceholder"
          />
        </el-form-item>

        <el-form-item label="API URL">
          <el-input
            v-model="connectionForm.api_url"
            placeholder="http://121.40.135.59:8010/"
          />
          <div class="settings-tip">
            如果你的接入方式依赖 <code>pro._DataApi__http_url</code>，请在这里填入对应的代理地址。
          </div>
        </el-form-item>

        <el-form-item>
          <div class="settings-actions">
            <el-button type="primary" :loading="connectionSaving" @click="saveConnectionSettings">
              保存连接配置
            </el-button>
            <el-button :loading="testing" @click="testConnection">
              测试连接
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="testResult"
        :title="testResult.message"
        :type="testResult.success ? 'success' : 'error'"
        show-icon
      />
    </el-card>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">行情拉取策略</div>
            <div class="panel-subtitle">把日常增量和历史补数分开管理，同时支持快捷范围、立即拉取和实时进度查看。</div>
          </div>
          <span class="section-tag">Sync Policy</span>
        </div>
      </template>

      <el-form :model="marketForm" label-width="120px" class="settings-form">
        <el-form-item label="全市场检索">
          <div class="stock-search-panel">
            <div class="stock-search-toolbar">
              <el-select
                v-model="stockSearchSelection"
                class="stock-search-select"
                multiple
                filterable
                remote
                reserve-keyword
                collapse-tags
                collapse-tags-tooltip
                default-first-option
                placeholder="输入股票代码、简称或 ts_code，直接从全市场搜索"
                :remote-method="handleStockSearch"
                :loading="stockSearchLoading"
                @visible-change="handleStockSearchVisibleChange"
              >
                <el-option
                  v-for="item in stockSearchResults"
                  :key="item.ts_code"
                  :label="formatStockOptionLabel(item)"
                  :value="item.ts_code"
                  :disabled="isStockInPool(item.ts_code)"
                >
                  <div class="stock-option">
                    <div class="stock-option__main">
                      <strong>{{ item.name || item.ts_code }}</strong>
                      <span>{{ item.ts_code }}</span>
                    </div>
                    <div class="stock-option__meta">
                      <div class="stock-option__badges">
                        <el-tag v-if="item.market" size="small" effect="plain">{{ item.market }}</el-tag>
                        <el-tag v-if="item.industry" size="small" effect="plain">{{ item.industry }}</el-tag>
                        <el-tag v-if="item.area" size="small" effect="plain">{{ item.area }}</el-tag>
                        <el-tag v-if="isStockInPool(item.ts_code)" size="small" type="success">已在股票池中</el-tag>
                      </div>
                    </div>
                  </div>
                </el-option>
              </el-select>
            </div>

            <div class="stock-filter-grid">
              <el-select
                v-model="stockMarketFilter"
                class="stock-market-filter"
                placeholder="全部板块"
                clearable
                @change="handleStockMarketChange"
              >
                <el-option label="全部板块" value="" />
                <el-option
                  v-for="item in stockMarketOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>

              <el-select
                v-model="stockIndustryFilter"
                class="stock-market-filter"
                placeholder="全部行业"
                clearable
                filterable
                @change="handleStockIndustryChange"
              >
                <el-option label="全部行业" value="" />
                <el-option
                  v-for="item in stockIndustryOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>

              <el-select
                v-model="stockAreaFilter"
                class="stock-market-filter"
                placeholder="全部地区"
                clearable
                filterable
                @change="handleStockAreaChange"
              >
                <el-option label="全部地区" value="" />
                <el-option
                  v-for="item in stockAreaOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </div>

            <div class="stock-search-actions">
              <el-button plain :disabled="!stockSearchSelection.length" @click="addSelectedStocksToPool">
                加入选中股票
              </el-button>
              <el-button plain :disabled="!stockSearchResults.length" @click="addSearchResultsToPool">
                加入当前显示结果
              </el-button>
              <el-button
                plain
                :loading="addingFilteredStocks"
                @click="addAllFilteredStocksToPool"
              >
                批量加入全部筛选结果
              </el-button>
              <el-button text @click="refreshStockCatalog">
                刷新股票列表
              </el-button>
            </div>

            <div class="settings-tip">
              当前匹配 {{ stockSearchTotal }} 条结果。可以按板块、行业、地区进一步筛选，再批量加入股票池，省去逐个录入代码的麻烦。
            </div>
            <div class="settings-tip">
              “批量加入全部筛选结果”只会填充股票池，不会自动开始同步；股票数量越多，后续补数和增量同步耗时会越长。
            </div>
          </div>
        </el-form-item>

        <el-form-item label="股票池">
          <div class="stock-pool-panel">
            <div class="stock-pool-toolbar">
              <el-input
                v-model="manualPoolInput"
                placeholder="手动补充股票，支持一次粘贴多个代码，用逗号或换行分隔"
                @keyup.enter="addManualSymbolsToPool"
              />
              <el-button plain @click="addManualSymbolsToPool">
                手动加入
              </el-button>
              <el-button text :disabled="poolStockItems.length < 2" @click="sortPoolSymbolsByCode">
                按代码排序
              </el-button>
            </div>

            <div class="stock-pool-summary">
              <span>当前股票池共 {{ poolStockItems.length }} 只股票</span>
              <small>标签式管理支持上移、下移和移除，保存时会按当前顺序写入配置。</small>
            </div>

            <div v-if="poolStockItems.length" class="stock-pool-grid">
              <article v-for="item in poolStockItems" :key="item.ts_code" class="stock-pool-card glass-surface">
                <div class="stock-pool-card__copy">
                  <strong>{{ item.name || item.ts_code }}</strong>
                  <span>{{ item.ts_code }}</span>
                </div>
                <div class="stock-pool-card__meta">
                  <el-tag v-if="item.market" size="small" effect="plain">{{ item.market }}</el-tag>
                  <el-tag v-if="item.industry" size="small" effect="plain">{{ item.industry }}</el-tag>
                  <el-tag v-if="item.area" size="small" effect="plain">{{ item.area }}</el-tag>
                </div>
                <div class="stock-pool-card__actions">
                  <el-button text size="small" :disabled="item.index === 0" @click="movePoolSymbol(item.index, -1)">
                    上移
                  </el-button>
                  <el-button
                    text
                    size="small"
                    :disabled="item.index === poolStockItems.length - 1"
                    @click="movePoolSymbol(item.index, 1)"
                  >
                    下移
                  </el-button>
                  <el-button text size="small" type="danger" @click="removePoolSymbol(item.ts_code)">
                    移除
                  </el-button>
                </div>
              </article>
            </div>
            <el-empty v-else description="还没有加入任何股票，先从上面的全市场检索里选择一些标的吧。" />
          </div>

          <div class="settings-tip">支持英文逗号、中文逗号或换行分隔；如果只填 6 位代码，系统会自动补全为 `.SH/.SZ/.BJ`。</div>
          <el-alert
            v-if="symbolValidation.invalidSymbols.length"
            class="settings-alert"
            type="error"
            show-icon
            :closable="false"
            :title="`发现 ${symbolValidation.invalidSymbols.length} 个股票代码格式不正确`"
            :description="`请改为 6 位数字，或使用 000001.SZ / 600519.SH / 430047.BJ 这类完整代码。当前异常值：${symbolValidation.invalidSymbols.join('、')}`"
          />
          <el-alert
            v-else-if="symbolValidation.normalizedPreview"
            class="settings-alert"
            type="info"
            show-icon
            :closable="false"
            title="股票代码会按交易所规则自动规范化"
            :description="`保存后将按以下代码执行拉取：${symbolValidation.normalizedPreview}`"
          />
        </el-form-item>

        <el-form-item label="大盘基准">
          <div class="benchmark-panel">
            <div class="benchmark-panel__header">
              <div>
                <div class="benchmark-panel__title">A 股基准指数同步</div>
                <div class="benchmark-panel__desc">
                  这些指数会一并拉取到本地，用来做大盘对比、超额收益计算和机器学习训练时的基准参考。
                </div>
              </div>

              <el-select
                v-model="marketForm.primary_benchmark"
                class="benchmark-primary-select"
                placeholder="选择主基准"
                @change="handlePrimaryBenchmarkChange"
              >
                <el-option
                  v-for="item in benchmarkOptions"
                  :key="item.code"
                  :label="`${item.label} / ${item.code}`"
                  :value="item.code"
                />
              </el-select>
            </div>

            <el-select
              v-model="marketForm.benchmark_index_codes"
              class="benchmark-code-select"
              multiple
              filterable
              allow-create
              default-first-option
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择或输入要同步的大盘指数 ts_code"
              @change="handleBenchmarkCodesChange"
            >
              <el-option
                v-for="item in benchmarkOptions"
                :key="item.code"
                :label="`${item.label} / ${item.code}`"
                :value="item.code"
              />
            </el-select>

            <div class="benchmark-panel__summary">
              当前已选 {{ marketForm.benchmark_index_codes.length }} 个指数，主基准会优先用于特征构建和超额收益标签。
            </div>
            <div class="settings-tip">
              默认预置上证指数、深证成指、创业板指、沪深300、中证500、中证1000、科创50，也支持手动补充其它指数 ts_code。
            </div>

            <el-alert
              v-if="benchmarkValidation.invalidSymbols.length"
              class="settings-alert"
              type="error"
              show-icon
              :closable="false"
              :title="`发现 ${benchmarkValidation.invalidSymbols.length} 个大盘指数代码格式不正确`"
              :description="`请改为 6 位数字，或使用 000300.SH / 399001.SZ 这类完整代码。当前异常值：${benchmarkValidation.invalidSymbols.join('、')}`"
            />
            <el-alert
              v-else-if="benchmarkValidation.normalizedPreview"
              class="settings-alert"
              type="info"
              show-icon
              :closable="false"
              title="大盘指数代码会按交易所规则自动规范化"
              :description="`保存后将按以下代码执行拉取：${benchmarkValidation.normalizedPreview}`"
            />
          </div>
        </el-form-item>

        <el-form-item label="拉取信息">
          <el-checkbox-group v-model="marketForm.data_types" class="checkbox-grid">
            <el-checkbox v-for="item in datasetOptions" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
          <div class="settings-tip">日线行情适合画图，基础指标和资金流向适合表格分析，龙虎榜适合作为事件补充。</div>
        </el-form-item>

        <el-form-item label="同步模式">
          <div class="mode-panel">
            <button
              type="button"
              class="mode-card"
              :class="{ 'is-active': syncMode === 'incremental' }"
              @click="syncMode = 'incremental'"
            >
              <span class="mode-card__eyebrow">日常增量</span>
              <strong>按增量窗口滚动更新</strong>
              <p>主要用于每天自动或手动补最近数据，依赖下方的“增量天数”和“同步频率”。</p>
            </button>
            <button
              type="button"
              class="mode-card"
              :class="{ 'is-active': syncMode === 'backfill' }"
              @click="syncMode = 'backfill'"
            >
              <span class="mode-card__eyebrow">历史补数</span>
              <strong>按时间范围回补历史数据</strong>
              <p>适合首轮建仓、补缺失记录或按阶段回溯，依赖下方日期范围。</p>
            </button>
          </div>
        </el-form-item>

        <el-form-item label="历史补数范围">
          <div class="range-panel">
            <el-date-picker
              v-model="syncDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              clearable
            />
            <div class="preset-actions">
              <el-button plain @click="applyPresetRange(7)">近7天</el-button>
              <el-button plain @click="applyPresetRange(30)">近30天</el-button>
              <el-button plain @click="applyPresetRange(90)">近90天</el-button>
              <el-button text @click="clearDateRange">清空范围</el-button>
            </div>
          </div>
          <div class="settings-tip">历史补数只读取这里的日期区间；日常增量会忽略这个范围，改为按“增量天数”滚动同步。</div>
          <el-alert
            v-if="dateRangeValidation.hasFutureDate"
            class="settings-alert"
            type="warning"
            show-icon
            :closable="false"
            title="历史补数范围包含未来日期"
            :description="`当前服务器允许的最晚日期是 ${todayDateLabel}，请把开始或结束日期调整到今天及以前。`"
          />
        </el-form-item>

        <div class="settings-grid">
          <el-form-item label="同步频率(秒)">
            <el-input-number v-model="marketForm.fetch_interval" :min="60" :step="300" />
          </el-form-item>

          <el-form-item label="增量天数">
            <el-input-number v-model="marketForm.history_days" :min="1" :step="5" />
          </el-form-item>

          <el-form-item label="自动同步">
            <el-switch v-model="marketForm.auto_sync" />
          </el-form-item>
        </div>

        <el-form-item>
          <div class="settings-actions settings-actions--wide">
            <el-button type="primary" :loading="marketSaving" @click="saveMarketSettings()">
              保存拉取策略
            </el-button>
            <el-button
              type="success"
              :loading="syncStarting && pendingSyncMode === syncMode"
              :disabled="isSyncRunning"
              @click="triggerSync(syncMode)"
            >
              {{ syncActionLabel }}
            </el-button>
            <el-button
              plain
              :loading="syncStarting && pendingSyncMode === 'incremental'"
              :disabled="isSyncRunning"
              @click="triggerSync('incremental')"
            >
              执行增量同步
            </el-button>
            <el-button
              plain
              :loading="syncStarting && pendingSyncMode === 'backfill'"
              :disabled="isSyncRunning"
              @click="triggerSync('backfill')"
            >
              执行历史补数
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <div class="runtime-grid">
        <div class="runtime-card glass-surface">
          <span>最近同步时间</span>
          <strong>{{ runtimeStatus.last_sync_at || '尚未执行' }}</strong>
        </div>
        <div class="runtime-card glass-surface">
          <span>最近同步状态</span>
          <strong>{{ runtimeStatus.last_sync_status || '未开始' }}</strong>
        </div>
        <div class="runtime-card glass-surface runtime-card--message">
          <span>最近同步说明</span>
          <strong>{{ runtimeStatus.last_sync_message || '保存策略后可手动同步，也可以开启自动同步。' }}</strong>
        </div>
      </div>

      <div class="sync-monitor glass-surface">
        <div class="sync-monitor__header">
          <div>
            <span class="sync-monitor__eyebrow">Execution Monitor</span>
            <h3>同步进度与失败明细</h3>
          </div>
          <div class="sync-monitor__tags">
            <el-tag :type="syncModeTagType">{{ syncModeLabel(syncStatus.mode) }}</el-tag>
            <el-tag :type="syncStatusTagType">{{ syncStatusLabel }}</el-tag>
          </div>
        </div>

        <el-progress
          :percentage="syncStatus.progress"
          :status="progressStatus"
          :indeterminate="isSyncRunning && syncStatus.total === 0"
          :stroke-width="12"
        />

        <div class="sync-monitor__meta">
          <span>任务进度：{{ syncStatus.current }}/{{ syncStatus.total || '--' }}</span>
          <span>当前任务：{{ syncStatus.current_task || '等待开始' }}</span>
          <span>最后更新：{{ syncStatus.updated_at || '暂无' }}</span>
        </div>

        <div class="settings-tip sync-monitor__message">
          {{ syncStatus.message || '点击“立即拉取”后，这里会展示同步进度、当前任务和失败明细。' }}
        </div>

        <el-alert
          v-if="syncStatus.result?.message && syncStatus.status !== 'running'"
          :title="syncStatus.result.message"
          :type="syncResultAlertType"
          show-icon
          :closable="false"
        />

        <div v-if="syncStatus.errors.length" class="sync-errors">
          <div class="sync-errors__title">失败明细</div>
          <div class="sync-errors__list">
            <div v-for="(item, index) in syncStatus.errors" :key="`${item}-${index}`" class="sync-errors__item">
              {{ item }}
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { getMarketDataSyncStatus, searchMarketStocks, syncMarketData } from '../../api/index'
import { getSettings, testTushare, updateSettings } from '../../api/settings'

const datasetOptions = [
  { label: '日线行情', value: 'daily' },
  { label: '基础指标', value: 'daily_basic' },
  { label: '资金流向', value: 'moneyflow' },
  { label: '龙虎榜', value: 'top_list' },
  { label: '大盘指数', value: 'index_daily' },
]
const defaultBenchmarkOptions = [
  { code: '000001.SH', label: '上证指数' },
  { code: '399001.SZ', label: '深证成指' },
  { code: '399006.SZ', label: '创业板指' },
  { code: '000300.SH', label: '沪深300' },
  { code: '000905.SH', label: '中证500' },
  { code: '000852.SH', label: '中证1000' },
  { code: '000688.SH', label: '科创50' },
]

const connectionForm = ref({ token: '', api_url: '' })
const marketForm = ref({
  symbols: '',
  data_types: ['daily', 'daily_basic', 'moneyflow', 'index_daily'],
  benchmark_index_codes: defaultBenchmarkOptions.map(item => item.code),
  primary_benchmark: '000300.SH',
  fetch_interval: 3600,
  history_days: 30,
  auto_sync: false,
})
const syncMode = ref('incremental')
const syncDateRange = ref([])
const runtimeStatus = ref({
  last_sync_at: '',
  last_sync_status: '',
  last_sync_message: '',
})
const stockSearchSelection = ref([])
const stockSearchResults = ref([])
const stockMarketFilter = ref('')
const stockAreaFilter = ref('')
const stockIndustryFilter = ref('')
const stockMarketOptions = ref([])
const stockAreaOptions = ref([])
const stockIndustryOptions = ref([])
const stockSearchLoading = ref(false)
const stockSearchTotal = ref(0)
const addingFilteredStocks = ref(false)
const manualPoolInput = ref('')
const stockMetaMap = ref({})
const syncStatus = ref(createEmptySyncStatus())
const activeSyncId = ref('')
const connectionSaving = ref(false)
const marketSaving = ref(false)
const testing = ref(false)
const syncStarting = ref(false)
const pendingSyncMode = ref('')
const testResult = ref(null)
const tokenPlaceholder = ref('Tushare Pro Token')

let syncPollingTimer = null
let stockSearchKeyword = ''

const todayDateLabel = formatDate(new Date())
const isSyncRunning = computed(() => syncStatus.value.status === 'running')
const syncActionLabel = computed(() => `立即拉取（${syncModeLabel(syncMode.value)}）`)
const symbolValidation = computed(() => buildSymbolValidation(marketForm.value.symbols))
const benchmarkValidation = computed(() =>
  buildSymbolValidation((marketForm.value.benchmark_index_codes || []).join(',')),
)
const dateRangeValidation = computed(() => buildDateRangeValidation(syncDateRange.value))
const poolSymbols = computed(() => getPoolSymbols())
const poolSymbolSet = computed(() => new Set(poolSymbols.value))
const benchmarkOptions = computed(() => {
  const optionMap = new Map(defaultBenchmarkOptions.map(item => [item.code, item]))
  normalizeCodeList(marketForm.value.benchmark_index_codes).forEach(code => {
    if (!optionMap.has(code)) {
      optionMap.set(code, { code, label: code })
    }
  })
  const primary = normalizeSymbol(marketForm.value.primary_benchmark)
  if (primary && !optionMap.has(primary)) {
    optionMap.set(primary, { code: primary, label: primary })
  }
  return Array.from(optionMap.values())
})
const poolStockItems = computed(() =>
  poolSymbols.value.map((tsCode, index) => {
    const meta = stockMetaMap.value[tsCode] || {}
    return {
      index,
      ts_code: tsCode,
      name: meta.name || '',
      market: meta.market || '',
      area: meta.area || '',
      industry: meta.industry || '',
    }
  }),
)
const syncStatusLabel = computed(() => {
  const labelMap = {
    idle: '待执行',
    started: '已创建',
    running: '执行中',
    completed: syncStatus.value.result?.status === 'partial' ? '部分完成' : '已完成',
    failed: '执行失败',
    unknown: '暂无任务',
  }
  return labelMap[syncStatus.value.status] || '暂无任务'
})
const syncStatusTagType = computed(() => {
  if (syncStatus.value.status === 'failed') {
    return 'danger'
  }
  if (syncStatus.value.result?.status === 'partial') {
    return 'warning'
  }
  if (syncStatus.value.status === 'completed') {
    return 'success'
  }
  if (syncStatus.value.status === 'running') {
    return 'warning'
  }
  return 'info'
})
const syncModeTagType = computed(() => (syncStatus.value.mode === 'backfill' ? 'warning' : 'success'))
const progressStatus = computed(() => {
  if (syncStatus.value.status === 'failed') {
    return 'exception'
  }
  if (syncStatus.value.result?.status === 'partial') {
    return 'warning'
  }
  if (syncStatus.value.status === 'completed') {
    return 'success'
  }
  return undefined
})
const syncResultAlertType = computed(() => {
  if (syncStatus.value.status === 'failed' || syncStatus.value.result?.status === 'failed') {
    return 'error'
  }
  if (syncStatus.value.result?.status === 'partial') {
    return 'warning'
  }
  return 'success'
})

function createEmptySyncStatus() {
  return {
    sync_id: '',
    status: 'idle',
    mode: 'incremental',
    message: '',
    progress: 0,
    current: 0,
    total: 0,
    current_task: '',
    errors: [],
    started_at: '',
    updated_at: '',
    result: {},
  }
}

function normalizeSyncStatus(payload = {}) {
  return {
    ...createEmptySyncStatus(),
    ...payload,
    errors: Array.isArray(payload.errors) ? payload.errors : [],
    result: payload.result && typeof payload.result === 'object' ? payload.result : {},
  }
}

function syncModeLabel(mode) {
  return mode === 'backfill' ? '历史补数' : '日常增量'
}

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback
}

function parseBoolean(value) {
  return ['1', 'true', 'yes', 'on'].includes(String(value || '').trim().toLowerCase())
}

function parseInteger(value, fallback) {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : fallback
}

function parseList(value, fallback = []) {
  if (!value) {
    return fallback
  }
  return String(value)
    .replaceAll('\n', ',')
    .replaceAll('，', ',')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function normalizeSymbol(symbol) {
  const normalized = String(symbol || '').trim().toUpperCase()
  if (!normalized) {
    return ''
  }
  if (normalized.includes('.')) {
    return normalized
  }
  if (/^\d{6}$/.test(normalized)) {
    if (/^[48]/.test(normalized)) {
      return `${normalized}.BJ`
    }
    if (/^[569]/.test(normalized)) {
      return `${normalized}.SH`
    }
    return `${normalized}.SZ`
  }
  return normalized
}

function normalizeSymbolsText(value) {
  return String(value || '')
    .replaceAll('\n', ',')
    .replaceAll('，', ',')
    .split(',')
    .map(item => normalizeSymbol(item))
    .filter(Boolean)
    .join(',')
}

function normalizeCodeList(value) {
  return Array.from(new Set(parseList(Array.isArray(value) ? value.join(',') : value).map(item => normalizeSymbol(item))))
}

function normalizeBenchmarkState(codes, primary) {
  const normalizedCodes = normalizeCodeList(codes)
  const normalizedPrimary = normalizeSymbol(primary)

  if (normalizedPrimary) {
    if (!normalizedCodes.includes(normalizedPrimary)) {
      normalizedCodes.unshift(normalizedPrimary)
    }
    return {
      codes: normalizedCodes,
      primary: normalizedPrimary,
    }
  }

  return {
    codes: normalizedCodes,
    primary: normalizedCodes[0] || '',
  }
}

function splitSymbols(value) {
  return String(value || '')
    .replaceAll('\n', ',')
    .replaceAll('，', ',')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function isValidSymbol(symbol) {
  return /^\d{6}$/.test(symbol) || /^\d{6}\.(SH|SZ|BJ)$/i.test(symbol)
}

function buildSymbolValidation(value) {
  const rawSymbols = splitSymbols(value)
  const invalidSymbols = rawSymbols
    .map(item => item.toUpperCase())
    .filter(item => !isValidSymbol(item))
  const normalizedSymbols = rawSymbols.map(item => normalizeSymbol(item)).filter(Boolean)
  const rawUpper = rawSymbols.map(item => item.toUpperCase()).join(',')
  const normalizedPreview = normalizedSymbols.join(',')

  return {
    invalidSymbols,
    normalizedPreview: invalidSymbols.length === 0 && normalizedPreview && normalizedPreview !== rawUpper
      ? normalizedPreview
      : '',
  }
}

function buildDateRangeValidation(range) {
  const [startDate = '', endDate = ''] = range || []
  const today = todayDateLabel
  return {
    hasFutureDate: Boolean((startDate && startDate > today) || (endDate && endDate > today)),
  }
}

function formatStockOptionLabel(item) {
  const name = item?.name || ''
  const tsCode = item?.ts_code || ''
  const market = item?.market || ''
  return [name, tsCode, market].filter(Boolean).join(' / ')
}

function cacheStockMeta(items = []) {
  if (!items.length) {
    return
  }

  stockMetaMap.value = {
    ...stockMetaMap.value,
    ...Object.fromEntries(
      items
        .filter(item => item?.ts_code)
        .map(item => [
          item.ts_code,
          {
            name: item.name || '',
            market: item.market || '',
            area: item.area || '',
            industry: item.industry || '',
          },
        ]),
    ),
  }
}

function isStockInPool(tsCode) {
  return poolSymbolSet.value.has(tsCode)
}

function getPoolSymbols() {
  return normalizeSymbolsText(marketForm.value.symbols)
    .split(',')
    .map(item => item.trim())
    .filter(Boolean)
}

function setPoolSymbols(symbols) {
  const normalized = Array.from(new Set(symbols.map(item => normalizeSymbol(item)).filter(Boolean)))
  marketForm.value.symbols = normalized.join(',')
}

function mergeSymbolsIntoPool(symbols) {
  const merged = [...getPoolSymbols(), ...symbols]
  setPoolSymbols(merged)
}

function addManualSymbolsToPool() {
  const normalized = normalizeSymbolsText(manualPoolInput.value)
  if (!normalized) {
    ElMessage.warning('请输入要加入股票池的股票代码')
    return
  }
  mergeSymbolsIntoPool(normalized.split(','))
  manualPoolInput.value = ''
  ElMessage.success('已把手动输入的股票加入股票池')
}

function removePoolSymbol(tsCode) {
  setPoolSymbols(getPoolSymbols().filter(item => item !== tsCode))
}

function movePoolSymbol(index, offset) {
  const symbols = [...getPoolSymbols()]
  const targetIndex = index + offset
  if (targetIndex < 0 || targetIndex >= symbols.length) {
    return
  }
  const [current] = symbols.splice(index, 1)
  symbols.splice(targetIndex, 0, current)
  setPoolSymbols(symbols)
}

function sortPoolSymbolsByCode() {
  const symbols = [...getPoolSymbols()].sort((left, right) => left.localeCompare(right, 'zh-CN'))
  setPoolSymbols(symbols)
  ElMessage.success('股票池已按代码排序')
}

function handleBenchmarkCodesChange(values) {
  const normalized = normalizeBenchmarkState(values, marketForm.value.primary_benchmark)
  marketForm.value.benchmark_index_codes = normalized.codes
  marketForm.value.primary_benchmark = normalized.primary
}

function handlePrimaryBenchmarkChange(value) {
  const normalized = normalizeBenchmarkState(marketForm.value.benchmark_index_codes, value)
  marketForm.value.benchmark_index_codes = normalized.codes
  marketForm.value.primary_benchmark = normalized.primary
}

function validateMarketSettings({ forSync = false } = {}) {
  if (symbolValidation.value.invalidSymbols.length) {
    ElMessage.error('股票池里存在格式不正确的代码，请先修正后再保存或同步')
    return false
  }

  if (benchmarkValidation.value.invalidSymbols.length) {
    ElMessage.error('大盘基准里存在格式不正确的代码，请先修正后再保存或同步')
    return false
  }

  if (marketForm.value.data_types.includes('index_daily') && !marketForm.value.benchmark_index_codes.length) {
    ElMessage.warning('已勾选“大盘指数”，请至少选择一个要同步的基准指数')
    return false
  }

  if (marketForm.value.benchmark_index_codes.length && !marketForm.value.primary_benchmark) {
    ElMessage.warning('请先选择一个主基准指数')
    return false
  }

  if (dateRangeValidation.value.hasFutureDate) {
    const action = forSync ? '执行同步' : '保存策略'
    ElMessage.warning(`历史补数范围不能晚于今天（${todayDateLabel}），请调整日期后再${action}`)
    return false
  }

  return true
}

function buildConnectionSettingsPayload() {
  return {
    settings: [
      { key: 'token', value: connectionForm.value.token, is_secret: true },
      { key: 'api_url', value: connectionForm.value.api_url, is_secret: false },
    ],
  }
}

function buildMarketSettingsPayload() {
  const [startDate = '', endDate = ''] = syncDateRange.value || []
  const normalizedBenchmark = normalizeBenchmarkState(
    marketForm.value.benchmark_index_codes,
    marketForm.value.primary_benchmark,
  )
  return {
    settings: [
      { key: 'symbols', value: normalizeSymbolsText(marketForm.value.symbols), is_secret: false },
      { key: 'data_types', value: marketForm.value.data_types.join(','), is_secret: false },
      { key: 'benchmark_index_codes', value: normalizedBenchmark.codes.join(','), is_secret: false },
      { key: 'primary_benchmark', value: normalizedBenchmark.primary, is_secret: false },
      { key: 'fetch_interval', value: String(marketForm.value.fetch_interval), is_secret: false },
      { key: 'history_days', value: String(marketForm.value.history_days), is_secret: false },
      { key: 'start_date', value: startDate, is_secret: false },
      { key: 'end_date', value: endDate, is_secret: false },
      { key: 'auto_sync', value: String(marketForm.value.auto_sync), is_secret: false },
    ],
  }
}

async function fetchStockCandidates(query = '', refresh = false, limit = 50) {
  stockSearchLoading.value = true
  try {
    const result = await searchMarketStocks({
      q: query,
      market: stockMarketFilter.value,
      area: stockAreaFilter.value,
      industry: stockIndustryFilter.value,
      limit,
      refresh,
    })
    stockSearchResults.value = result.items || []
    stockMarketOptions.value = result.markets || []
    stockAreaOptions.value = result.areas || []
    stockIndustryOptions.value = result.industries || []
    stockSearchTotal.value = result.total || 0
    cacheStockMeta(result.items || [])
  } catch (error) {
    stockSearchResults.value = []
    stockSearchTotal.value = 0
    ElMessage.error(getErrorMessage(error, '股票列表加载失败'))
  } finally {
    stockSearchLoading.value = false
  }
}

function stopSyncPolling() {
  if (syncPollingTimer) {
    window.clearTimeout(syncPollingTimer)
    syncPollingTimer = null
  }
}

function handleStockSearch(query) {
  stockSearchKeyword = query || ''
  fetchStockCandidates(stockSearchKeyword, false, 50)
}

function handleStockSearchVisibleChange(visible) {
  if (!visible || stockSearchResults.value.length) {
    return
  }
  fetchStockCandidates('', false, 50)
}

function handleStockMarketChange() {
  fetchStockCandidates(stockSearchKeyword, false, 50)
}

function handleStockAreaChange() {
  fetchStockCandidates(stockSearchKeyword, false, 50)
}

function handleStockIndustryChange() {
  fetchStockCandidates(stockSearchKeyword, false, 50)
}

function addSelectedStocksToPool() {
  if (!stockSearchSelection.value.length) {
    return
  }
  mergeSymbolsIntoPool(stockSearchSelection.value)
  ElMessage.success(`已加入 ${stockSearchSelection.value.length} 只股票到股票池`)
  stockSearchSelection.value = []
}

function addSearchResultsToPool() {
  if (!stockSearchResults.value.length) {
    return
  }
  mergeSymbolsIntoPool(stockSearchResults.value.map(item => item.ts_code))
  ElMessage.success(`已加入当前搜索结果，共 ${stockSearchResults.value.length} 只股票`)
}

async function addAllFilteredStocksToPool() {
  if (!stockMarketFilter.value && !stockAreaFilter.value && !stockIndustryFilter.value && !stockSearchKeyword) {
    ElMessage.warning('请至少设置一个搜索关键词或筛选条件，再批量加入全部筛选结果')
    return
  }

  addingFilteredStocks.value = true
  try {
    const result = await searchMarketStocks({
      q: stockSearchKeyword,
      market: stockMarketFilter.value,
      area: stockAreaFilter.value,
      industry: stockIndustryFilter.value,
      limit: 10000,
    })
    const items = result.items || []
    mergeSymbolsIntoPool(items.map(item => item.ts_code))
    cacheStockMeta(items)
    stockSearchResults.value = items
    stockSearchTotal.value = result.total || items.length
    stockMarketOptions.value = result.markets || stockMarketOptions.value
    stockAreaOptions.value = result.areas || stockAreaOptions.value
    stockIndustryOptions.value = result.industries || stockIndustryOptions.value
    ElMessage.success(`已把全部筛选结果加入股票池，共 ${items.length} 只股票`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '批量加载筛选股票失败'))
  } finally {
    addingFilteredStocks.value = false
  }
}

function refreshStockCatalog() {
  fetchStockCandidates(stockSearchKeyword, true, 50)
}

function applyPresetRange(days) {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - (days - 1))
  syncDateRange.value = [formatDate(start), formatDate(end)]
  syncMode.value = 'backfill'
}

function clearDateRange() {
  syncDateRange.value = []
}

async function loadConnectionSettings() {
  const res = await getSettings('tushare')
  const tokenSetting = res.settings.find(item => item.key === 'token')
  const apiUrlSetting = res.settings.find(item => item.key === 'api_url')

  if (tokenSetting) {
    if (tokenSetting.value && tokenSetting.value.includes('****')) {
      tokenPlaceholder.value = `${tokenSetting.value}（已保存，如需更换请重新输入）`
      connectionForm.value.token = ''
    } else {
      connectionForm.value.token = tokenSetting.value
    }
  }

  if (apiUrlSetting) {
    connectionForm.value.api_url = apiUrlSetting.value || ''
  }
}

async function loadMarketSettings() {
  const res = await getSettings('market_data')
  const map = Object.fromEntries((res.settings || []).map(item => [item.key, item.value]))
  marketForm.value.symbols = normalizeSymbolsText(map.symbols || '')
  marketForm.value.data_types = parseList(map.data_types, ['daily', 'daily_basic', 'moneyflow', 'index_daily'])
  const normalizedBenchmark = normalizeBenchmarkState(
    parseList(map.benchmark_index_codes, defaultBenchmarkOptions.map(item => item.code)),
    map.primary_benchmark || '000300.SH',
  )
  marketForm.value.benchmark_index_codes = normalizedBenchmark.codes
  marketForm.value.primary_benchmark = normalizedBenchmark.primary
  marketForm.value.fetch_interval = parseInteger(map.fetch_interval, 3600)
  marketForm.value.history_days = parseInteger(map.history_days, 30)
  marketForm.value.auto_sync = parseBoolean(map.auto_sync)
  syncDateRange.value = map.start_date && map.end_date ? [map.start_date, map.end_date] : []
  syncMode.value = syncDateRange.value.length === 2 ? 'backfill' : 'incremental'
}

async function loadRuntimeSettings() {
  const res = await getSettings('market_data_runtime')
  const map = Object.fromEntries((res.settings || []).map(item => [item.key, item.value]))
  runtimeStatus.value = {
    last_sync_at: map.last_sync_at || '',
    last_sync_status: map.last_sync_status || '',
    last_sync_message: map.last_sync_message || '',
  }
}

async function loadLatestSyncStatus() {
  const result = await getMarketDataSyncStatus()
  const normalized = normalizeSyncStatus(result)

  if (normalized.status === 'unknown') {
    syncStatus.value = createEmptySyncStatus()
    activeSyncId.value = ''
    return
  }

  syncStatus.value = normalized
  activeSyncId.value = normalized.sync_id || ''

  if (normalized.status === 'running' && normalized.sync_id) {
    scheduleSyncPolling(normalized.sync_id, false)
  }
}

function scheduleSyncPolling(syncId, notifyOnFinish = true) {
  stopSyncPolling()
  syncPollingTimer = window.setTimeout(() => pollSyncStatus(syncId, notifyOnFinish), 1500)
}

async function pollSyncStatus(syncId = activeSyncId.value, notifyOnFinish = true) {
  if (!syncId) {
    return
  }

  try {
    const result = await getMarketDataSyncStatus(syncId)
    const normalized = normalizeSyncStatus(result)
    syncStatus.value = normalized
    activeSyncId.value = normalized.sync_id || syncId

    if (normalized.status === 'running') {
      scheduleSyncPolling(syncId, notifyOnFinish)
      return
    }

    stopSyncPolling()
    pendingSyncMode.value = ''
    syncStarting.value = false
    await loadRuntimeSettings()

    if (!notifyOnFinish) {
      return
    }

    if (normalized.status === 'failed') {
      ElMessage.error(normalized.result?.message || normalized.message || '同步失败')
      return
    }

    if (normalized.result?.status === 'partial') {
      ElMessage.warning(normalized.result?.message || '同步完成，但存在部分失败任务')
      return
    }

    ElMessage.success(normalized.result?.message || '同步完成')
  } catch (error) {
    stopSyncPolling()
    pendingSyncMode.value = ''
    syncStarting.value = false
    ElMessage.error(getErrorMessage(error, '同步状态查询失败'))
  }
}

async function saveConnectionSettings() {
  connectionSaving.value = true
  try {
    await updateSettings('tushare', buildConnectionSettingsPayload())
    ElMessage.success('连接配置已保存')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存失败'))
  } finally {
    connectionSaving.value = false
  }
}

async function saveMarketSettings(showMessage = true) {
  if (!validateMarketSettings({ forSync: false })) {
    return
  }

  marketSaving.value = true
  try {
    await updateSettings('market_data', buildMarketSettingsPayload())
    if (showMessage) {
      ElMessage.success('拉取策略已保存')
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存失败'))
    throw error
  } finally {
    marketSaving.value = false
  }
}

async function testConnection() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testTushare({
      token: connectionForm.value.token,
      api_url: connectionForm.value.api_url,
    })
  } catch (error) {
    testResult.value = { success: false, message: getErrorMessage(error, '请求失败') }
  } finally {
    testing.value = false
  }
}

async function triggerSync(mode = syncMode.value) {
  if (isSyncRunning.value) {
    ElMessage.warning('已有同步任务正在执行，请等待当前任务结束')
    return
  }

  if (mode === 'backfill' && (!syncDateRange.value || syncDateRange.value.length !== 2)) {
    ElMessage.warning('执行历史补数前，请先选择完整的时间范围')
    return
  }

  if (!validateMarketSettings({ forSync: true })) {
    return
  }

  pendingSyncMode.value = mode
  syncStarting.value = true

  try {
    await saveMarketSettings(false)
    const result = await syncMarketData({ mode })
    syncMode.value = mode
    activeSyncId.value = result.sync_id
    syncStatus.value = normalizeSyncStatus({
      sync_id: result.sync_id,
      status: 'running',
      mode: result.mode || mode,
      message: result.message || '行情同步任务已启动',
    })
    scheduleSyncPolling(result.sync_id, true)
  } catch (error) {
    pendingSyncMode.value = ''
    syncStarting.value = false
    ElMessage.error(getErrorMessage(error, '同步失败'))
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      loadConnectionSettings(),
      loadMarketSettings(),
      loadRuntimeSettings(),
      loadLatestSyncStatus(),
    ])
  } catch {}
})

onBeforeUnmount(() => {
  stopSyncPolling()
})
</script>

<style scoped>
.settings-form {
  max-width: 1040px;
}

.settings-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.settings-actions--wide {
  align-items: center;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.stock-search-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.stock-search-toolbar {
  display: flex;
  width: 100%;
}

.stock-search-select,
.stock-market-filter {
  width: 100%;
}

.stock-filter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.stock-search-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stock-option {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.stock-option__main,
.stock-option__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-option__main strong {
  font-size: 13px;
  color: var(--text-primary);
}

.stock-option__badges {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.stock-option__main span,
.stock-option__meta span {
  font-size: 12px;
  color: var(--text-secondary);
}

.stock-pool-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(120, 148, 180, 0.24);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.74), rgba(244, 249, 255, 0.58)),
    radial-gradient(circle at top right, rgba(108, 167, 246, 0.18), transparent 52%);
  backdrop-filter: blur(18px);
}

.stock-pool-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.stock-pool-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--text-secondary);
  font-size: 13px;
}

.stock-pool-summary span {
  color: var(--text-primary);
  font-weight: 600;
}

.stock-pool-summary small {
  line-height: 1.7;
}

.stock-pool-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.stock-pool-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 164px;
  padding: 16px;
  border: 1px solid rgba(120, 148, 180, 0.18);
}

.stock-pool-card__copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stock-pool-card__copy strong {
  font-size: 14px;
  color: var(--text-primary);
}

.stock-pool-card__copy span {
  font-size: 12px;
  color: var(--text-secondary);
}

.stock-pool-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
}

.stock-pool-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: auto;
}

.benchmark-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
  padding: 18px;
  border-radius: 24px;
  border: 1px solid rgba(120, 148, 180, 0.24);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.76), rgba(243, 248, 255, 0.6)),
    radial-gradient(circle at top right, rgba(61, 129, 212, 0.16), transparent 52%);
  backdrop-filter: blur(18px);
}

.benchmark-panel__header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 320px);
  gap: 14px;
  align-items: start;
}

.benchmark-panel__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.benchmark-panel__desc {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.8;
}

.benchmark-primary-select,
.benchmark-code-select {
  width: 100%;
}

.benchmark-panel__summary {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.settings-tip {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.settings-alert {
  margin-top: 12px;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 18px;
}

.mode-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  width: 100%;
}

.mode-card {
  padding: 18px 20px;
  border: 1px solid rgba(120, 148, 180, 0.28);
  border-radius: 20px;
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.78), rgba(246, 250, 255, 0.54)),
    radial-gradient(circle at top right, rgba(115, 181, 255, 0.22), transparent 50%);
  backdrop-filter: blur(18px);
  text-align: left;
  transition: transform 0.22s ease, border-color 0.22s ease, box-shadow 0.22s ease;
  cursor: pointer;
}

.mode-card:hover {
  transform: translateY(-2px);
  border-color: rgba(87, 141, 214, 0.46);
  box-shadow: 0 18px 36px rgba(36, 64, 102, 0.12);
}

.mode-card.is-active {
  border-color: rgba(62, 123, 202, 0.7);
  box-shadow: 0 22px 44px rgba(54, 92, 150, 0.16);
}

.mode-card__eyebrow {
  display: inline-flex;
  margin-bottom: 10px;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(64, 96, 146, 0.78);
}

.mode-card strong {
  display: block;
  margin-bottom: 8px;
  font-size: 16px;
}

.mode-card p {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.7;
}

.range-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.preset-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.runtime-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 4px;
}

.runtime-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px;
}

.runtime-card span {
  color: var(--text-secondary);
  font-size: 12px;
}

.runtime-card strong {
  line-height: 1.7;
}

.sync-monitor {
  margin-top: 18px;
  padding: 24px;
  border: 1px solid rgba(120, 148, 180, 0.22);
}

.sync-monitor__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.sync-monitor__header h3 {
  margin: 6px 0 0;
  font-size: 20px;
}

.sync-monitor__eyebrow {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(64, 96, 146, 0.72);
}

.sync-monitor__tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sync-monitor__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
  font-size: 13px;
  color: var(--text-secondary);
}

.sync-monitor__message {
  margin: 14px 0 18px;
}

.sync-errors {
  margin-top: 18px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 245, 245, 0.62);
  border: 1px solid rgba(216, 96, 96, 0.18);
}

.sync-errors__title {
  font-size: 13px;
  font-weight: 600;
  color: #a13f3f;
  margin-bottom: 12px;
}

.sync-errors__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sync-errors__item {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  line-height: 1.6;
  color: #6f2d2d;
  font-size: 13px;
}

@media (max-width: 960px) {
  .stock-filter-grid,
  .settings-grid,
  .runtime-grid,
  .benchmark-panel__header,
  .checkbox-grid,
  .mode-panel,
  .sync-monitor__meta {
    grid-template-columns: 1fr;
  }

  .sync-monitor__header {
    flex-direction: column;
  }
}

@media (max-width: 720px) {
  .stock-option {
    flex-direction: column;
  }

  .stock-option__badges {
    justify-content: flex-start;
  }

  .stock-pool-toolbar {
    grid-template-columns: 1fr;
  }

  .stock-pool-summary {
    align-items: flex-start;
  }

  .stock-pool-grid {
    grid-template-columns: 1fr;
  }
}
</style>
