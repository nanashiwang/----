<template>
  <div>
    <el-row :gutter="16" class="mb">
      <el-col :span="6"><el-statistic title="今日推荐" :value="stats.todayRec" /></el-col>
      <el-col :span="6"><el-statistic title="累计推荐" :value="stats.totalRec" /></el-col>
      <el-col :span="6"><el-statistic title="交易次数" :value="stats.totalTrades" /></el-col>
      <el-col :span="6"><el-statistic title="知识条目" :value="stats.knowledgeCount" /></el-col>
    </el-row>

    <el-row :gutter="16" class="mb">
      <el-col :span="8">
        <el-card header="快捷操作">
          <el-space wrap>
            <el-button type="primary" @click="runWf('observe')" :loading="wfLoading">观察工作流</el-button>
            <el-button type="success" @click="runWf('reason')" :loading="wfLoading">推理工作流</el-button>
            <el-button type="warning" @click="runWf('review')" :loading="wfLoading">复盘工作流</el-button>
          </el-space>
          <p v-if="wfMsg" style="margin-top:12px;color:#999">{{ wfMsg }}</p>
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card header="最新推荐">
          <el-table :data="latestRec" size="small" max-height="250">
            <el-table-column prop="ts_code" label="股票" width="100" />
            <el-table-column prop="weight" label="权重" width="80" />
            <el-table-column prop="reason" label="理由" show-overflow-tooltip />
            <el-table-column prop="date" label="日期" width="110" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRecommendations, getTrades, getHotKnowledge, runWorkflow, getWorkflowStatus } from '../api/index'
import { ElMessage } from 'element-plus'

const stats = ref({ todayRec: 0, totalRec: 0, totalTrades: 0, knowledgeCount: 0 })
const latestRec = ref([])
const wfLoading = ref(false)
const wfMsg = ref('')

onMounted(async () => {
  try {
    const [rec, trades, kb] = await Promise.all([
      getRecommendations({ limit: 10 }),
      getTrades({ limit: 1 }),
      getHotKnowledge({ limit: 1 }),
    ])
    latestRec.value = rec
    stats.value.totalRec = rec.length
    stats.value.todayRec = rec.filter(r => r.date === new Date().toISOString().slice(0, 10)).length
  } catch {}
})

async function runWf(type) {
  wfLoading.value = true
  wfMsg.value = '启动中...'
  try {
    const res = await runWorkflow(type)
    wfMsg.value = `已启动: ${res.workflow_id}`
    const check = setInterval(async () => {
      const s = await getWorkflowStatus(res.workflow_id)
      wfMsg.value = `${s.status}: ${s.message || ''}`
      if (s.status === 'completed' || s.status === 'failed') {
        clearInterval(check)
        wfLoading.value = false
        ElMessage[s.status === 'completed' ? 'success' : 'error'](s.message)
      }
    }, 3000)
  } catch (e) {
    wfMsg.value = '启动失败'
    wfLoading.value = false
  }
}
</script>

<style scoped>
.mb { margin-bottom: 16px; }
</style>
