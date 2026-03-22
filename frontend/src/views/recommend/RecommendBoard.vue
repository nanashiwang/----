<template>
  <div class="page-shell">
    <section class="page-hero page-hero--compact">
      <span class="page-eyebrow">Recommendation Feed</span>
      <h2>推荐看板</h2>
      <p>按日期查看策略输出，用更顺滑的玻璃化表格阅读权重、理由和生成时间。</p>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">推荐列表</div>
            <div class="panel-subtitle">建议优先关注高权重标的，再结合理由文本做人工复核。</div>
          </div>

          <div class="recommend-toolbar">
            <span class="section-tag">{{ list.length }} 条结果</span>
            <el-date-picker
              v-model="date"
              type="date"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="load"
            />
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" size="large" empty-text="当前日期暂无推荐结果">
        <el-table-column prop="ts_code" label="股票代码" width="120" />
        <el-table-column prop="weight" label="推荐权重" width="140" sortable>
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(100, Math.round((row.weight || 0) * 100))"
              :stroke-width="14"
              :text-inside="true"
            />
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="推荐理由" show-overflow-tooltip />
        <el-table-column prop="created_at" label="生成时间" width="190" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { getRecommendations } from '../../api/index'

const date = ref(new Date().toISOString().slice(0, 10))
const list = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    list.value = await getRecommendations({ date: date.value })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.recommend-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

@media (max-width: 768px) {
  .recommend-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
