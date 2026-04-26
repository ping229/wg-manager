<template>
  <div class="config-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VPN配置文件</span>
          <div>
            <el-button @click="copyConfig" :disabled="!config">
              <el-icon><DocumentCopy /></el-icon>
              复制
            </el-button>
            <el-button type="primary" @click="downloadConfig" :disabled="!config">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!config && !loading" description="暂无配置，请先申请VPN">
        <el-button type="primary" @click="$router.push('/')">返回申请</el-button>
      </el-empty>

      <el-input
        v-else
        v-model="config"
        type="textarea"
        :rows="18"
        readonly
        v-loading="loading"
      />

      <div v-if="config" class="qrcode-section">
        <el-divider>二维码配置</el-divider>
        <div class="qrcode-container">
          <canvas ref="qrcodeCanvas"></canvas>
          <p class="qrcode-tip">使用 WireGuard 手机客户端扫描此二维码即可导入配置</p>
        </div>
      </div>
    </el-card>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>客户端下载</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card shadow="hover" class="client-card">
            <el-icon size="32"><Monitor /></el-icon>
            <h4>Windows</h4>
            <a href="https://www.wireguard.com/install/" target="_blank">下载</a>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="client-card">
            <el-icon size="32"><Apple /></el-icon>
            <h4>macOS</h4>
            <a href="https://apps.apple.com/app/wireguard/id1451685025" target="_blank">下载</a>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="client-card">
            <el-icon size="32"><Iphone /></el-icon>
            <h4>iOS</h4>
            <a href="https://apps.apple.com/app/wireguard/id1441195209" target="_blank">下载</a>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="client-card">
            <el-icon size="32"><Cellphone /></el-icon>
            <h4>Android</h4>
            <a href="https://play.google.com/store/apps/details?id=com.wireguard.android" target="_blank">下载</a>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const config = ref('')
const qrcodeCanvas = ref(null)

async function fetchConfig() {
  loading.value = true
  try {
    const response = await api.get('/api/config/download', { responseType: 'text' })
    config.value = response.data
    await nextTick()
    generateQRCode()
  } catch (error) {
    if (error.response?.status !== 404) {
      console.error(error)
    }
  } finally {
    loading.value = false
  }
}

function copyConfig() {
  navigator.clipboard.writeText(config.value)
  ElMessage.success('已复制到剪贴板')
}

async function downloadConfig() {
  try {
    const response = await api.get('/api/config/download', { responseType: 'text' })
    const blob = new Blob([response.data], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'wg-config.conf'
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
  }
}

async function generateQRCode() {
  if (!qrcodeCanvas.value || !config.value) return

  try {
    const QRCode = (await import('qrcode')).default
    await QRCode.toCanvas(qrcodeCanvas.value, config.value, {
      width: 200,
      margin: 2
    })
  } catch (error) {
    console.error('QRCode generation failed:', error)
  }
}

onMounted(fetchConfig)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.qrcode-section {
  text-align: center;
  margin-top: 20px;
}

.qrcode-container {
  display: inline-block;
  padding: 20px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.qrcode-tip {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}

.client-card {
  text-align: center;
  padding: 10px;
}

.client-card h4 {
  margin: 10px 0;
}

.client-card a {
  color: #409eff;
  text-decoration: none;
}
</style>
