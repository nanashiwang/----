<template>
  <div class="page-shell">
    <section class="page-hero page-hero--compact">
      <span class="page-eyebrow">Data Source Access</span>
      <h2>Tushare 配置</h2>
      <p>维护行情与基础数据授权 Token，建议保存后立刻做一次连接验证。</p>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">数据授权参数</div>
            <div class="panel-subtitle">该配置会影响行情拉取、指标计算与部分策略输入。</div>
          </div>
          <span class="section-tag">Tushare Pro</span>
        </div>
      </template>

      <el-form :model="form" label-width="120px" class="settings-form">
        <el-form-item label="Token">
          <el-input
            v-model="form.token"
            type="password"
            show-password
            :placeholder="tokenPlaceholder"
          />
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

import { getSettings, testTushare, updateSettings } from '../../api/settings'

const form = ref({ token: '' })
const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)
const tokenPlaceholder = ref('Tushare Pro Token')

function getErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback
}

onMounted(async () => {
  try {
    const res = await getSettings('tushare')
    const setting = res.settings.find(item => item.key === 'token')
    if (setting) {
      if (setting.value && setting.value.includes('****')) {
        tokenPlaceholder.value = `${setting.value}（已保存，如需更换请重新输入）`
        form.value.token = ''
      } else {
        form.value.token = setting.value
      }
    }
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
