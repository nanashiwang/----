<template>
  <el-card header="Agent 管理">
    <el-table :data="agents" v-loading="loading">
      <el-table-column prop="cluster" label="集群" width="90">
        <template #default="{ row }">
          <el-tag :type="clusterType(row.cluster)" size="small">{{ row.cluster }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="display_name" label="名称" width="140" />
      <el-table-column prop="system_prompt" label="Prompt" show-overflow-tooltip />
      <el-table-column prop="llm_model" label="模型" width="100" />
      <el-table-column prop="is_enabled" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">{{ row.is_enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/agents/${row.id}`)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAgents } from '../../api/index'

const agents = ref([])
const loading = ref(false)

const clusterType = (c) => ({ observe: 'primary', reason: 'success', act: 'warning', review: 'danger' }[c] || '')

onMounted(async () => {
  loading.value = true
  try { agents.value = await getAgents() } finally { loading.value = false }
})
</script>
