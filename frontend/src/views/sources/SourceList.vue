<template>
  <el-card header="资讯源管理">
    <template #header>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span>资讯源管理</span>
        <el-button type="primary" size="small" @click="showAdd = true">添加资讯源</el-button>
      </div>
    </template>
    <el-table :data="sources" v-loading="loading">
      <el-table-column prop="name" label="名称" width="160" />
      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ row.type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_enabled" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">{{ row.is_enabled ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_fetched" label="上次拉取" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="doFetch(row.id)">拉取</el-button>
          <el-button link type="danger" @click="doDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加资讯源" width="500">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="名称"><el-input v-model="addForm.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="addForm.type">
            <el-option label="RSS" value="rss" />
            <el-option label="网页爬虫" value="crawler" />
            <el-option label="Tushare" value="tushare" />
            <el-option label="微信" value="wechat" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置(JSON)">
          <el-input v-model="addForm.config" type="textarea" :rows="4" placeholder='{"url":"https://..."}' />
        </el-form-item>
        <el-form-item label="拉取间隔(秒)">
          <el-input-number v-model="addForm.fetch_interval" :min="60" :step="600" />
        </el-form-item>
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
import { getSources, createSource, deleteSource, fetchSource } from '../../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const sources = ref([])
const loading = ref(false)
const showAdd = ref(false)
const addForm = ref({ name: '', type: 'rss', config: '', fetch_interval: 3600, is_enabled: true })

async function load() {
  loading.value = true
  try { sources.value = await getSources() } finally { loading.value = false }
}
onMounted(load)

async function doAdd() {
  try {
    await createSource(addForm.value)
    showAdd.value = false
    ElMessage.success('已添加')
    load()
  } catch { ElMessage.error('添加失败') }
}

async function doDelete(id) {
  await ElMessageBox.confirm('确认删除此资讯源？')
  await deleteSource(id)
  ElMessage.success('已删除')
  load()
}

async function doFetch(id) {
  try {
    const res = await fetchSource(id)
    ElMessage[res.success ? 'success' : 'error'](res.success ? `拉取${res.count}条` : res.message)
    load()
  } catch { ElMessage.error('拉取失败') }
}
</script>
