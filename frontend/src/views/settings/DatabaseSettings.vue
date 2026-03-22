<template>
  <div class="page-shell">
    <section class="page-hero page-hero--compact">
      <span class="page-eyebrow">Storage Overview</span>
      <h2>数据库配置</h2>
      <p>当前页面仅做展示，不直接修改数据库连接；实际连接参数仍以环境变量或配置文件为准。</p>
    </section>

    <el-card class="panel-card" shadow="never">
      <template #header>
        <div class="panel-toolbar">
          <div class="panel-toolbar__copy">
            <div class="panel-title">连接信息概览</div>
            <div class="panel-subtitle">统一查看 MongoDB 与 SQLite 的配置来源，便于排查部署问题。</div>
          </div>
          <span class="section-tag">Read Only</span>
        </div>
      </template>

      <el-alert
        title="数据库连接信息通常通过 .env、容器环境变量或 config.yaml 注入。此页面只做展示，不会直接修改生产配置。"
        type="info"
        show-icon
        style="margin-bottom: 18px"
      />

      <el-descriptions :column="1" border>
        <el-descriptions-item label="MongoDB URI">{{ mongoUri }}</el-descriptions-item>
        <el-descriptions-item label="MongoDB 数据库">{{ mongoDb }}</el-descriptions-item>
        <el-descriptions-item label="SQLite 路径">{{ sqlitePath }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

import { getSettings } from '../../api/settings'

const mongoUri = ref('由环境变量或配置文件提供')
const mongoDb = ref('由环境变量或配置文件提供')
const sqlitePath = ref('由环境变量或配置文件提供')

onMounted(async () => {
  try {
    const res = await getSettings('database')
    for (const item of res.settings || []) {
      if (item.key === 'mongo_uri') mongoUri.value = item.value
      if (item.key === 'mongo_db') mongoDb.value = item.value
      if (item.key === 'sqlite_path') sqlitePath.value = item.value
    }
  } catch {}
})
</script>
