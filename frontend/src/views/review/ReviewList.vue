<template>
  <el-card header="复盘分析">
    <div v-loading="loading">
      <el-empty v-if="!list.length" description="暂无复盘数据" />
      <el-collapse v-else>
        <el-collapse-item v-for="item in list" :key="item._id" :title="`${item.date} - ${item.summary}`">
          <p><strong>成功:</strong> {{ (item.correct_predictions || []).join(', ') || '无' }}</p>
          <p><strong>失败:</strong> {{ (item.wrong_predictions || []).join(', ') || '无' }}</p>
          <p><strong>关键洞察:</strong></p>
          <ul><li v-for="(ins, i) in (item.key_insights || [])" :key="i">{{ ins }}</li></ul>
        </el-collapse-item>
      </el-collapse>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getReviews } from '../../api/index'

const list = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try { list.value = await getReviews({ limit: 20 }) } finally { loading.value = false }
})
</script>
