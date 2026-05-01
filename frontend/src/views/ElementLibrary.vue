<template>
  <div class="element-library-page cyber-page">
    <el-card class="sys-page-head" shadow="never">
      <div class="sys-page-head__row">
        <div>
          <h2 class="sys-page-head__title">📚 元素库管理</h2>
          <p class="sys-page-head__sub">
            基于POM架构的页面元素管理，支持模块、页面、元素三层结构
          </p>
        </div>
      </div>
    </el-card>

    <div class="element-library-layout">
      <!-- 左侧：模块和页面树 -->
      <el-card class="tree-panel" shadow="never">
        <div class="panel-header">
          <h3 class="panel-title">模块与页面</h3>
          <el-button type="primary" size="small" @click="handleAddModule">
            <el-icon><Plus /></el-icon>
            新建模块
          </el-button>
        </div>

        <div class="tree-container">
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="treeProps"
            node-key="id"
            :expand-on-click-node="false"
            :highlight-current="true"
            @node-click="handleNodeClick"
            class="element-tree"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <span class="tree-node__icon">
                  <el-icon v-if="data.type === 'module'"><Folder /></el-icon>
                  <el-icon v-else><Document /></el-icon>
                </span>
                <span class="tree-node__label">{{ node.label }}</span>
                <span class="tree-node__actions">
                  <el-button
                    v-if="data.type === 'module'"
                    link
                    size="small"
                    @click.stop="handleAddPage(data)"
                  >
                    <el-icon><Plus /></el-icon>
                  </el-button>
                  <el-button
                    link
                    size="small"
                    @click.stop="handleEdit(data)"
                  >
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button
                    link
                    size="small"
                    type="danger"
                    @click.stop="handleDelete(data)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </span>
              </div>
            </template>
          </el-tree>
        </div>
      </el-card>

      <!-- 右侧：元素列表 -->
      <el-card class="table-panel" shadow="never">
        <div class="panel-header">
          <h3 class="panel-title">
            {{ selectedNode ? `${selectedNode.label} - 元素列表` : '请选择页面' }}
          </h3>
          <div class="panel-actions">
            <el-input
              v-model="searchText"
              placeholder="搜索元素"
              clearable
              style="width: 200px; margin-right: 12px"
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button
              type="primary"
              size="small"
              :disabled="!selectedPage"
              @click="handleAddElement"
            >
              <el-icon><Plus /></el-icon>
              新建元素
            </el-button>
          </div>
        </div>

        <el-table
          :data="elementList"
          stripe
          class="element-table"
          v-loading="loading"
        >
          <el-table-column prop="name" label="元素名称" width="180" />
          <el-table-column prop="locator_type" label="定位方式" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="getLocatorTypeTag(row.locator_type)">
                {{ row.locator_type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="locator_value" label="定位表达式" min-width="250" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link size="small" @click="handleEditElement(row)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button link size="small" type="danger" @click="handleDeleteElement(row)">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 模块对话框 -->
    <el-dialog
      v-model="moduleDialogVisible"
      :title="moduleForm.id ? '编辑模块' : '新建模块'"
      width="500px"
    >
      <el-form :model="moduleForm" label-width="100px">
        <el-form-item label="模块名称" required>
          <el-input v-model="moduleForm.name" placeholder="请输入模块名称" />
        </el-form-item>
        <el-form-item label="父模块">
          <el-select v-model="moduleForm.parent" placeholder="选择父模块（可选）" clearable>
            <el-option
              v-for="mod in allModules"
              :key="mod.id"
              :label="mod.name"
              :value="mod.id"
              :disabled="mod.id === moduleForm.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="moduleForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveModule">保存</el-button>
      </template>
    </el-dialog>

    <!-- 页面对话框 -->
    <el-dialog
      v-model="pageDialogVisible"
      :title="pageForm.id ? '编辑页面' : '新建页面'"
      width="500px"
    >
      <el-form :model="pageForm" label-width="100px">
        <el-form-item label="页面名称" required>
          <el-input v-model="pageForm.name" placeholder="请输入页面名称" />
        </el-form-item>
        <el-form-item label="页面URL">
          <el-input v-model="pageForm.url" placeholder="https://example.com/page" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="pageForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pageDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSavePage">保存</el-button>
      </template>
    </el-dialog>

    <!-- 元素对话框 -->
    <el-dialog
      v-model="elementDialogVisible"
      :title="elementForm.id ? '编辑元素' : '新建元素'"
      width="600px"
    >
      <el-form :model="elementForm" label-width="100px">
        <el-form-item label="元素名称" required>
          <el-input v-model="elementForm.name" placeholder="请输入元素名称" />
        </el-form-item>
        <el-form-item label="定位方式" required>
          <el-select v-model="elementForm.locator_type" placeholder="选择定位方式">
            <el-option label="ID" value="id" />
            <el-option label="Name" value="name" />
            <el-option label="XPath" value="xpath" />
            <el-option label="CSS Selector" value="css" />
            <el-option label="Class Name" value="class" />
            <el-option label="Tag Name" value="tag" />
            <el-option label="Link Text" value="link_text" />
            <el-option label="Partial Link Text" value="partial_link_text" />
          </el-select>
        </el-form-item>
        <el-form-item label="定位表达式" required>
          <el-input
            v-model="elementForm.locator_value"
            type="textarea"
            :rows="3"
            placeholder="请输入定位表达式"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="elementForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="elementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveElement">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, Edit, Delete, Folder, Document, Search } from '@element-plus/icons-vue';
import {
  getUIModulesTree,
  createUIModule,
  updateUIModule,
  deleteUIModule,
  createUIPage,
  updateUIPage,
  deleteUIPage,
  getUIPageElements,
  createUIPageElement,
  updateUIPageElement,
  deleteUIPageElement,
  getAllUIModules
} from '@/api/elementLibrary';

const treeRef = ref(null);
const treeData = ref([]);
const allModules = ref([]);
const selectedNode = ref(null);
const selectedPage = ref(null);
const elementList = ref([]);
const loading = ref(false);
const searchText = ref('');

const treeProps = {
  children: 'children',
  label: 'label'
};

// 模块表单
const moduleDialogVisible = ref(false);
const moduleForm = reactive({
  id: null,
  name: '',
  parent: null,
  description: '',
  project: null
});

// 页面表单
const pageDialogVisible = ref(false);
const pageForm = reactive({
  id: null,
  name: '',
  url: '',
  description: '',
  module: null
});

// 元素表单
const elementDialogVisible = ref(false);
const elementForm = reactive({
  id: null,
  name: '',
  locator_type: 'xpath',
  locator_value: '',
  description: '',
  page: null
});

// 获取当前项目ID
const currentProjectId = computed(() => {
  return localStorage.getItem('current_project_id') || '1';
});

// 加载模块树
const loadTree = async () => {
  try {
    const data = await getUIModulesTree(currentProjectId.value);
    treeData.value = buildTreeData(data);
  } catch (error) {
    ElMessage.error('加载模块树失败');
  }
};

// 加载所有模块（用于下拉选择）
const loadAllModules = async () => {
  try {
    allModules.value = await getAllUIModules(currentProjectId.value);
  } catch (error) {
    console.error('加载模块列表失败', error);
  }
};

// 构建树形数据
const buildTreeData = (modules) => {
  return modules.map(module => ({
    id: `module-${module.id}`,
    label: module.name,
    type: 'module',
    data: module,
    children: [
      ...(module.pages || []).map(page => ({
        id: `page-${page.id}`,
        label: page.name,
        type: 'page',
        data: page
      })),
      ...(module.children ? buildTreeData(module.children) : [])
    ]
  }));
};

// 树节点点击
const handleNodeClick = (data) => {
  selectedNode.value = data;
  if (data.type === 'page') {
    selectedPage.value = data.data;
    loadElements(data.data.id);
  } else {
    selectedPage.value = null;
    elementList.value = [];
  }
};

// 加载元素列表
const loadElements = async (pageId) => {
  loading.value = true;
  try {
    elementList.value = await getUIPageElements(pageId);
  } catch (error) {
    ElMessage.error('加载元素列表失败');
  } finally {
    loading.value = false;
  }
};

// 搜索元素
const handleSearch = () => {
  if (selectedPage.value) {
    loadElements(selectedPage.value.id);
  }
};

// 新建模块
const handleAddModule = () => {
  Object.assign(moduleForm, {
    id: null,
    name: '',
    parent: null,
    description: '',
    project: currentProjectId.value
  });
  moduleDialogVisible.value = true;
};

// 新建页面
const handleAddPage = (moduleData) => {
  Object.assign(pageForm, {
    id: null,
    name: '',
    url: '',
    description: '',
    module: moduleData.data.id
  });
  pageDialogVisible.value = true;
};

// 新建元素
const handleAddElement = () => {
  if (!selectedPage.value) {
    ElMessage.warning('请先选择页面');
    return;
  }
  Object.assign(elementForm, {
    id: null,
    name: '',
    locator_type: 'xpath',
    locator_value: '',
    description: '',
    page: selectedPage.value.id
  });
  elementDialogVisible.value = true;
};

// 编辑
const handleEdit = (data) => {
  if (data.type === 'module') {
    Object.assign(moduleForm, {
      id: data.data.id,
      name: data.data.name,
      parent: data.data.parent,
      description: data.data.description,
      project: currentProjectId.value
    });
    moduleDialogVisible.value = true;
  } else {
    Object.assign(pageForm, {
      id: data.data.id,
      name: data.data.name,
      url: data.data.url,
      description: data.data.description,
      module: data.data.module
    });
    pageDialogVisible.value = true;
  }
};

// 编辑元素
const handleEditElement = (row) => {
  Object.assign(elementForm, {
    id: row.id,
    name: row.name,
    locator_type: row.locator_type,
    locator_value: row.locator_value,
    description: row.description,
    page: row.page
  });
  elementDialogVisible.value = true;
};

// 删除
const handleDelete = async (data) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除${data.type === 'module' ? '模块' : '页面'} "${data.label}" 吗？`,
      '警告',
      { type: 'warning' }
    );

    if (data.type === 'module') {
      await deleteUIModule(data.data.id);
    } else {
      await deleteUIPage(data.data.id);
    }

    ElMessage.success('删除成功');
    loadTree();
    loadAllModules();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
};

// 删除元素
const handleDeleteElement = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除元素 "${row.name}" 吗？`, '警告', {
      type: 'warning'
    });

    await deleteUIPageElement(row.id);
    ElMessage.success('删除成功');
    loadElements(selectedPage.value.id);
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
};

