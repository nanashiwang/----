<template>
  <el-card header="数据库配置">
    <el-alert title="数据库连接信息通过环境变量或config.yaml配置，此处仅供查看" type="info" show-icon style="margin-bottom:16px" />
    <el-descriptions border :column="1">
      <el-descriptions-item label="MongoDB URI">{{ mongoUri }}</el-descriptions-item>
      <el-descriptions-item label="MongoDB 数据库名">{{ mongoDb }}</el-descriptions-item>
      <el-descriptions-item label="SQLite 路径">{{ sqlitePath }}</el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getSettings } from '../../api/settings'

const mongoUri = ref('-')
const mongoDb = ref('-')
const sqlitePath = ref('-')

onMounted(async () => {
  try {
    const res = await getSettings('database')
    // 数据库配置暂不通过Web修改，仅展示
  } catch {}
})
</script>
