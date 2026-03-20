<template>
  <el-card>
    <template #header>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span>交易记录</span>
        <el-button type="primary" size="small" @click="showAdd = true">手动录入</el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="ts_code" label="股票" width="110" />
      <el-table-column prop="trade_date" label="日期" width="110" />
      <el-table-column prop="action" label="操作" width="80">
        <template #default="{ row }">
          <el-tag :type="row.action === 'buy' ? 'danger' : 'success'" size="small">{{ row.action === 'buy' ? '买入' : '卖出' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="100" />
      <el-table-column prop="volume" label="数量" width="100" />
      <el-table-column prop="profit_loss" label="盈亏" width="100">
        <template #default="{ row }">
          <span :style="{ color: (row.profit_loss || 0) >= 0 ? '#67c23a' : '#f56c6c' }">{{ row.profit_loss || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="录入时间" />
    </el-table>

    <el-dialog v-model="showAdd" title="录入交易" width="450">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="股票代码"><el-input v-model="addForm.ts_code" placeholder="600519.SH" /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="addForm.trade_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="操作">
          <el-radio-group v-model="addForm.action">
            <el-radio value="buy">买入</el-radio>
            <el-radio value="sell">卖出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="价格"><el-input-number v-model="addForm.price" :precision="2" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="addForm.volume" :min="1" :step="100" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="doAdd">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTrades, createTrade } from '../../api/index'
import { ElMessage } from 'element-plus'

const list = ref([])
const loading = ref(false)
const showAdd = ref(false)
const addForm = ref({ ts_code: '', trade_date: '', action: 'buy', price: 0, volume: 100 })

async function load() {
  loading.value = true
  try { list.value = await getTrades({ limit: 50 }) } finally { loading.value = false }
}
onMounted(load)

async function doAdd() {
  try {
    await createTrade(addForm.value)
    showAdd.value = false
    ElMessage.success('已录入')
    load()
  } catch { ElMessage.error('录入失败') }
}
</script>
