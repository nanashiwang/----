<template>
  <el-row :gutter="16">
    <el-col :span="12">
      <el-card header="热知识库">
        <el-table :data="hotList" v-loading="loading" size="small">
          <el-table-column prop="content" label="内容" show-overflow-tooltip />
          <el-table-column prop="category" label="分类" width="80" />
          <el-table-column label="置信度" width="100">
            <template #default="{ row }">{{ ((row.confidence || 0) * 100).toFixed(0) }}%</template>
          </el-table-column>
          <el-table-column prop="test_count" label="测试次数" width="80" />
          <el-table-column label="操作" width="60">
            <template #default="{ row }">
              <el-button link type="danger" size="small" @click="doDelete(row._id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-col>
    <el-col :span="12">
      <el-card header="冷知识库">
        <el-select v-model="coldAgent" @change="loadCold" style="margin-bottom:12px;width:100%">
          <el-option label="技术指标专员" value="tech_analyst" />
          <el-option label="事件收集专员" value="event_collector" />
          <el-option label="复盘分析师" value="retrospect_agent" />
        </el-select>
        <el-table :data="coldList" size="small">
          <el-table-column prop="content" label="内容" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="180" />
        </el-table>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getHotKnowledge, getColdKnowledge, deleteHotKnowledge } from '../../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const hotList = ref([])
const coldList = ref([])
const coldAgent = ref('tech_analyst')
const loading = ref(false)

async function loadHot() {
  loading.value = true
  try { hotList.value = await getHotKnowledge({ limit: 20 }) } finally { loading.value = false }
}
async function loadCold() {
  try { coldList.value = await getColdKnowledge(coldAgent.value) } catch {}
}
async function doDelete(id) {
  await ElMessageBox.confirm('确认删除？')
  await deleteHotKnowledge(id)
  ElMessage.success('已删除')
  loadHot()
}

onMounted(() => { loadHot(); loadCold() })
</script>
