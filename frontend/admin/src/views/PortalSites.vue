<template>
  <div>
    <h2>Portal 站点管理</h2>

    <!-- 站点列表 -->
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>已接入的 Portal 站点</span>
          <el-button type="primary" @click="showAddDialog">添加站点</el-button>
        </div>
      </template>

      <el-table :data="sites" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="url" label="地址" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="在线" width="80">
          <template #default="{ row }">
            <el-tag :type="row.online ? 'success' : 'danger'" size="small">
              {{ row.online ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="testConnection(row)">测试</el-button>
            <el-button size="small" type="primary" @click="editSite(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteSite(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑站点' : '添加站点'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="站点名称" />
        </el-form-item>
        <el-form-item label="地址" required>
          <el-input v-model="form.url" placeholder="http://portal-host:8080" />
        </el-form-item>
        <el-form-item label="KEY" required>
          <el-input v-model="form.key" placeholder="与 Portal 端 KEY 相同" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="状态" v-if="isEdit">
          <el-select v-model="form.status">
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSite">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const sites = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = ref({
  name: '',
  url: '',
  key: '',
  description: '',
  status: 'active'
})

const loadSites = async () => {
  loading.value = true
  try {
    const res = await api.get('/api/portal-sites')
    sites.value = res.data
  } catch (error) {
    ElMessage.error('加载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  editId.value = null
  form.value = { name: '', url: '', key: '', description: '', status: 'active' }
  dialogVisible.value = true
}

const editSite = (site) => {
  isEdit.value = true
  editId.value = site.id
  form.value = {
    name: site.name,
    url: site.url,
    key: '',
    description: site.description || '',
    status: site.status
  }
  dialogVisible.value = true
}

const saveSite = async () => {
  if (!form.value.name || !form.value.url || !form.value.key) {
    ElMessage.warning('请填写必填项')
    return
  }

  try {
    if (isEdit.value) {
      await api.put(`/api/portal-sites/${editId.value}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/api/portal-sites', form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    loadSites()
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  }
}

const testConnection = async (site) => {
  try {
    const res = await api.post(`/api/portal-sites/${site.id}/test`)
    if (res.data.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error('连接失败: ' + res.data.message)
    }
  } catch (error) {
    ElMessage.error('测试失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteSite = async (site) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除站点 "${site.name}" 吗？`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    await api.delete(`/api/portal-sites/${site.id}`)
    ElMessage.success('删除成功')
    loadSites()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

onMounted(() => {
  loadSites()
})
</script>
