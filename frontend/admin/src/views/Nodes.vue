<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点管理</span>
          <div class="header-actions">
            <el-button type="success" :disabled="selectedRows.length === 0" @click="batchEnable">
              批量启用 ({{ selectedRows.length }})
            </el-button>
            <el-button type="warning" :disabled="selectedRows.length === 0" @click="batchDisable">
              批量禁用 ({{ selectedRows.length }})
            </el-button>
            <el-button @click="exportNodes">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
            <el-button @click="importDialogVisible = true">
              <el-icon><Upload /></el-icon>
              导入
            </el-button>
            <el-button type="primary" @click="showDialog()">
              <el-icon><Plus /></el-icon>
              添加节点
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="nodes"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        ref="tableRef"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="endpoint" label="地址" />
        <el-table-column prop="wg_port" label="端口" width="80" />
        <el-table-column prop="address_pool" label="地址池" />
        <el-table-column label="KEY" width="150">
          <template #default="{ row }">
            <div class="key-cell" v-if="row.key">
              <span class="key-text">{{ maskKey(row.key) }}</span>
              <el-button size="small" text @click="copyToClipboard(row.key)">复制</el-button>
            </div>
            <span v-else class="text-muted">未设置</span>
          </template>
        </el-table-column>
        <el-table-column label="客户端" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.online">{{ row.peer_count }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="在线状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.online ? 'success' : 'danger'" size="small">
              {{ row.online ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'primary' : 'info'" size="small">
              {{ row.status === 'active' ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row)">查看</el-button>
            <el-button size="small" @click="showAccessControl(row)">访问控制</el-button>
            <el-button size="small" @click="showDialog(row)">编辑</el-button>
            <el-button
              size="small"
              :type="row.status === 'active' ? 'warning' : 'success'"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-button size="small" type="danger" @click="deleteNode(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="节点详情" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="名称">{{ detailData.name }}</el-descriptions-item>
        <el-descriptions-item label="公网地址">{{ detailData.endpoint }}</el-descriptions-item>
        <el-descriptions-item label="WG端口">{{ detailData.wg_port }}</el-descriptions-item>
        <el-descriptions-item label="接口名">{{ detailData.wg_interface }}</el-descriptions-item>
        <el-descriptions-item label="地址池">{{ detailData.address_pool }}</el-descriptions-item>
        <el-descriptions-item label="客户端数">
          <span v-if="detailData.online">{{ detailData.peer_count }}</span>
          <span v-else class="text-muted">节点离线</span>
        </el-descriptions-item>
        <el-descriptions-item label="DNS">{{ detailData.dns }}</el-descriptions-item>
        <el-descriptions-item label="MTU">{{ detailData.mtu }}</el-descriptions-item>
        <el-descriptions-item label="Keepalive">{{ detailData.keepalive }}秒</el-descriptions-item>
        <el-descriptions-item label="上传限速">
          {{ detailData.default_upload_limit > 0 ? detailData.default_upload_limit + ' Mbps' : '不限速' }}
        </el-descriptions-item>
        <el-descriptions-item label="下载限速">
          {{ detailData.default_download_limit > 0 ? detailData.default_download_limit + ' Mbps' : '不限速' }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="detailData.status === 'active' ? 'primary' : 'info'" size="small">
            {{ detailData.status === 'active' ? '已启用' : '已禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Agent URL">
          <div class="copy-field">
            <span>{{ detailData.api_url }}</span>
            <el-button size="small" text @click="copyToClipboard(detailData.api_url)">复制</el-button>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="KEY">
          <div class="copy-field">
            <span class="key-text">{{ detailData.key || '未设置' }}</span>
            <el-button v-if="detailData.key" size="small" text @click="copyToClipboard(detailData.key)">复制</el-button>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="公钥">
          <div class="copy-field">
            <span class="public-key">{{ detailData.public_key }}</span>
            <el-button size="small" text @click="copyToClipboard(detailData.public_key)">复制</el-button>
          </div>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 访问控制对话框 -->
    <el-dialog v-model="accessControlVisible" title="访问控制" width="550px">
      <div class="access-control-header">
        <span>设置禁止访问此节点的用户名模式（支持正则表达式）</span>
      </div>
      <div class="pattern-input">
        <el-input
          v-model="newPattern"
          placeholder="输入用户名或正则表达式，如: test.* 或 ^user[0-9]+$"
          @keyup.enter="addPattern"
        >
          <template #append>
            <el-button @click="addPattern" :disabled="!newPattern">添加</el-button>
          </template>
        </el-input>
      </div>
      <div class="pattern-list" v-if="patterns.length > 0">
        <el-tag
          v-for="(pattern, index) in patterns"
          :key="index"
          closable
          type="warning"
          class="pattern-tag"
          @close="removePattern(index)"
        >
          {{ pattern }}
        </el-tag>
      </div>
      <el-empty v-else description="暂无访问限制" :image-size="60" />
      <template #footer>
        <el-button @click="accessControlVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAccessControl" :loading="savingAccess">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editId ? '编辑节点' : '添加节点'" width="550px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="节点名称" />
        </el-form-item>
        <el-form-item label="公网地址" prop="endpoint">
          <el-input v-model="form.endpoint" placeholder="如: vpn.example.com" />
        </el-form-item>
        <el-form-item label="WG端口" prop="wg_port">
          <el-input-number v-model="form.wg_port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="接口名" prop="wg_interface">
          <el-input v-model="form.wg_interface" placeholder="如: wg0" />
        </el-form-item>
        <el-form-item label="地址池" prop="address_pool">
          <el-input v-model="form.address_pool" placeholder="如: 10.100.0.0/24" />
        </el-form-item>
        <el-form-item label="DNS">
          <el-input v-model="form.dns" placeholder="默认: 8.8.8.8" />
        </el-form-item>
        <el-form-item label="MTU">
          <el-input-number v-model="form.mtu" :min="1200" :max="1500" />
        </el-form-item>
        <el-form-item label="Keepalive">
          <el-input-number v-model="form.keepalive" :min="0" :max="600" />
        </el-form-item>
        <el-form-item label="上传限速">
          <el-input-number v-model="form.default_upload_limit" :min="0" :max="10000" />
          <span class="form-tip">Mbps, 0表示不限速</span>
        </el-form-item>
        <el-form-item label="下载限速">
          <el-input-number v-model="form.default_download_limit" :min="0" :max="10000" />
          <span class="form-tip">Mbps, 0表示不限速</span>
        </el-form-item>
        <el-form-item label="Agent URL" prop="api_url">
          <el-input v-model="form.api_url" placeholder="如: http://192.168.1.100:8082" />
        </el-form-item>
        <el-form-item label="KEY" prop="key">
          <el-input v-model="form.key" placeholder="与 Agent 端配置的 KEY 相同" />
          <span class="form-tip">用于 Admin 与 Agent 之间的认证</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入节点" width="600px">
      <div class="import-tips">
        <p>请上传 JSON 格式的节点配置文件，或直接粘贴 JSON 内容</p>
        <el-input
          v-model="importJson"
          type="textarea"
          :rows="10"
          placeholder='粘贴 JSON 内容，格式如：
{
  "nodes": [
    {
      "name": "节点名称",
      "endpoint": "vpn.example.com",
      "wg_port": 51820,
      "address_pool": "10.100.0.0/24",
      "api_url": "http://192.168.1.100:8082",
      "key": "your-key-here",
      ...
    }
  ]
}'
        />
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="importNodes" :loading="importing" :disabled="!importJson">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Download, Upload } from '@element-plus/icons-vue'
import { api } from '../api'

const loading = ref(false)
const submitting = ref(false)
const importing = ref(false)
const nodes = ref([])
const selectedRows = ref([])
const tableRef = ref()
const dialogVisible = ref(false)
const detailVisible = ref(false)
const editId = ref(null)
const formRef = ref()
const detailData = ref({})

// 导入相关
const importDialogVisible = ref(false)
const importJson = ref('')

// 访问控制相关
const accessControlVisible = ref(false)
const savingAccess = ref(false)
const currentNode = ref(null)
const patterns = ref([])
const newPattern = ref('')

const form = reactive({
  name: '',
  endpoint: '',
  wg_port: 51820,
  wg_interface: 'wg0',
  address_pool: '',
  dns: '8.8.8.8',
  mtu: 1420,
  keepalive: 25,
  default_upload_limit: 0,
  default_download_limit: 0,
  api_url: '',
  key: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入地址', trigger: 'blur' }],
  address_pool: [{ required: true, message: '请输入地址池', trigger: 'blur' }],
  api_url: [{ required: true, message: '请输入Agent URL', trigger: 'blur' }],
  key: [{ required: true, message: '请输入 KEY', trigger: 'blur' }]
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function maskKey(key) {
  if (!key || key.length < 8) return key || ''
  return key.substring(0, 4) + '****' + key.substring(key.length - 4)
}

function getBlockedCount(node) {
  if (!node.blocked_patterns) return 0
  try {
    const arr = JSON.parse(node.blocked_patterns)
    return Array.isArray(arr) ? arr.length : 0
  } catch {
    return 0
  }
}

async function fetchNodes() {
  loading.value = true
  try {
    const { data } = await api.get('/api/nodes')
    nodes.value = data
  } finally {
    loading.value = false
  }
}

function showDetail(node) {
  detailData.value = node
  detailVisible.value = true
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function showAccessControl(node) {
  currentNode.value = node
  try {
    patterns.value = node.blocked_patterns ? JSON.parse(node.blocked_patterns) : []
  } catch {
    patterns.value = []
  }
  newPattern.value = ''
  accessControlVisible.value = true
}

function addPattern() {
  if (newPattern.value && !patterns.value.includes(newPattern.value)) {
    patterns.value.push(newPattern.value)
    newPattern.value = ''
  }
}

function removePattern(index) {
  patterns.value.splice(index, 1)
}

async function saveAccessControl() {
  savingAccess.value = true
  try {
    await api.put(`/api/nodes/${currentNode.value.id}`, {
      blocked_patterns: JSON.stringify(patterns.value)
    })
    ElMessage.success('访问控制设置已保存')
    accessControlVisible.value = false
    fetchNodes()
  } finally {
    savingAccess.value = false
  }
}

function showDialog(node = null) {
  editId.value = node?.id || null
  if (node) {
    Object.assign(form, {
      name: node.name,
      endpoint: node.endpoint,
      wg_port: node.wg_port,
      wg_interface: node.wg_interface,
      address_pool: node.address_pool,
      dns: node.dns,
      mtu: node.mtu,
      keepalive: node.keepalive,
      default_upload_limit: node.default_upload_limit || 0,
      default_download_limit: node.default_download_limit || 0,
      api_url: node.api_url,
      key: node.key || ''
    })
  } else {
    Object.assign(form, {
      name: '',
      endpoint: '',
      wg_port: 51820,
      wg_interface: 'wg0',
      address_pool: '',
      dns: '8.8.8.8',
      mtu: 1420,
      keepalive: 25,
      default_upload_limit: 0,
      default_download_limit: 0,
      api_url: '',
      key: ''
    })
  }
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
    submitting.value = true

    if (editId.value) {
      await api.put(`/api/nodes/${editId.value}`, form)
      ElMessage.success('更新成功')
    } else {
      await api.post('/api/nodes', form)
      ElMessage.success('添加成功')
    }

    dialogVisible.value = false
    fetchNodes()
  } catch (error) {
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(node) {
  const action = node.status === 'active' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}此节点吗?`, '确认', { type: 'warning' })
    await api.post(`/api/nodes/${node.id}/${node.status === 'active' ? 'disable' : 'enable'}`)
    ElMessage.success(`${action}成功`)
    fetchNodes()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

async function deleteNode(node) {
  try {
    await ElMessageBox.confirm('确定要删除此节点吗?', '确认', { type: 'warning' })
    try {
      await api.delete(`/api/nodes/${node.id}`)
      ElMessage.success('删除成功')
      fetchNodes()
    } catch (error) {
      if (error.response?.status === 400) {
        const detail = error.response.data.detail
        if (detail.includes('Peer')) {
          try {
            await ElMessageBox.confirm(
              `${detail}\n\n是否强制删除？这将清空该节点下的所有Peer。`,
              '强制删除确认',
              { type: 'warning', confirmButtonText: '强制删除', cancelButtonText: '取消' }
            )
            await api.delete(`/api/nodes/${node.id}?force=true`)
            ElMessage.success('节点及所有Peer已删除')
            fetchNodes()
          } catch (e) {
            if (e !== 'cancel') console.error(e)
          }
          return
        }
      }
      throw error
    }
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

// 批量操作
async function batchEnable() {
  try {
    await ElMessageBox.confirm(`确定要启用选中的 ${selectedRows.value.length} 个节点吗?`, '批量启用', { type: 'info' })
    const nodeIds = selectedRows.value.map(n => n.id)
    const { data } = await api.post('/api/nodes/batch-enable', { node_ids: nodeIds })
    ElMessage.success(data.message)
    selectedRows.value = []
    fetchNodes()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

async function batchDisable() {
  try {
    await ElMessageBox.confirm(
      `确定要禁用选中的 ${selectedRows.value.length} 个节点吗? 禁用后将清空该节点下的所有Peer。`,
      '批量禁用',
      { type: 'warning' }
    )
    const nodeIds = selectedRows.value.map(n => n.id)
    const { data } = await api.post('/api/nodes/batch-disable', { node_ids: nodeIds })
    ElMessage.success(data.message)
    selectedRows.value = []
    fetchNodes()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

// 导出
async function exportNodes() {
  try {
    const { data } = await api.get('/api/nodes/export')
    const jsonStr = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonStr], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `nodes_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${data.count} 个节点`)
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 导入
async function importNodes() {
  if (!importJson.value.trim()) {
    ElMessage.warning('请输入 JSON 内容')
    return
  }

  importing.value = true
  try {
    const jsonData = JSON.parse(importJson.value)
    const nodesData = jsonData.nodes || [jsonData]
    const { data } = await api.post('/api/nodes/import', { nodes: nodesData })
    ElMessage.success(data.message)
    if (data.errors && data.errors.length > 0) {
      console.warn('导入错误:', data.errors)
    }
    importDialogVisible.value = false
    importJson.value = ''
    fetchNodes()
  } catch (error) {
    if (error instanceof SyntaxError) {
      ElMessage.error('JSON 格式错误')
    } else {
      ElMessage.error(error.response?.data?.detail || '导入失败')
    }
  } finally {
    importing.value = false
  }
}

onMounted(fetchNodes)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.text-muted {
  color: #909399;
  font-size: 12px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.copy-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.key-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.key-text {
  font-family: monospace;
  font-size: 12px;
}

.public-key {
  font-family: monospace;
  font-size: 12px;
  word-break: break-all;
}

.access-control-header {
  margin-bottom: 16px;
  color: #606266;
  font-size: 14px;
}

.pattern-input {
  margin-bottom: 16px;
}

.pattern-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pattern-tag {
  font-family: monospace;
}

.import-tips {
  margin-bottom: 16px;
}

.import-tips p {
  margin-bottom: 10px;
  color: #606266;
}
</style>
