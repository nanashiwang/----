<template>
  <el-card>
    <template #header>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span>用户管理</span>
        <el-button type="primary" size="small" @click="showAdd = true">添加用户</el-button>
      </div>
    </template>

    <el-table :data="users" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : ''" size="small">{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login" label="上次登录" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="toggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
          <el-button link type="danger" @click="doDelete(row.id)" :disabled="row.role === 'admin'">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加用户" width="400">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="addForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="addForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addForm.role">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
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
import { getUsers, createUser, updateUser, deleteUser } from '../../api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

const users = ref([])
const loading = ref(false)
const showAdd = ref(false)
const addForm = ref({ username: '', password: '', role: 'user' })

async function load() {
  loading.value = true
  try { users.value = await getUsers() } finally { loading.value = false }
}
onMounted(load)

async function doAdd() {
  try {
    await createUser(addForm.value)
    showAdd.value = false
    addForm.value = { username: '', password: '', role: 'user' }
    ElMessage.success('已添加')
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '添加失败') }
}

async function toggleActive(row) {
  await updateUser(row.id, { is_active: !row.is_active })
  ElMessage.success('已更新')
  load()
}

async function doDelete(id) {
  await ElMessageBox.confirm('确认删除此用户？')
  await deleteUser(id)
  ElMessage.success('已删除')
  load()
}
</script>