// 保存模块
const handleSaveModule = async () => {
  if (!moduleForm.name) {
    ElMessage.warning('请输入模块名称');
    return;
  }

  try {
    if (moduleForm.id) {
      await updateUIModule(moduleForm.id, moduleForm);
      ElMessage.success('更新成功');
    } else {
      await createUIModule(moduleForm);
      ElMessage.success('创建成功');
    }
    moduleDialogVisible.value = false;
    loadTree();
    loadAllModules();
  } catch (error) {
    ElMessage.error('保存失败');
  }
};

// 保存页面
const handleSavePage = async () => {
  if (!pageForm.name) {
    ElMessage.warning('请输入页面名称');
    return;
  }

  try {
    if (pageForm.id) {
      await updateUIPage(pageForm.id, pageForm);
      ElMessage.success('更新成功');
    } else {
      await createUIPage(pageForm);
      ElMessage.success('创建成功');
    }
    pageDialogVisible.value = false;
    loadTree();
  } catch (error) {
    ElMessage.error('保存失败');
  }
};

// 保存元素
const handleSaveElement = async () => {
  if (!elementForm.name || !elementForm.locator_value) {
    ElMessage.warning('请填写必填项');
    return;
  }

  try {
    if (elementForm.id) {
      await updateUIPageElement(elementForm.id, elementForm);
      ElMessage.success('更新成功');
    } else {
      await createUIPageElement(elementForm);
      ElMessage.success('创建成功');
    }
    elementDialogVisible.value = false;
    loadElements(selectedPage.value.id);
  } catch (error) {
    ElMessage.error('保存失败');
  }
};

