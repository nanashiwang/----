<template>
  <div class="page-shell">
    <section class="page-hero page-hero--compact">
      <span class="page-eyebrow">Model Access</span>
      <h2>LLM 配置</h2>
      <p>统一维护模型供应商、网关地址与访问密钥，并在保存前完成连通性验证。</p>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">模型接入参数</div>
            <div class="panel-subtitle">建议优先使用稳定的 API 网关，并保存前先进行一次测试连接。</div>
          </div>
          <span class="section-tag">{{ form.provider.toUpperCase() }}</span>
        </div>
      </template>

      <el-form :model="form" label-width="120px" class="settings-form">
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
          <el-input v-model="form.model" placeholder="gpt-4 / gpt-5.2-codex" />
        </el-form-item>

        <el-form-item label="温度">
          <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
        </el-form-item>

        <el-form-item>
          <div class="settings-actions">
            <el-button type="primary" @click="save" :loading="saving">保存配置</el-button>
            <el-button @click="test" :loading="testing">测试连接</el-button>
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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { getSettings, testLLM, updateSettings } from '../../api/settings'

const form = ref({
  provider: 'openai',
  api_base: '',
  api_key: '',
  model: 'gpt-4',
  temperature: 0.7,
})
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback
}

onMounted(async () => {
  try {
    const res = await getSettings('llm')
    for (const setting of res.settings) {
      if (!(setting.key in form.value)) continue
      form.value[setting.key] = setting.key === 'temperature'
        ? parseFloat(setting.value)
        : setting.value
    }
  } catch {}
})

async function save() {
  saving.value = true
  try {
    await updateSettings('llm', {
      settings: Object.entries(form.value).map(([key, value]) => ({
        key,
        value: String(value),
        is_secret: key === 'api_key',
      })),
    })
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await testLLM(form.value)
  } catch (error) {
    testResult.value = { success: false, message: getErrorMessage(error, '请求失败') }
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.settings-form {
  max-width: 920px;
}

.settings-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
