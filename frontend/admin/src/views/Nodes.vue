<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点管理</span>
          <el-button type="primary" @click="showDialog()">
            <el-icon><Plus /></el-icon>
            添加节点
          </el-button>
        </div>
      </template>

      <el-table :data="nodes" v-loading="loading">
        <el-table-column prop="name" label="名称" width="120" />
        <el-table-column prop="endpoint" label="地址" />
        <el-table-column prop="wg_port" label="端口" width="80" />
        <el-table-column prop="address_pool" label="地址池" />
        <el-table-column label="限速" width="120">
          <template #default="{ row }">
            <span v-if="row.default_upload_limit > 0 || row.default_download_limit > 0">
              ↑{{ row.default_upload_limit || 0 }} / ↓{{ row.default_download_limit || 0 }} Mbps
            </span>
            <span v-else class="text-muted">不限速</span>
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
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="syncNode(row)">同步</el-button>
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
        <el-form-item label="API密钥" prop="api_key">
          <el-input v-model="form.api_key" placeholder="Agent API密钥" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const submitting = ref(false)
const nodes = ref([])
const dialogVisible = ref(false)
const editId = ref(null)
const formRef = ref()

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
  api_key: ''
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  endpoint: [{ required: true, message: '请输入地址', trigger: 'blur' }],
  address_pool: [{ required: true, message: '请输入地址池', trigger: 'blur' }],
  api_url: [{ required: true, message: '请输入Agent URL', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入API密钥', trigger: 'blur' }]
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
      api_key: ''
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
      api_key: ''
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

async function syncNode(node) {
  try {
    const { data } = await api.post(`/api/nodes/${node.id}/sync`)
    if (data.synced) {
      ElMessage.success('同步成功')
    } else {
      ElMessage.warning(`同步失败: ${data.error}`)
    }
  } catch (error) {
    console.error(error)
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
    await api.delete(`/api/nodes/${node.id}`)
    ElMessage.success('删除成功')
    fetchNodes()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
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

.text-muted {
  color: #909399;
  font-size: 12px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>