// 获取定位方式标签类型
const getLocatorTypeTag = (type) => {
  const typeMap = {
    id: 'success',
    name: 'success',
    xpath: 'warning',
    css: 'primary',
    class: 'info',
    tag: 'info',
    link_text: 'danger',
    partial_link_text: 'danger'
  };
  return typeMap[type] || '';
};

onMounted(() => {
  loadTree();
  loadAllModules();
});
</script>

<style scoped>
.element-library-page {
  min-height: 100vh;
  padding: 0;
}

.sys-page-head {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 255, 218, 0.1);
  border-radius: 12px;
  margin-bottom: 24px;
  backdrop-filter: blur(10px);
}

.sys-page-head__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sys-page-head__title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #00d8ff 0%, #1e5a8e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 8px 0;
}

.sys-page-head__sub {
  color: rgba(148, 163, 184, 0.9);
  font-size: 14px;
  margin: 0;
}

.element-library-layout {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 24px;
  height: calc(100vh - 220px);
}

.tree-panel,
.table-panel {
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(100, 255, 218, 0.15);
  border-radius: 12px;
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(100, 255, 218, 0.1);
  margin-bottom: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.panel-actions {
  display: flex;
  align-items: center;
}

.tree-container {
  flex: 1;
  overflow-y: auto;
}

.element-tree {
  background: transparent;
  color: #e2e8f0;
}

.tree-node {
  display: flex;
  align-items: center;
  flex: 1;
  padding-right: 8px;
}

.tree-node__icon {
  margin-right: 8px;
  color: #00d8ff;
}

.tree-node__label {
  flex: 1;
  font-size: 14px;
}

.tree-node__actions {
  display: none;
}

.tree-node:hover .tree-node__actions {
  display: flex;
  gap: 4px;
}

.element-table {
  flex: 1;
}

/* 深色主题样式 */
:deep(.el-tree) {
  background: transparent;
  color: #e2e8f0;
}

:deep(.el-tree-node__content) {
  background: transparent;
  color: #e2e8f0;
  border-radius: 6px;
  margin-bottom: 4px;
}

:deep(.el-tree-node__content:hover) {
  background: rgba(100, 255, 218, 0.1);
}

:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: rgba(100, 255, 218, 0.2);
  border-left: 3px solid #00d8ff;
}

:deep(.el-table) {
  background: transparent;
  color: #e2e8f0;
}

:deep(.el-table th.el-table__cell) {
  background: rgba(100, 255, 218, 0.1);
  color: #00d8ff;
  border-color: rgba(100, 255, 218, 0.2);
}

:deep(.el-table tr) {
  background: transparent;
}

:deep(.el-table td.el-table__cell) {
  border-color: rgba(100, 255, 218, 0.1);
}

:deep(.el-table__body tr:hover > td) {
  background: rgba(100, 255, 218, 0.05);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: rgba(100, 255, 218, 0.03);
}
</style>
