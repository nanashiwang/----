<template>
  <el-card header="推荐看板">
    <el-date-picker v-model="date" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" @change="load" style="margin-bottom:16px" />
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="ts_code" label="股票代码" width="110" />
      <el-table-column prop="weight" label="推荐权重" width="100" sortable>
        <template #default="{ row }">
          <el-progress :percentage="(row.weight || 0) * 100" :stroke-width="14" :text-inside="true" />
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="推荐理由" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRecommendations } from '../../api/index'

const date = ref(new Date().toISOString().slice(0, 10))
const list = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try { list.value = await getRecommendations({ date: date.value }) } finally { loading.value = false }
}
onMounted(load)
</script>
