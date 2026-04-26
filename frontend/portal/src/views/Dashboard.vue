<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>我的VPN配置</span>
          </template>
          <div v-if="peerInfo" class="peer-info">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="节点">{{ peerInfo.node?.name }}</el-descriptions-item>
              <el-descriptions-item label="分配IP">{{ peerInfo.peer?.address }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDate(peerInfo.peer?.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="上传限速">
                {{ peerInfo.peer?.upload_limit ? peerInfo.peer.upload_limit + ' Mbps' : '不限速' }}
              </el-descriptions-item>
              <el-descriptions-item label="下载限速">
                {{ peerInfo.peer?.download_limit ? peerInfo.peer.download_limit + ' Mbps' : '不限速' }}
              </el-descriptions-item>
            </el-descriptions>
            <div style="margin-top: 20px;">
              <el-button type="primary" @click="$router.push('/config')">查看配置文件</el-button>
              <el-button @click="downloadConfig">下载配置</el-button>
              <el-button type="danger" @click="deleteConfig">删除配置</el-button>
            </div>
          </div>
          <el-empty v-else description="暂无VPN配置">
            <el-button type="primary" @click="showCreateDialog">申请VPN配置</el-button>
          </el-empty>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header>
            <span>可用节点</span>
          </template>
          <el-table :data="nodes" v-loading="loading" max-height="300">
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="endpoint" label="地址" />
            <el-table-column label="限速" width="130">
              <template #default="{ row }">
                <span v-if="row.default_upload_limit > 0 || row.default_download_limit > 0" class="limit-text">
                  ↑{{ row.default_upload_limit || 0 }} / ↓{{ row.default_download_limit || 0 }}
                </span>
                <span v-else class="text-muted">不限速</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.online ? 'success' : 'danger'" size="small">
                  {{ row.online ? '在线' : '离线' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px;">
      <template #header>
        <span>使用说明</span>
      </template>
      <el-steps :active="3" finish-status="success">
        <el-step title="注册账号" description="填写注册信息等待审批" />
        <el-step title="审批通过" description="管理员审核通过后可登录" />
        <el-step title="获取配置" description="选择节点获取VPN配置" />
        <el-step title="导入客户端" description="将配置导入WireGuard客户端" />
      </el-steps>
    </el-card>

    <!-- 选择节点对话框 -->
    <el-dialog v-model="createDialogVisible" title="申请VPN配置" width="450px">
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="选择节点">
          <el-select v-model="createForm.node_id" placeholder="请选择节点" style="width: 100%">
            <el-option
              v-for="node in nodes"
              :key="node.id"
              :label="getNodeLabel(node)"
              :value="node.id"
              :disabled="!node.online"
            >
              <div class="node-option">
                <span>{{ node.name }} ({{ node.endpoint }})</span>
                <span class="node-limit">
                  <template v-if="node.default_upload_limit > 0 || node.default_download_limit > 0">
                    限速: ↑{{ node.default_upload_limit || 0 }}/↓{{ node.default_download_limit || 0 }} Mbps
                  </template>
                  <template v-else>不限速</template>
                </span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createPeer" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const creating = ref(false)
const peerInfo = ref(null)
const nodes = ref([])
const createDialogVisible = ref(false)

const createForm = reactive({
  node_id: null
})

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

function getNodeLabel(node) {
  const limitText = (node.default_upload_limit > 0 || node.default_download_limit > 0)
    ? ` [限速: ↑${node.default_upload_limit || 0}/↓${node.default_download_limit || 0} Mbps]`
    : ' [不限速]'
  return `${node.name} (${node.endpoint})${limitText}`
}

async function fetchData() {
  loading.value = true
  try {
    // 获取节点列表
    const nodesRes = await api.get('/api/nodes')
    nodes.value = nodesRes.data

    // 获取配置信息
    try {
      const peerRes = await api.get('/api/config')
      peerInfo.value = peerRes.data
    } catch (error) {
      if (error.response?.status === 404) {
        peerInfo.value = null
      }
    }
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  const onlineNodes = nodes.value.filter(n => n.online)
  if (onlineNodes.length === 0) {
    ElMessage.warning('暂无在线节点')
    return
  }
  createForm.node_id = onlineNodes[0]?.id || null
  createDialogVisible.value = true
}

async function createPeer() {
  if (!createForm.node_id) {
    ElMessage.warning('请选择节点')
    return
  }

  creating.value = true
  try {
    await api.post('/api/config/generate', { node_id: createForm.node_id })
    ElMessage.success('VPN配置已创建')
    createDialogVisible.value = false
    fetchData()
  } catch (error) {
    console.error(error)
  } finally {
    creating.value = false
  }
}

async function downloadConfig() {
  try {
    const response = await api.get('/api/config/download', { responseType: 'text' })
    const blob = new Blob([response.data], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `wg-${peerInfo.value.node?.name || 'config'}.conf`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
  }
}

async function deleteConfig() {
  try {
    await ElMessageBox.confirm('确定要删除当前VPN配置吗？', '确认', { type: 'warning' })
    await api.delete('/api/config')
    ElMessage.success('配置已删除')
    peerInfo.value = null
    fetchData()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

onMounted(fetchData)
</script>

<style scoped>
.peer-info {
  padding: 10px 0;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}

.limit-text {
  font-size: 12px;
  color: #606266;
}

.node-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.node-limit {
  font-size: 12px;
  color: #909399;
}
</style>
