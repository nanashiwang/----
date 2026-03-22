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
        <el-form-item label="股票池">
          <el-input
            v-model="marketForm.symbols"
            type="textarea"
            :rows="4"
            placeholder="000001.SZ,600519.SH,159915.SZ"
          />
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

import { getMarketDataSyncStatus, syncMarketData } from '../../api/index'
import { getSettings, testTushare, updateSettings } from '../../api/settings'

const datasetOptions = [
  { label: '日线行情', value: 'daily' },
  { label: '基础指标', value: 'daily_basic' },
  { label: '资金流向', value: 'moneyflow' },
  { label: '龙虎榜', value: 'top_list' },
]

const connectionForm = ref({ token: '', api_url: '' })
const marketForm = ref({
  symbols: '',
  data_types: ['daily', 'daily_basic', 'moneyflow'],
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

const todayDateLabel = formatDate(new Date())
const isSyncRunning = computed(() => syncStatus.value.status === 'running')
const syncActionLabel = computed(() => `立即拉取（${syncModeLabel(syncMode.value)}）`)
const symbolValidation = computed(() => buildSymbolValidation(marketForm.value.symbols))
const dateRangeValidation = computed(() => buildDateRangeValidation(syncDateRange.value))
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

function validateMarketSettings({ forSync = false } = {}) {
  if (symbolValidation.value.invalidSymbols.length) {
    ElMessage.error('股票池里存在格式不正确的代码，请先修正后再保存或同步')
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
  return {
    settings: [
      { key: 'symbols', value: normalizeSymbolsText(marketForm.value.symbols), is_secret: false },
      { key: 'data_types', value: marketForm.value.data_types.join(','), is_secret: false },
      { key: 'fetch_interval', value: String(marketForm.value.fetch_interval), is_secret: false },
      { key: 'history_days', value: String(marketForm.value.history_days), is_secret: false },
      { key: 'start_date', value: startDate, is_secret: false },
      { key: 'end_date', value: endDate, is_secret: false },
      { key: 'auto_sync', value: String(marketForm.value.auto_sync), is_secret: false },
    ],
  }
}

function stopSyncPolling() {
  if (syncPollingTimer) {
    window.clearTimeout(syncPollingTimer)
    syncPollingTimer = null
  }
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
  marketForm.value.data_types = parseList(map.data_types, ['daily', 'daily_basic', 'moneyflow'])
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
  .settings-grid,
  .runtime-grid,
  .checkbox-grid,
  .mode-panel,
  .sync-monitor__meta {
    grid-template-columns: 1fr;
  }

  .sync-monitor__header {
    flex-direction: column;
  }
}
</style>
