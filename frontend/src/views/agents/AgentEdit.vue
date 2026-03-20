<template>
  <el-card :header="`编辑 Agent: ${form.display_name}`">
    <el-form :model="form" label-width="120px" v-loading="loading">
      <el-form-item label="集群">
        <el-tag>{{ form.cluster }}</el-tag>
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.display_name" />
      </el-form-item>
      <el-form-item label="System Prompt">
        <el-input v-model="form.system_prompt" type="textarea" :rows="8" />
      </el-form-item>
      <el-form-item label="LLM提供商">
        <el-input v-model="form.llm_provider" placeholder="留空使用全局配置" />
      </el-form-item>
      <el-form-item label="LLM模型">
        <el-input v-model="form.llm_model" placeholder="留空使用全局配置" />
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="form.is_enabled" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="$router.push('/agents')">返回</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAgent, updateAgent } from '../../api/index'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const form = ref({ cluster: '', display_name: '', system_prompt: '', llm_provider: '', llm_model: '', is_enabled: true })
const loading = ref(false)
const saving = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const data = await getAgent(route.params.id)
    Object.assign(form.value, data)
  } finally { loading.value = false }
})

async function save() {
  saving.value = true
  try {
    await updateAgent(route.params.id, form.value)
    ElMessage.success('已保存')
    router.push('/agents')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}
</script>
