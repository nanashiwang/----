<template>
  <el-card header="LLM 配置">
    <el-form :model="form" label-width="120px">
      <el-form-item label="提供商">
        <el-select v-model="form.provider">
          <el-option label="OpenAI" value="openai" />
          <el-option label="Anthropic" value="anthropic" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      <el-form-item label="API Base URL">
        <el-input v-model="form.api_base" placeholder="https://api.openai.com/v1" />
      </el-form-item>
      <el-form-item label="API Key">
        <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
      </el-form-item>
      <el-form-item label="模型">
        <el-input v-model="form.model" placeholder="gpt-4" />
      </el-form-item>
      <el-form-item label="温度">
        <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="test" :loading="testing">测试连接</el-button>
      </el-form-item>
    </el-form>
    <el-alert v-if="testResult" :title="testResult.message" :type="testResult.success ? 'success' : 'error'" show-icon />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings, updateSettings, testLLM } from '../../api/settings'
import { ElMessage } from 'element-plus'

const form = ref({ provider: 'openai', api_base: '', api_key: '', model: 'gpt-4', temperature: 0.7 })
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

onMounted(async () => {
  try {
    const res = await getSettings('llm')
    for (const s of res.settings) {
      if (s.key in form.value) form.value[s.key] = s.key === 'temperature' ? parseFloat(s.value) : s.value
    }
  } catch {}
})

async function save() {
  saving.value = true
  try {
    await updateSettings('llm', {
      settings: Object.entries(form.value).map(([key, value]) => ({
        key, value: String(value), is_secret: key === 'api_key'
      }))
    })
    ElMessage.success('已保存')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

async function test() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testLLM(form.value)
  } catch { testResult.value = { success: false, message: '请求失败' } }
  finally { testing.value = false }
}
</script>
