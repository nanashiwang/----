<template>
  <el-card header="回测系统">
    <el-form :inline="true" :model="form">
      <el-form-item label="开始日期">
        <el-date-picker v-model="form.start_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="form.end_date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="持有天数">
        <el-input-number v-model="form.hold_days" :min="1" :max="30" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="run" :loading="loading">运行回测</el-button>
      </el-form-item>
    </el-form>

    <template v-if="result">
      <el-divider />
      <el-row :gutter="16" v-if="!result.error" style="margin-bottom:16px">
        <el-col :span="6"><el-statistic title="总交易次数" :value="result.total_trades" /></el-col>
        <el-col :span="6"><el-statistic title="胜率" :value="(result.win_rate * 100).toFixed(1) + '%'" /></el-col>
        <el-col :span="6"><el-statistic title="平均收益" :value="(result.avg_return * 100).toFixed(2) + '%'" /></el-col>
        <el-col :span="6"><el-statistic title="最大收益" :value="(result.max_return * 100).toFixed(2) + '%'" /></el-col>
      </el-row>
      <el-alert v-if="result.error" :title="result.error" type="warning" show-icon />
      <el-table v-if="result.details" :data="result.details" size="small" stripe>
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column prop="ts_code" label="股票" width="110" />
        <el-table-column prop="weight" label="权重" width="80" />
        <el-table-column label="收益率" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.return_rate >= 0 ? '#67c23a' : '#f56c6c' }">
              {{ (row.return_rate * 100).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { runBacktest } from '../../api/index'
import dayjs from 'dayjs'

const form = ref({
  start_date: dayjs().subtract(30, 'day').format('YYYY-MM-DD'),
  end_date: dayjs().format('YYYY-MM-DD'),
  hold_days: 5,
})
const result = ref(null)
const loading = ref(false)

async function run() {
  loading.value = true
  result.value = null
  try { result.value = await runBacktest(form.value) }
  catch { result.value = { error: '请求失败' } }
  finally { loading.value = false }
}
</script>
