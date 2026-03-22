<template>
  <el-card header="Tushare 配置">
    <el-form :model="form" label-width="120px">
      <el-form-item label="Token">
        <el-input v-model="form.token" type="password" show-password placeholder="Tushare Pro Token" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="test" :loading="testing">测试连接</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      v-if="testResult"
      :title="testResult.message"
      :type="testResult.success ? 'success' : 'error'"
      show-icon
      style="margin-top: 12px"
    />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

import { getSettings, updateSettings, testTushare } from '../../api/settings'

const form = ref({ token: '' })
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback
}

onMounted(async () => {
  try {
    const res = await getSettings('tushare')
    const setting = res.settings.find(s => s.key === 'token')
    if (setting) form.value.token = setting.value
  } catch {}
})

async function save() {
  saving.value = true
  try {
    await updateSettings('tushare', {
      settings: [{ key: 'token', value: form.value.token, is_secret: true }],
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
    testResult.value = await testTushare({ token: form.value.token })
  } catch (error) {
    testResult.value = { success: false, message: getErrorMessage(error, '请求失败') }
  } finally {
    testing.value = false
  }
}
</script>
