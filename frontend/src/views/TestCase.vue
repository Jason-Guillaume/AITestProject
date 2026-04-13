<template>
  <div class="testcase-page cyber-page admin-list-page">
    <div class="testcase-layout testcase-layout--module-dock">
      <!-- 左侧：IDE 风格可折叠模块树（宽屏推挤主内容；窄屏覆盖 + 遮罩） -->
      <aside
        class="module-tree-dock"
        :class="{
          'module-tree-dock--wide': isModuleDockWideLayout,
          'module-tree-dock--overlay': !isModuleDockWideLayout,
          'is-expanded': isExpanded,
        }"
      >
        <div class="module-tree-rail" aria-label="模块目录快捷栏">
          <el-tooltip :content="isExpanded ? '收起模块树' : '展开模块树'" placement="right" :show-after="200">
            <el-button
              class="module-tree-rail__expand-btn"
              :class="{ 'is-expanded': isExpanded }"
              text
              type="primary"
              :aria-expanded="isExpanded"
              @click.stop="toggleModuleTreeExpanded"
            >
              <el-icon :size="20"><DArrowLeft v-if="isExpanded" /><DArrowRight v-else /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="模块目录" placement="right" :show-after="200">
            <button
              type="button"
              class="module-tree-rail__btn"
              :class="{ 'is-active': isExpanded }"
              :aria-expanded="isExpanded"
              @click.stop="openModuleTreePanel"
            >
              <el-icon :size="20"><FolderOpened /></el-icon>
            </button>
          </el-tooltip>
          <el-tooltip content="全部用例" placement="right" :show-after="200">
            <button
              type="button"
              class="module-tree-rail__btn"
              :disabled="!currentProjectId"
              @click.stop="clearModuleFilter"
            >
              <el-icon :size="20"><List /></el-icon>
            </button>
          </el-tooltip>
          <el-tooltip content="新建模块" placement="right" :show-after="200">
            <button
              type="button"
              class="module-tree-rail__btn"
              :disabled="!currentProjectId"
              @click.stop="openNewModuleDialog"
            >
              <el-icon :size="20"><Plus /></el-icon>
            </button>
          </el-tooltip>
        </div>

        <div
          class="module-tree-slide"
          :class="{ 'is-open': isExpanded }"
        >
          <el-card class="tc-card tc-card--tree admin-list-card tc-tree-panel" shadow="never">
            <div class="tree-panel__head">
              <div
                class="tree-panel__all-cases"
                :class="{ 'is-active': isAllModulesActive }"
                title="显示当前项目下全部用例"
                role="button"
                tabindex="0"
                @click="clearModuleFilter"
                @keydown.enter.prevent="clearModuleFilter"
              >
                <el-icon class="tree-panel__all-icon"><List /></el-icon>
                <span class="tree-panel__all-label">全部用例</span>
              </div>
              <div class="tree-panel__head-actions">
                <el-tooltip content="新建模块" placement="bottom" :show-after="400">
                  <el-button
                    class="tree-panel__icon-btn"
                    text
                    type="primary"
                    size="small"
                    :disabled="!currentProjectId"
                    @click="openNewModuleDialog"
                  >
                    <el-icon :size="18"><Plus /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip
                  :content="isModuleDockWideLayout ? '收起侧栏' : '关闭模块树'"
                  placement="bottom"
                  :show-after="400"
                >
                  <el-button
                    class="tree-panel__icon-btn"
                    text
                    type="primary"
                    size="small"
                    @click="onTreePanelFoldClick"
                  >
                    <el-icon :size="18"><DArrowLeft v-if="isModuleDockWideLayout" /><Fold v-else /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
            <div class="tc-card__tree-body tree-panel__body">
              <div v-if="!currentProjectId" class="module-tree-empty">
                请先在顶部选择项目，再管理模块与用例。
              </div>
              <el-tree
                v-else-if="moduleTree.length"
                ref="moduleTreeRef"
                :data="moduleTree"
                :props="{ label: 'name', children: 'children' }"
                default-expand-all
                highlight-current
                :expand-on-click-node="false"
                node-key="id"
                :current-node-key="selectedModuleKey"
                @node-click="onModuleClick"
                class="module-el-tree tree-panel-tree"
              >
                <template #default="{ data }">
                  <div class="module-node-row">
                    <span class="module-node module-node--main">
                      <el-icon class="module-node__icon">
                        <Folder v-if="moduleNodeIsFolder(data)" />
                        <Document v-else />
                      </el-icon>
                      <span class="module-node__text">{{ data.name }}</span>
                    </span>
                    <!-- 隐式删除：hover / 当前行 / focus 时显示；阻止冒泡避免触发 node-click -->
                    <span
                      v-if="isModuleTreeRowDeletable(data)"
                      class="module-node-row__actions"
                    >
                      <button
                        type="button"
                        class="module-node__delete-btn"
                        title="删除模块"
                        aria-label="删除模块"
                        @click="onModuleDeleteBtnClick($event, data)"
                      >
                        <el-icon :size="15"><Delete /></el-icon>
                      </button>
                    </span>
                  </div>
                </template>
              </el-tree>
              <div v-else class="module-tree-empty">
                当前项目下暂无模块，请点击工具栏 <strong>+</strong> 新建模块。
              </div>
            </div>
          </el-card>
        </div>
      </aside>

      <div class="testcase-main-shell">
        <!-- 右侧：主内容卡片（遮罩在其后，以便叠在表格上形成分层） -->
        <el-card class="tc-card tc-card--main admin-list-card" shadow="never">
        <!-- 单行工具栏：左侧全部操作按钮，右侧搜索 -->
        <div class="admin-toolbar-row case-toolbar--single">
          <div class="admin-toolbar-row__left">
            <el-tag
              v-if="activeTestCaseTypeLabel"
              type="info"
              effect="plain"
              class="testcase-route-type-tag"
            >
              {{ activeTestCaseTypeLabel }}
            </el-tag>
            <el-button type="primary" :disabled="isRecycleMode" @click="openAiGenerateDialog">
              <el-icon><MagicStick /></el-icon> AI生成测试用例
            </el-button>
            <el-button
              :type="isRecycleMode ? 'info' : 'warning'"
              plain
              @click="toggleRecycleMode"
            >
              {{ isRecycleMode ? '返回用例列表' : '回收站' }}
            </el-button>
            <el-button :disabled="isRecycleMode" @click="openNewCaseDialog">
              <el-icon><Plus /></el-icon> 新增测试用例
            </el-button>
            <el-button :disabled="isRecycleMode" @click="toPlan">
              <el-icon><Tickets /></el-icon> 转测试计划
            </el-button>
            <el-button
              v-if="!isRecycleMode"
              type="success"
              :disabled="selectedCaseIds.length === 0"
              :loading="isExecuting"
              @click="batchExecuteCases"
            >
              <el-icon><VideoPlay /></el-icon> 批量执行
            </el-button>
            <el-button
              v-if="!isRecycleMode"
              type="danger"
              :disabled="selectedCaseIds.length === 0"
              :loading="isDeleting"
              @click="batchDeleteCases"
            >
              <el-icon><Delete /></el-icon> 批量删除
            </el-button>
            <el-button
              v-if="isRecycleMode"
              type="success"
              :disabled="selectedCaseIds.length === 0"
              :loading="isExecuting"
              @click="batchRestoreCases"
            >
              恢复选中
            </el-button>
            <el-button
              v-if="isRecycleMode"
              type="danger"
              :disabled="selectedCaseIds.length === 0"
              :loading="isDeleting"
              @click="batchHardDeleteCases"
            >
              彻底删除选中
            </el-button>
            <span v-if="selectedCaseIds.length > 0" class="case-toolbar__selection-hint">
              已选 {{ selectedCaseIds.length }} 项
            </span>
          </div>
          <div class="admin-toolbar-row__right">
            <el-input
              v-model="searchKw"
              placeholder="请输入用例名称"
              clearable
              class="search-input case-toolbar-search"
            >
              <template #suffix><el-icon><Search /></el-icon></template>
            </el-input>
          </div>
        </div>

        <div
          v-loading="isTableLoading"
          class="admin-table-panel case-table-panel case-table-panel--master"
        >
          <div v-if="!isTableLoading && caseList.length === 0" class="case-table-empty-state">
            <el-empty description="当前条件下暂无测试用例">
              <template #default>
                <p class="case-empty-hint">
                  在左侧选择模块或使用「全部用例」，也可通过 AI 根据需求一键生成结构化用例并导入列表。
                </p>
                <el-button
                  v-if="!isRecycleMode"
                  type="primary"
                  :disabled="!currentProjectId"
                  @click="openAiGenerateDialog"
                >
                  <el-icon class="el-icon--left"><MagicStick /></el-icon>
                  AI 一键生成
                </el-button>
              </template>
            </el-empty>
          </div>
          <div v-else class="case-table-scroll">
            <el-table
              ref="caseTableRef"
              :data="caseList"
              table-layout="fixed"
              :highlight-current-row="isRecycleMode"
              :row-class-name="caseRowClassName"
              stripe
              border
              size="default"
              style="width: 100%"
              class="case-table admin-data-table case-table--fluid case-table--thin"
              row-key="id"
              @selection-change="onCaseSelectionChange"
            >
              <el-table-column type="selection" width="44" fixed="left" align="center" />
              <el-table-column
                label="编号"
                width="100"
                fixed="left"
                align="left"
                show-overflow-tooltip
              >
                <template #default="{ row }">
                  <span class="case-display-id">{{ formatCaseDisplayId(row) }}</span>
                </template>
              </el-table-column>
              <el-table-column
                label="用例名称"
                min-width="250"
                align="left"
                show-overflow-tooltip
                class-name="col-case-name"
              >
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    class="case-name-link case-name-link--master"
                    @click.stop="openCaseDetailDrawer(row)"
                  >
                    {{ row.case_name }}
                  </el-button>
                </template>
              </el-table-column>
              <el-table-column label="等级" width="76" align="center">
                <template #default="{ row }">
                  <el-tag
                    v-if="row.level === 'P0'"
                    size="small"
                    effect="dark"
                    class="tc-tag-p0 tc-tag-p0--vivid"
                  >
                    {{ row.level }}
                  </el-tag>
                  <el-tag
                    v-else-if="row.level === 'P1'"
                    size="small"
                    effect="dark"
                    class="tc-tag-p1 tc-tag-p1--vivid"
                  >
                    {{ row.level }}
                  </el-tag>
                  <el-tag v-else size="small" effect="plain" class="tc-tag-level-muted">
                    {{ row.level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="有效性" width="80" align="center">
                <template #default="{ row }">
                  <el-tag
                    v-if="!row.is_valid"
                    type="danger"
                    size="small"
                    effect="dark"
                    class="tc-tag-invalid"
                  >
                    无效
                  </el-tag>
                  <span v-else class="tc-text-valid">有效</span>
                </template>
              </el-table-column>
              <el-table-column
                label="更新人"
                width="100"
                align="center"
                show-overflow-tooltip
              >
                <template #default="{ row }">{{ row.updater_name || row.creator_name || '—' }}</template>
              </el-table-column>
              <el-table-column
                label="操作"
                width="160"
                fixed="right"
                align="center"
                class-name="col-actions-pinned"
              >
                <template #default="{ row }">
                  <template v-if="!isRecycleMode">
                    <div class="case-row-actions case-row-actions--compact">
                      <el-tooltip v-if="effectiveCaseTestType(row) === 'api'" content="完整执行控制台" placement="top">
                        <el-button
                          link
                          type="warning"
                          class="case-action-icon"
                          @click="openApiConsole(row)"
                        >
                          <el-icon><Lightning /></el-icon>
                        </el-button>
                      </el-tooltip>
                      <el-tooltip content="编辑" placement="top">
                        <el-button link type="primary" class="case-action-icon" @click="editCase(row)">
                          <el-icon><EditPen /></el-icon>
                        </el-button>
                      </el-tooltip>
                      <el-dropdown trigger="click" @command="(cmd) => handleRowMoreCommand(cmd, row)">
                        <el-button link type="primary" size="small" class="more-dropdown-btn">
                          <el-icon><ArrowDown /></el-icon>
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="copy">复制</el-dropdown-item>
                            <el-dropdown-item command="rollback">版本回溯</el-dropdown-item>
                            <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                  </template>
                  <template v-else>
                    <div class="case-row-actions case-row-actions--recycle">
                      <el-button link type="success" size="small" @click="restoreCase(row)">恢复</el-button>
                      <el-button link type="danger" size="small" @click="hardDeleteCase(row)">彻底删除</el-button>
                    </div>
                  </template>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="PAGE_SIZE"
            :total="totalCount"
            layout="total, prev, pager, next, jumper"
            size="large"
            background
            @current-change="onPaginationCurrentChange"
          />
        </div>
        </el-card>
        <Transition name="module-tree-flyout-backdrop-fade">
          <div
            v-if="isExpanded && !isModuleDockWideLayout"
            class="module-tree-flyout-backdrop"
            aria-hidden="true"
            @click="closeModuleTreeFlyoutBackdrop"
          />
        </Transition>
      </div>
    </div>

    <el-drawer
      v-model="caseDetailDrawerVisible"
      :title="caseDetailTitle"
      direction="rtl"
      :size="caseDetailDrawerSize"
      :class="[
        'case-detail-drawer',
        'cyber-drawer-dark',
        'case-detail-drawer--master',
        { 'case-detail-drawer--fullscreen': caseDetailDrawerIsFullscreen },
      ]"
      destroy-on-close
      @closed="onCaseDetailDrawerClosed"
    >
      <template v-if="caseDetailRow">
        <div class="case-detail-drawer-head">
          <div class="case-detail-meta">
            <span class="case-detail-id-tag">{{ formatCaseDisplayId(caseDetailRow) }}</span>
            <el-tag
              v-if="caseDetailRow.is_valid"
              size="small"
              effect="plain"
              class="tc-drawer-status-ghost"
            >
              有效
            </el-tag>
            <el-tag v-else type="danger" size="small" effect="dark">无效</el-tag>
            <span class="tc-drawer-status-text">{{ reviewLabel(caseDetailRow.review_status) }}</span>
            <span class="tc-drawer-status-text">{{
              caseDetailRow.archive_status === 2 ? '已归档' : '未归档'
            }}</span>
          </div>
        </div>
        <el-descriptions
          :column="1"
          border
          size="small"
          class="case-detail-desc"
        >
          <el-descriptions-item label="归属模块" label-class-name="case-detail-desc__label">
            <span class="case-detail-text">{{ moduleLabel(caseDetailRow) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="用例名称" label-class-name="case-detail-desc__label">
            <span class="case-detail-text">{{ caseDetailRow.case_name }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="业务编号" label-class-name="case-detail-desc__label">
            <span class="case-detail-text">{{
              caseDetailRow.case_number != null ? String(caseDetailRow.case_number) : '—'
            }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="等级" label-class-name="case-detail-desc__label">
            <span class="case-detail-text">{{ caseDetailRow.level }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <template v-if="resolvedDrawerType === 'api' && caseDetailRow">
          <div class="case-detail-section-title">接口执行与调试</div>
          <el-skeleton v-if="!drawerHeavyContentMounted" :rows="5" animated class="case-drawer-api-skeleton" />
          <CaseDrawerApiPanel
            v-else
            ref="drawerApiPanelRef"
            :case-row="caseDetailRow"
            :module-id="caseDetailModuleId"
            @after-execute="onDrawerApiAfterExecute"
          />
        </template>

        <template v-else-if="resolvedDrawerType === 'ui-automation'">
          <div class="case-detail-section-title">UI 自动化</div>
          <el-skeleton v-if="!drawerHeavyContentMounted" :rows="3" animated />
          <el-descriptions
            v-else
            :column="1"
            border
            size="small"
            class="case-detail-desc case-detail-desc--typed"
          >
            <el-descriptions-item label="包名 / Package" label-class-name="case-detail-desc__label">
              <span class="case-detail-text">{{ drawerStr(caseDetailRow.app_under_test) }}</span>
            </el-descriptions-item>
            <el-descriptions-item
              label="定位符 (XPath / Selector)"
              label-class-name="case-detail-desc__label"
            >
              <pre class="case-detail-pre">{{ drawerStr(caseDetailRow.primary_locator) }}</pre>
            </el-descriptions-item>
            <el-descriptions-item
              label="动作类型 / 框架"
              label-class-name="case-detail-desc__label"
            >
              <span class="case-detail-text">{{ drawerStr(caseDetailRow.automation_framework) }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </template>

        <template v-else-if="resolvedDrawerType === 'performance'">
          <div class="case-detail-section-title">性能测试</div>
          <el-skeleton v-if="!drawerHeavyContentMounted" :rows="3" animated />
          <el-descriptions
            v-else
            :column="1"
            border
            size="small"
            class="case-detail-desc case-detail-desc--typed"
          >
            <el-descriptions-item label="并发数" label-class-name="case-detail-desc__label">
              <span class="case-detail-text">{{
                caseDetailRow.concurrency != null ? String(caseDetailRow.concurrency) : '—'
              }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="持续时间(s)" label-class-name="case-detail-desc__label">
              <span class="case-detail-text">{{
                caseDetailRow.duration_seconds != null
                  ? String(caseDetailRow.duration_seconds)
                  : '—'
              }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="目标 RPS" label-class-name="case-detail-desc__label">
              <span class="case-detail-text">{{
                caseDetailRow.target_rps != null ? String(caseDetailRow.target_rps) : '—'
              }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </template>

        <template v-else-if="drawerExtraFields.length">
          <div class="case-detail-section-title">扩展信息</div>
          <el-skeleton v-if="!drawerHeavyContentMounted" :rows="4" animated />
          <el-descriptions
            v-else
            :column="1"
            border
            size="small"
            class="case-detail-desc case-detail-desc--typed"
          >
            <el-descriptions-item
              v-for="(f, i) in drawerExtraFields"
              :key="i"
              :label="f.label"
              label-class-name="case-detail-desc__label"
            >
              <pre v-if="isDrawerTailFieldPreformatted(f)" class="case-detail-pre">{{ f.value }}</pre>
              <span v-else class="case-detail-text">{{ f.value }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </template>

      </template>
      <template #footer>
        <div class="case-detail-drawer-footer">
          <template v-if="!isRecycleMode && caseDetailRow">
            <template v-if="resolvedDrawerType === 'api'">
              <el-button
                type="primary"
                :loading="drawerSaveExecuteLoading"
                :disabled="!drawerHeavyContentMounted"
                @click="onDrawerSaveAndExecuteApi"
              >
                保存并执行
              </el-button>
              <el-button @click="openExecutionLogsDialog">查看测试日志</el-button>
              <el-button type="success" plain @click="onDrawerReportHook">回填报告…</el-button>
            </template>
            <template v-else>
              <el-button type="primary" @click="editFromDrawer">编辑用例</el-button>
              <el-button :disabled="!caseDetailRow.id" @click="onDrawerRecordExec">
                记录执行
              </el-button>
            </template>
          </template>
          <el-button @click="caseDetailDrawerVisible = false">关闭</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog
      v-model="executionLogsDialogVisible"
      title="测试执行日志"
      width="720px"
      class="cyber-dialog-dark"
      destroy-on-close
      @opened="loadExecutionLogsForDialog"
    >
      <el-table v-loading="executionLogsLoading" :data="executionLogsRows" size="small" border stripe>
        <el-table-column prop="id" label="ID" width="72" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_passed ? 'success' : 'danger'" size="small">
              {{ row.is_passed ? '通过' : '未通过' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_status_code" label="HTTP" width="80" align="center" />
        <el-table-column prop="duration_ms" label="耗时ms" width="88" align="right" />
        <el-table-column prop="trace_id" label="trace_id" min-width="120" show-overflow-tooltip />
        <el-table-column prop="create_time" label="时间" width="160" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button @click="executionLogsDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="rollbackDialogVisible"
      title="版本回溯"
      width="760px"
      class="cyber-dialog-dark"
      destroy-on-close
      @opened="loadCaseVersionsForRollback"
    >
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="回溯会按所选快照覆盖当前用例内容，并自动生成一条基线快照。"
      />
      <el-table
        v-loading="rollbackVersionsLoading"
        :data="rollbackVersionRows"
        size="small"
        border
        stripe
        style="margin-top: 12px;"
      >
        <el-table-column label="选择" width="70" align="center">
          <template #default="{ row }">
            <el-radio :model-value="selectedRollbackVersionId" :label="row.id" @change="selectedRollbackVersionId = row.id">
              &nbsp;
            </el-radio>
          </template>
        </el-table-column>
        <el-table-column prop="version_label" label="版本标签" width="130" />
        <el-table-column prop="snapshot_no" label="序号" width="80" />
        <el-table-column label="发布版本" width="120">
          <template #default="{ row }">{{ row.release_version_no || "-" }}</template>
        </el-table-column>
        <el-table-column label="创建人" width="120">
          <template #default="{ row }">{{ row.creator_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ formatDate(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="快照用例名" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.snapshot_case_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="步骤数" width="84" align="center">
          <template #default="{ row }">{{ row.snapshot_step_count ?? 0 }}</template>
        </el-table-column>
        <el-table-column label="快照 API 地址" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.snapshot_api_url || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center">
          <template #default="{ row }">
            <TableActionGroup :row="row" :actions="rollbackSnapshotActions" @action="handleRollbackSnapshotAction" />
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="rollbackDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="rollbackSubmitting" @click="submitRollbackFromDialog">
          确认回溯
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="rollbackSnapshotDetailVisible"
      title="快照详情"
      direction="rtl"
      size="48%"
      class="cyber-drawer-dark"
      destroy-on-close
    >
      <template v-if="rollbackSnapshotDetailRow">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="版本标签">
            {{ rollbackSnapshotDetailRow.version_label || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="发布版本">
            {{ rollbackSnapshotDetailRow.release_version_no || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="快照用例名">
            {{ rollbackSnapshotDetailRow.snapshot_case_name || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="步骤数">
            {{ rollbackSnapshotDetailRow.snapshot_step_count ?? 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="API 地址">
            {{ rollbackSnapshotDetailRow.snapshot_api_url || "-" }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="case-detail-section-title">步骤详情</div>
        <el-table :data="rollbackSnapshotSteps" size="small" border stripe>
          <el-table-column prop="step_number" label="#" width="66" align="center" />
          <el-table-column prop="step_desc" label="步骤描述" min-width="180" show-overflow-tooltip />
          <el-table-column prop="expected_result" label="预期结果" min-width="220" show-overflow-tooltip />
        </el-table>

        <div class="case-detail-section-title">当前差异</div>
        <el-empty v-if="rollbackSnapshotDiffRows.length === 0" description="与当前用例一致（或无可对比字段）" />
        <el-table v-else :data="rollbackSnapshotDiffRows" size="small" border stripe>
          <el-table-column prop="field" label="字段" width="150" />
          <el-table-column prop="current" label="当前值" min-width="180" show-overflow-tooltip />
          <el-table-column prop="snapshot" label="快照值" min-width="180" show-overflow-tooltip />
        </el-table>

        <div class="case-detail-section-title">子类型数据</div>
        <pre class="case-detail-pre">{{ rollbackSnapshotSubtypeText }}</pre>
      </template>
      <template #footer>
        <div class="case-detail-drawer-footer">
          <el-button @click="rollbackSnapshotDetailVisible = false">关闭</el-button>
        </div>
      </template>
    </el-drawer>

    <!-- 新建模块 -->
    <el-dialog
      v-model="showModuleDialog"
      title="新建模块"
      width="420px"
      class="cyber-dialog-dark"
      destroy-on-close
      @closed="resetModuleForm"
    >
      <el-form ref="moduleFormRef" :model="newModuleForm" :rules="moduleFormRules" label-width="88px">
        <el-form-item label="模块名称" prop="name">
          <el-input v-model="newModuleForm.name" placeholder="例如：登录页、订单流程" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="上级模块">
          <el-select
            v-model="newModuleForm.parent"
            placeholder="不选则为顶级模块"
            clearable
            filterable
            style="width:100%"
          >
            <el-option
              v-for="m in flatModules"
              :key="m.id"
              :label="moduleParentOptionLabel(m)"
              :value="m.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showModuleDialog = false">取消</el-button>
        <el-button type="primary" :loading="moduleSaving" @click="submitNewModule">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增/编辑弹窗（按测试类型展示扩展字段） -->
    <el-dialog
      v-model="showDialog"
      :title="editingCase ? '编辑用例' : '新增测试用例'"
      :width="caseDialogWidth"
      class="cyber-dialog-dark"
    >
      <el-form ref="formRef" :model="caseForm" :rules="caseRules" label-width="108px">
        <el-form-item label="用例名称" prop="case_name">
          <el-input v-model="caseForm.case_name" placeholder="请输入用例名称" />
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-select v-model="caseForm.level" placeholder="请选择">
            <el-option v-for="l in ['P0','P1','P2','P3']" :key="l" :label="l" :value="l" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属模块" prop="module">
          <el-select v-model="caseForm.module" placeholder="请选择模块" clearable filterable>
            <el-option v-for="m in flatModules" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <template v-if="activeTestCaseType === 'api'">
          <el-form-item label="API 地址" prop="api_url">
            <el-input v-model="caseForm.api_url" placeholder="https://..." />
          </el-form-item>
          <el-form-item label="HTTP 方法" prop="api_method">
            <el-select v-model="caseForm.api_method" placeholder="方法" style="width: 100%">
              <el-option v-for="m in ['GET','POST','PUT','PATCH','DELETE','HEAD']" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="请求头 JSON" prop="api_headers_text">
            <el-input
              v-model="caseForm.api_headers_text"
              type="textarea"
              :rows="3"
              placeholder='例如 {"Content-Type":"application/json"}'
            />
          </el-form-item>
          <el-form-item label="请求体" prop="api_body">
            <el-input v-model="caseForm.api_body" type="textarea" :rows="4" placeholder="可选" />
          </el-form-item>
          <el-form-item label="期望状态码" prop="api_expected_status">
            <el-input-number v-model="caseForm.api_expected_status" :min="100" :max="599" controls-position="right" />
          </el-form-item>
        </template>
        <template v-else-if="activeTestCaseType === 'performance'">
          <el-form-item label="并发数" prop="concurrency">
            <el-input-number v-model="caseForm.concurrency" :min="1" :max="999999" controls-position="right" />
          </el-form-item>
          <el-form-item label="持续时间(s)" prop="duration_seconds">
            <el-input-number v-model="caseForm.duration_seconds" :min="1" :max="86400" controls-position="right" />
          </el-form-item>
          <el-form-item label="目标 RPS" prop="target_rps">
            <el-input-number v-model="caseForm.target_rps" :min="1" :max="9999999" controls-position="right" />
          </el-form-item>
        </template>
        <template v-else-if="activeTestCaseType === 'security'">
          <el-form-item label="攻击面说明" prop="attack_surface">
            <el-input v-model="caseForm.attack_surface" type="textarea" :rows="2" placeholder="范围、入口等" />
          </el-form-item>
          <el-form-item label="工具/模板" prop="tool_preset">
            <el-input v-model="caseForm.tool_preset" placeholder="扫描器或脚本模板" />
          </el-form-item>
          <el-form-item label="风险等级" prop="risk_level">
            <el-select v-model="caseForm.risk_level" placeholder="可选" clearable style="width: 100%">
              <el-option label="高" value="高" />
              <el-option label="中" value="中" />
              <el-option label="低" value="低" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else-if="activeTestCaseType === 'ui-automation'">
          <el-form-item label="应用/包名" prop="app_under_test">
            <el-input v-model="caseForm.app_under_test" placeholder="包名或应用标识" />
          </el-form-item>
          <el-form-item label="主定位符" prop="primary_locator">
            <el-input v-model="caseForm.primary_locator" placeholder="xpath / accessibility id 等" />
          </el-form-item>
          <el-form-item label="自动化框架" prop="automation_framework">
            <el-input v-model="caseForm.automation_framework" placeholder="如 Appium、Playwright" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCase">确定</el-button>
      </template>
    </el-dialog>

    <ApiExecuteConsoleDialog v-model="apiConsoleVisible" :case-row="apiConsoleCaseRow" />

    <TestCaseModal
      v-model="showAiGenerateDialog"
      :flat-modules="flatModules"
      :test-case-type="activeTestCaseType"
      :selected-module-id="selectedModule"
      :project-id="currentProjectId"
      @imported="onAiGenerateImported"
      @append-flat-module="onAppendFlatModuleForAi"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Search,
  MagicStick,
  Tickets,
  Fold,
  DArrowLeft,
  DArrowRight,
  ArrowDown,
  VideoPlay,
  Delete,
  List,
  Folder,
  FolderOpened,
  Document,
  EditPen,
  Lightning,
} from '@element-plus/icons-vue'
import ApiExecuteConsoleDialog from '@/components/api/ApiExecuteConsoleDialog.vue'
import TestCaseModal from '@/components/TestCaseModal.vue'
import TableActionGroup from '@/components/common/TableActionGroup.vue'
import CaseDrawerApiPanel from '@/components/testcase/CaseDrawerApiPanel.vue'
import {
  getCasesApi,
  createCaseApi,
  updateCaseApi,
  deleteCaseApi,
  restoreCaseApi,
  hardDeleteCaseApi,
  batchDeleteCasesApi,
  batchExecuteCasesApi,
  getModulesApi,
  createModuleApi,
  deleteModuleApi,
  getCaseDetailApi,
  getCaseExecutionLogsApi,
  getCaseVersionsApi,
  rollbackCaseVersionApi,
} from '@/api/testcase'
import { TEST_CASE_TYPE_LABEL_ZH } from '@/constants/testCaseTypeLabels'
import { CASE_DETAIL_DRAWER_FULLSCREEN_BREAKPOINT_PX } from '@/constants/caseDrawerUi'
import type { TestCaseRow } from '@/types/testcase'
import {
  getDrawerExtraFields,
  formatCaseDisplayId,
  isDrawerTailFieldPreformatted,
  type DrawerField,
} from '@/composables/useTestCaseTypeColumns'

/** 与侧边栏 / 路由 param 一致，供列表页识别当前测试类型（后续可接入筛选参数） */
const TEST_CASE_ROUTE_TYPES = ['functional', 'api', 'performance', 'security', 'ui-automation']
const rollbackSnapshotActions = [{ key: 'detail', tooltip: '查看详情', icon: Document, type: 'primary' }]

const route = useRoute()
const router = useRouter()

/** ApiTest.vue 通过 provide 固定为 api，避免单独路由缺少 :type 参数 */
const testCaseForcedType = inject<string | null>('testCaseForcedType', null)

function handleRollbackSnapshotAction(action: string, row: TestCaseRow) {
  if (action === 'detail') openRollbackSnapshotDetail(row)
}

const activeTestCaseType = computed(() => {
  const f = testCaseForcedType
  if (f != null && String(f).trim() !== '') return String(f).trim()
  return String(route.params.type || '')
})

const activeTestCaseTypeLabel = computed(
  () => TEST_CASE_TYPE_LABEL_ZH[activeTestCaseType.value] || '',
)

const isRecycleMode = computed(() => String(route.query.recycle || '') === '1')
const recycleFocusCaseId = computed(() => {
  const raw = String(route.query.recycle_case_id || '').trim()
  if (!raw) return null
  const n = Number(raw)
  return Number.isInteger(n) && n > 0 ? n : null
})

watch(
  activeTestCaseType,
  (t) => {
    if (!TEST_CASE_ROUTE_TYPES.includes(t)) {
      router.replace({ name: 'TestCase', params: { type: 'functional' } })
    }
  },
  { immediate: true },
)

/** 视口 ≥ 此宽度时使用侧栏「推挤」布局；更窄时为覆盖式 + 遮罩以保护表格宽度 */
const MODULE_TREE_SIDEBAR_PUSH_BREAKPOINT_PX = 1200
const AITESTA_SIDEBAR_EXPANDED_LS = 'aitesta_sidebar_expanded'
const LEGACY_MODULE_TREE_EXPANDED_LS = 'testcase_module_tree_expanded'

function readModuleTreeExpandedFromStorage(): boolean {
  if (typeof localStorage === 'undefined') return false
  const v = localStorage.getItem(AITESTA_SIDEBAR_EXPANDED_LS)
  if (v === '1') return true
  if (v === '0') return false
  return localStorage.getItem(LEGACY_MODULE_TREE_EXPANDED_LS) === '1'
}

function persistModuleTreeExpanded(v: boolean) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(AITESTA_SIDEBAR_EXPANDED_LS, v ? '1' : '0')
}

const isExpanded = ref(readModuleTreeExpandedFromStorage())

function toggleModuleTreeExpanded() {
  isExpanded.value = !isExpanded.value
  persistModuleTreeExpanded(isExpanded.value)
}

/** 点击「模块目录」图标时展开侧栏（收起由展开按钮或窄屏遮罩完成） */
function openModuleTreePanel() {
  isExpanded.value = true
  persistModuleTreeExpanded(true)
}

function onTreePanelFoldClick() {
  isExpanded.value = false
  persistModuleTreeExpanded(false)
}

function closeModuleTreeFlyoutBackdrop() {
  isExpanded.value = false
  persistModuleTreeExpanded(false)
}

const CURRENT_PROJECT_LS = 'current_project_id'

function readCurrentProjectId() {
  const raw = localStorage.getItem(CURRENT_PROJECT_LS)
  if (raw == null || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

const currentProjectId = ref(readCurrentProjectId())

/** 表格数据加载中（列表请求期间） */
const isTableLoading = ref(false)
const caseList = ref<TestCaseRow[]>([])
/** 表格多选：仅保存选中行的 id */
const selectedCaseIds = ref([])
const caseTableRef = ref(null)
const isExecuting = ref(false)
const isDeleting = ref(false)
const moduleTree = ref([])
const flatModules = ref([])
const searchKw = ref('')
const selectedModule = ref(null)
const moduleTreeRef = ref(null)
const showDialog = ref(false)
const editingCase = ref<TestCaseRow | null>(null)

const caseDetailDrawerVisible = ref(false)
const caseDetailRow = ref<TestCaseRow | null>(null)
const windowInnerWidth = ref(
  typeof window !== 'undefined'
    ? window.innerWidth
    : CASE_DETAIL_DRAWER_FULLSCREEN_BREAKPOINT_PX + 1,
)
/** 抽屉打开后下一帧再挂载重型区块（API 编辑器等），减轻首帧卡顿 */
const drawerHeavyContentMounted = ref(false)

function syncDrawerViewportWidth() {
  if (typeof window !== 'undefined') {
    windowInnerWidth.value = window.innerWidth
  }
}

const isModuleDockWideLayout = computed(
  () => windowInnerWidth.value >= MODULE_TREE_SIDEBAR_PUSH_BREAKPOINT_PX,
)

const caseDetailDrawerSize = computed(() =>
  windowInnerWidth.value < CASE_DETAIL_DRAWER_FULLSCREEN_BREAKPOINT_PX ? '100%' : '45%',
)

const caseDetailDrawerIsFullscreen = computed(
  () => windowInnerWidth.value < CASE_DETAIL_DRAWER_FULLSCREEN_BREAKPOINT_PX,
)

const drawerApiPanelRef = ref<{ saveAndExecute?: () => Promise<void> } | null>(null)
const drawerSaveExecuteLoading = ref(false)
const executionLogsDialogVisible = ref(false)
const executionLogsLoading = ref(false)
const executionLogsRows = ref<Record<string, unknown>[]>([])
const rollbackDialogVisible = ref(false)
const rollbackVersionsLoading = ref(false)
const rollbackSubmitting = ref(false)
const rollbackCaseRow = ref<TestCaseRow | null>(null)
const rollbackVersionRows = ref<Record<string, unknown>[]>([])
const selectedRollbackVersionId = ref<number | null>(null)
const rollbackSnapshotDetailVisible = ref(false)
const rollbackSnapshotDetailRow = ref<Record<string, unknown> | null>(null)

const caseDetailModuleId = computed(() => moduleIdFromRow(caseDetailRow.value))

/** 接口执行控制台（API 用例） */
const apiConsoleVisible = ref(false)
const apiConsoleCaseRow = ref<TestCaseRow | null>(null)

function openApiConsole(row: TestCaseRow) {
  apiConsoleCaseRow.value = row
  apiConsoleVisible.value = true
}

const caseDetailTitle = computed(() =>
  caseDetailRow.value ? `用例详情 · ${caseDetailRow.value.case_name || ''}` : '用例详情',
)

/** 行上 test_type 优先；缺省或仅空白时用当前路由类型（避免抽屉分区误判） */
function effectiveCaseTestType(row: TestCaseRow | null): string {
  const fromRow = String(row?.test_type ?? '').trim()
  if (fromRow) return fromRow
  return String(activeTestCaseType.value || '').trim()
}

/** 与路由/行数据对齐，供抽屉分区（API / UI / 其他） */
const resolvedDrawerType = computed(() => effectiveCaseTestType(caseDetailRow.value))

const drawerExtraFields = computed((): DrawerField[] => {
  const r = caseDetailRow.value
  if (!r) return []
  const tt = effectiveCaseTestType(r)
  if (tt === 'api' || tt === 'ui-automation' || tt === 'performance') return []
  return getDrawerExtraFields({ ...r, test_type: tt })
})

function drawerStr(v: unknown): string {
  if (v == null || v === '') return '—'
  return String(v)
}
const saving = ref(false)
const formRef = ref()

const showModuleDialog = ref(false)
const moduleSaving = ref(false)
const moduleFormRef = ref()
const newModuleForm = ref({ name: '', parent: null })
const moduleFormRules = {
  name: [{ required: true, message: '请输入模块名称', trigger: 'blur' }],
}
/** 服务端分页：当前页（DRF page） */
const currentPage = ref(1)
/** 每页固定 10 条，与后端 page_size 一致（不可切换） */
const PAGE_SIZE = 10
/** 总条数（DRF count） */
const totalCount = ref(0)

function emptyCaseForm() {
  const mid = selectedModule.value
  return {
    case_name: '',
    level: 'P2',
    module: mid == null || mid === '' ? null : mid,
    api_url: '',
    api_method: 'GET',
    api_headers_text: '{}',
    api_body: '',
    api_expected_status: null,
    concurrency: 1,
    duration_seconds: 60,
    target_rps: null,
    attack_surface: '',
    tool_preset: '',
    risk_level: '',
    app_under_test: '',
    primary_locator: '',
    automation_framework: '',
  }
}

const caseForm = ref(emptyCaseForm())

const caseDialogWidth = computed(() =>
  activeTestCaseType.value === 'functional' ? '480px' : '720px',
)

const caseRules = computed(() => {
  const r = {
    case_name: [{ required: true, message: '请输入用例名称', trigger: 'blur' }],
    level: [{ required: true, message: '请选择等级', trigger: 'change' }],
  }
  if (activeTestCaseType.value === 'api') {
    r.api_url = [{ required: true, message: '请输入 API 地址', trigger: 'blur' }]
  }
  return r
})

const showAiGenerateDialog = ref(false)

function openAiGenerateDialog() {
  loadModules()
  showAiGenerateDialog.value = true
}

function onAiGenerateImported() {
  loadModules()
  fetchTestCases()
}

function onAppendFlatModuleForAi(entry: { id: number; name: string; parent: null }) {
  flatModules.value = [...flatModules.value, entry]
}

function openNewModuleDialog() {
  if (!currentProjectId.value) {
    ElMessage.warning('请先在顶部选择项目')
    return
  }
  newModuleForm.value = { name: '', parent: selectedModule.value || null }
  showModuleDialog.value = true
}

function resetModuleForm() {
  newModuleForm.value = { name: '', parent: null }
  moduleFormRef.value?.resetFields?.()
}

function moduleParentOptionLabel(m) {
  const p = m?.parent
  const pid = p == null || p === '' ? null : typeof p === 'object' ? p.id : p
  return pid ? `└ ${m.name}` : m.name
}

async function submitNewModule() {
  try {
    await moduleFormRef.value?.validate()
  } catch {
    return
  }
  const pid = currentProjectId.value
  if (!pid) {
    ElMessage.warning('请先在顶部选择项目')
    return
  }
  const name = (newModuleForm.value.name || '').trim()
  if (!name) return
  const tt = activeTestCaseType.value
  if (!TEST_CASE_ROUTE_TYPES.includes(tt)) {
    ElMessage.warning('当前测试类型无效，请刷新页面后重试')
    return
  }
  moduleSaving.value = true
  try {
    await createModuleApi({
      project: pid,
      name,
      parent: newModuleForm.value.parent || null,
      test_type: tt,
    })
    ElMessage.success('模块已创建')
    showModuleDialog.value = false
    await loadModules()
  } catch (err) {
    const msg =
      err?.response?.data?.detail ||
      err?.response?.data?.msg ||
      err?.response?.data?.non_field_errors?.[0] ||
      err?.message ||
      '创建失败'
    ElMessage.error(typeof msg === 'string' ? msg : '创建失败')
  } finally {
    moduleSaving.value = false
  }
}

function onAppProjectChanged() {
  currentProjectId.value = readCurrentProjectId()
  selectedModule.value = null
  currentPage.value = 1
  clearCaseSelection()
  loadModules()
  fetchTestCases()
}

const selectedModuleKey = computed(() =>
  selectedModule.value != null && selectedModule.value !== ''
    ? selectedModule.value
    : undefined,
)

/** 「全部用例」高亮：已选项目且未选中具体模块 */
const isAllModulesActive = computed(
  () =>
    !!currentProjectId.value &&
    (selectedModule.value == null || selectedModule.value === ''),
)

function moduleNodeIsFolder(data) {
  const ch = data?.children
  return Array.isArray(ch) && ch.length > 0
}

function reviewLabel(v) { return { 1: '未评审', 2: '评审中', 3: '已评审' }[v] || '-' }

watch(
  () => caseDetailDrawerVisible.value && caseDetailRow.value != null,
  (show) => {
    if (show) {
      syncDrawerViewportWidth()
      drawerHeavyContentMounted.value = false
      nextTick(() => {
        if (caseDetailDrawerVisible.value && caseDetailRow.value) {
          drawerHeavyContentMounted.value = true
        }
      })
    } else {
      drawerHeavyContentMounted.value = false
    }
  },
)

async function openCaseDetailDrawer(row: TestCaseRow) {
  syncDrawerViewportWidth()
  caseDetailRow.value = { ...row }
  caseDetailDrawerVisible.value = true
  if (isRecycleMode.value || row?.id == null) return
  try {
    const { data } = await getCaseDetailApi(row.id)
    const payload = data && typeof data === 'object' && 'data' in data ? (data as { data: unknown }).data : data
    if (payload && typeof payload === 'object' && Number((payload as TestCaseRow).id) === Number(row.id)) {
      caseDetailRow.value = payload as TestCaseRow
    }
  } catch {
    /* 保留列表行数据，避免详情 404/权限 时抽屉空白 */
  }
}

function onCaseDetailDrawerClosed() {
  drawerHeavyContentMounted.value = false
  caseDetailRow.value = null
}

async function onDrawerSaveAndExecuteApi() {
  drawerSaveExecuteLoading.value = true
  try {
    await drawerApiPanelRef.value?.saveAndExecute?.()
  } finally {
    drawerSaveExecuteLoading.value = false
  }
}

function onDrawerApiAfterExecute() {
  ElMessage.success('执行完成，可使用「回填报告」打开完整控制台以生成测试报告')
}

function onDrawerReportHook() {
  const r = caseDetailRow.value
  if (!r) return
  caseDetailDrawerVisible.value = false
  nextTick(() => openApiConsole(r))
}

function openExecutionLogsDialog() {
  if (!caseDetailRow.value?.id) return
  executionLogsDialogVisible.value = true
}

async function loadExecutionLogsForDialog() {
  const id = caseDetailRow.value?.id
  if (!id) return
  executionLogsLoading.value = true
  try {
    const { data } = await getCaseExecutionLogsApi(id, { page_size: 50 })
    const raw = data as { results?: unknown[]; data?: unknown[] }
    const payload = Array.isArray(raw?.results)
      ? raw.results
      : Array.isArray(raw?.data)
        ? raw.data
        : Array.isArray(data)
          ? data
          : []
    executionLogsRows.value = (payload as Record<string, unknown>[]).map((row) => {
      const r = row as { create_time?: string; created_at?: string }
      const t = r.created_at ?? r.create_time
      return {
        ...row,
        create_time:
          t != null ? String(t).slice(0, 19).replace('T', ' ') : '—',
      }
    })
  } catch {
    executionLogsRows.value = []
    ElMessage.error('加载执行日志失败')
  } finally {
    executionLogsLoading.value = false
  }
}

async function onDrawerRecordExec() {
  const id = caseDetailRow.value?.id
  if (!id) return
  try {
    await batchExecuteCasesApi({ ids: [id] })
    ElMessage.success('已记录执行次数')
    fetchTestCases()
  } catch {
    ElMessage.error('记录失败')
  }
}

function formatDate(dt) { return dt ? dt.slice(0, 16).replace('T', ' ') : '-' }

function clearCaseSelection() {
  selectedCaseIds.value = []
  caseTableRef.value?.clearSelection?.()
}

function onCaseSelectionChange(rows) {
  selectedCaseIds.value = (rows || []).map((r) => r.id).filter((id) => id != null)
}

function onModuleClick(data) {
  if (!data || data.id == null) return
  selectedModule.value = data.id
  currentPage.value = 1
  clearCaseSelection()
  fetchTestCases()
}

function clearModuleFilter() {
  selectedModule.value = null
  currentPage.value = 1
  nextTick(() => {
    moduleTreeRef.value?.setCurrentKey?.(null)
  })
  clearCaseSelection()
  fetchTestCases()
}

/** 页码变化：重新请求（由 el-pagination 触发） */
function onPaginationCurrentChange() {
  clearCaseSelection()
  fetchTestCases()
}

function toggleRecycleMode() {
  const nextRecycle = !isRecycleMode.value
  router.push({
    name: route.name || 'TestCase',
    params: route.params,
    query: {
      ...route.query,
      recycle: nextRecycle ? '1' : undefined,
      recycle_case_id: undefined,
    },
  })
}

function normalizeListResponse(payload) {
  if (Array.isArray(payload)) return payload
  if (payload?.results && Array.isArray(payload.results)) return payload.results
  if (payload?.data && Array.isArray(payload.data)) return payload.data
  return []
}

function normalizeTotal(payload, rows) {
  const c = payload?.count
  if (typeof c === 'number' && !Number.isNaN(c)) return c
  return rows.length
}

/** 列表请求序号：快速切换路由时丢弃过期的响应，避免表格停在旧 testType 数据 */
let fetchTestCasesSeq = 0
let locatingRecycleCase = false
let recycleLocateFailureNotified = false

function sortRecycleRowsByDeletedAtDesc(rows) {
  if (!Array.isArray(rows)) return []
  return [...rows].sort((a, b) => {
    const ta = Date.parse(a?.deleted_at || '') || 0
    const tb = Date.parse(b?.deleted_at || '') || 0
    return tb - ta
  })
}

function caseRowClassName({ row }) {
  if (!isRecycleMode.value) return ''
  if (!recycleFocusCaseId.value) return ''
  return Number(row?.id) === Number(recycleFocusCaseId.value) ? 'recycle-focus-row' : ''
}

async function focusRecycleCaseRowIfVisible() {
  if (!isRecycleMode.value || !recycleFocusCaseId.value) return false
  const target = caseList.value.find((r) => Number(r?.id) === Number(recycleFocusCaseId.value))
  if (!target) return false
  await nextTick()
  caseTableRef.value?.setCurrentRow?.(target)
  return true
}

async function locateRecycleCaseAcrossPages() {
  if (locatingRecycleCase) return
  if (!isRecycleMode.value || !recycleFocusCaseId.value || !currentProjectId.value) return
  const alreadyVisible = caseList.value.some((r) => Number(r?.id) === Number(recycleFocusCaseId.value))
  if (alreadyVisible) {
    recycleLocateFailureNotified = false
    return
  }
  locatingRecycleCase = true
  try {
    const maxPages = Math.max(1, Math.ceil((Number(totalCount.value) || 0) / PAGE_SIZE))
    let found = false
    for (let p = 1; p <= maxPages; p += 1) {
      if (p === Number(currentPage.value)) continue
      const params = {
        page: p,
        page_size: PAGE_SIZE,
        project: currentProjectId.value,
      }
      const q = (searchKw.value || '').trim()
      if (q) params.search = q
      if (selectedModule.value && !isRecycleMode.value) params.module = selectedModule.value
      const tt = activeTestCaseType.value
      if (TEST_CASE_ROUTE_TYPES.includes(tt)) params.testType = tt
      const { data } = await getCasesApi({ ...params, recycle: "1" })
      const rows = sortRecycleRowsByDeletedAtDesc(normalizeListResponse(data))
      const hit = rows.some((r) => Number(r?.id) === Number(recycleFocusCaseId.value))
      if (!hit) continue
      found = true
      currentPage.value = p
      caseList.value = rows
      totalCount.value = normalizeTotal(data, rows)
      await focusRecycleCaseRowIfVisible()
      ElMessage.success(`已定位到回收站用例 #${recycleFocusCaseId.value}`)
      recycleLocateFailureNotified = false
      return
    }
    if (!found && !recycleLocateFailureNotified) {
      recycleLocateFailureNotified = true
      ElMessage.warning(`未找到回收站用例 #${recycleFocusCaseId.value}（可能不在当前筛选条件内）`)
    }
  } catch {
    // ignore locate failure and keep current page
  } finally {
    locatingRecycleCase = false
  }
}

/**
 * 拉取用例列表（服务端分页 + 可选模块筛选 + 名称搜索）
 * 查询参数与 DRF PageNumberPagination 一致：page、page_size
 */
async function fetchTestCases() {
  const pid = readCurrentProjectId()
  currentProjectId.value = pid
  if (!pid) {
    caseList.value = []
    totalCount.value = 0
    isTableLoading.value = false
    clearCaseSelection()
    return
  }
  const seq = ++fetchTestCasesSeq
  isTableLoading.value = true
  const params = {
    page: currentPage.value,
    page_size: PAGE_SIZE,
    project: pid,
  }
  const q = (searchKw.value || '').trim()
  if (q) params.search = q
  // 回收站须展示「本项目 + 当前测试类型」下全部软删用例；若仍带左侧模块筛选，
  // 会只显示该模块子树内的删除项，其它模块删的用例看不到，表现为「回收站是空的」。
  if (selectedModule.value && !isRecycleMode.value) params.module = selectedModule.value
  const tt = activeTestCaseType.value
  if (TEST_CASE_ROUTE_TYPES.includes(tt)) params.testType = tt
  try {
    const { data } = await getCasesApi({
      ...params,
      ...(isRecycleMode.value ? { recycle: "1" } : {}),
    })
    if (seq !== fetchTestCasesSeq) return
    const rowsRaw = normalizeListResponse(data)
    const rows = isRecycleMode.value ? sortRecycleRowsByDeletedAtDesc(rowsRaw) : rowsRaw
    caseList.value = rows
    totalCount.value = normalizeTotal(data, rows)
    await focusRecycleCaseRowIfVisible()
    await locateRecycleCaseAcrossPages()
  } catch (err) {
    if (seq !== fetchTestCasesSeq) return
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '加载失败'
    ElMessage.error(typeof msg === 'string' ? msg : '加载用例失败')
    caseList.value = []
    totalCount.value = 0
  } finally {
    if (seq === fetchTestCasesSeq) isTableLoading.value = false
  }
}

/**
 * 进入回收站时：清空名称搜索、取消左侧模块筛选（避免仍按子模块收敛导致「回收站是空的」）、回到第 1 页。
 * 含直达 ?recycle=1 场景。
 */
watch(
  isRecycleMode,
  (on) => {
    if (!on) return
    searchKw.value = ''
    currentPage.value = 1
    selectedModule.value = null
    nextTick(() => {
      moduleTreeRef.value?.setCurrentKey?.(null)
    })
  },
  { flush: 'post', immediate: true },
)

/**
 * 同一路由组件复用（/test-case/:type）：必须监听 fullPath，仅监听 params.type 在部分场景下不可靠。
 * flush: post 确保与路由、computed 更新同一节拍。
 */
watch(
  () => route.fullPath,
  () => {
    if (!route.path.startsWith('/test-case/')) return
    const type = String(route.params.type ?? '')
    if (!TEST_CASE_ROUTE_TYPES.includes(type)) return
    currentPage.value = 1
    clearCaseSelection()
    nextTick(() => {
      fetchTestCases()
    })
  },
  { flush: 'post' },
)

/** 搜索关键字防抖后触发列表刷新（服务端 search 参数） */
let searchDebounceTimer = null
watch(searchKw, () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    currentPage.value = 1
    clearCaseSelection()
    fetchTestCases()
  }, 350)
})

/** 批量记录执行：exec_count +1 */
async function batchExecuteCases() {
  const ids = selectedCaseIds.value
  if (!ids.length) return
  isExecuting.value = true
  try {
    const { data } = await batchExecuteCasesApi({ ids })
    const msg = typeof data?.msg === 'string' ? data.msg : `已为 ${ids.length} 条用例记录执行`
    ElMessage.success(msg)
    clearCaseSelection()
    await fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量执行失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量执行失败')
  } finally {
    isExecuting.value = false
  }
}

/** 批量逻辑删除：需二次确认 */
async function batchDeleteCases() {
  const ids = selectedCaseIds.value
  const n = ids.length
  if (!n) return
  try {
    await ElMessageBox.confirm(
      `警告：此操作不可恢复。将删除已选中的 ${n} 条用例，是否继续？`,
      '批量删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  isDeleting.value = true
  try {
    const pid = readCurrentProjectId()
    const { data } = await batchDeleteCasesApi(
      { ids },
      pid != null ? { params: { project: pid } } : undefined,
    )
    const msg = typeof data?.msg === 'string' ? data.msg : `已成功删除 ${n} 条用例`
    ElMessage.success(msg)
    clearCaseSelection()
    await fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '批量删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '批量删除失败')
  } finally {
    isDeleting.value = false
  }
}

async function restoreCase(row) {
  try {
    await restoreCaseApi(row.id)
    ElMessage.success('已恢复')
    clearCaseSelection()
    await fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '恢复失败'
    ElMessage.error(typeof msg === 'string' ? msg : '恢复失败')
  }
}

async function hardDeleteCase(row) {
  try {
    await ElMessageBox.confirm(
      `将彻底删除「${row.case_name}」，且不可恢复，是否继续？`,
      '彻底删除',
      {
        type: 'warning',
        confirmButtonText: '彻底删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  try {
    await hardDeleteCaseApi(row.id)
    ElMessage.success('已彻底删除')
    clearCaseSelection()
    await fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.response?.data?.detail || err?.message || '彻底删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '彻底删除失败')
  }
}

async function batchRestoreCases() {
  const ids = [...selectedCaseIds.value]
  if (!ids.length) return
  isExecuting.value = true
  let ok = 0
  try {
    for (const id of ids) {
      try {
        await restoreCaseApi(id)
        ok += 1
      } catch {
        // keep going
      }
    }
    ElMessage.success(`已恢复 ${ok}/${ids.length} 条`)
    clearCaseSelection()
    await fetchTestCases()
  } finally {
    isExecuting.value = false
  }
}

async function batchHardDeleteCases() {
  const ids = [...selectedCaseIds.value]
  if (!ids.length) return
  try {
    await ElMessageBox.confirm(
      `将彻底删除选中的 ${ids.length} 条用例，且不可恢复，是否继续？`,
      '批量彻底删除',
      {
        type: 'warning',
        confirmButtonText: '彻底删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  isDeleting.value = true
  let ok = 0
  try {
    for (const id of ids) {
      try {
        await hardDeleteCaseApi(id)
        ok += 1
      } catch {
        // keep going
      }
    }
    ElMessage.success(`已彻底删除 ${ok}/${ids.length} 条`)
    clearCaseSelection()
    await fetchTestCases()
  } finally {
    isDeleting.value = false
  }
}

/** 与 loadModules 内 parent 解析一致，供构建树 / 删除子树复用（单一真相，避免分叉） */
function moduleParentIdField(m) {
  const p = m?.parent
  if (p == null || p === '') return null
  return typeof p === 'object' ? p.id : p
}

/** 由扁平列表挂 children 并返回根节点列表，供首次加载与删除后本地重建（保留展开状态优于全量 refetch） */
function rebuildModuleTreeFromFlatList(list) {
  const roots = list.filter((m) => !moduleParentIdField(m))
  roots.forEach((m) => {
    m.children = list.filter((c) => moduleParentIdField(c) === m.id)
  })
  return roots
}

/** 包含根及其所有子孙模块 id，用于前端与子树一并移除（与树筛选语义一致） */
function collectSubtreeModuleIdSet(rootId, list) {
  const rid = Number(rootId)
  const byParent = new Map()
  for (const m of list) {
    const pid = moduleParentIdField(m)
    if (pid == null) continue
    const pk = Number(pid)
    if (!byParent.has(pk)) byParent.set(pk, [])
    byParent.get(pk).push(Number(m.id))
  }
  const out = new Set([rid])
  const queue = [rid]
  while (queue.length) {
    const cur = queue.shift()
    for (const kid of byParent.get(cur) || []) {
      if (!out.has(kid)) {
        out.add(kid)
        queue.push(kid)
      }
    }
  }
  return out
}

/** 对接后端 DELETE /testcase/modules/:id/（软删），命名与需求对齐便于测试替换 */
async function deleteTestModule(moduleId) {
  return deleteModuleApi(moduleId)
}

/**
 * 「全部用例 / 回收站」不在树数据中；若接口将来下发只读节点，用 deletable / is_system 等字段兜底。
 */
function isModuleTreeRowDeletable(data) {
  if (!data || data.id == null) return false
  if (data.deletable === false || data.is_system === true || data.is_virtual === true) return false
  return true
}

function removeModuleSubtreeLocally(rootId) {
  const list = flatModules.value
  const removeIds = collectSubtreeModuleIdSet(rootId, list)
  const deletedNode = list.find((m) => Number(m.id) === Number(rootId))
  const parentIdOfDeleted = deletedNode ? moduleParentIdField(deletedNode) : null
  flatModules.value = list.filter((m) => !removeIds.has(Number(m.id)))
  moduleTree.value = rebuildModuleTreeFromFlatList(flatModules.value)
  return { removeIds, parentIdOfDeleted }
}

/** 删除的节点含当前选中模块时：优先选中父节点（仍存在），否则回退「全部用例」并刷新列表 */
function syncSelectionAfterModuleDeleted(removeIds, parentIdOfDeleted) {
  const sel = selectedModule.value
  if (sel == null || sel === '') return
  if (!removeIds.has(Number(sel))) return
  const p = parentIdOfDeleted != null ? Number(parentIdOfDeleted) : null
  const parentStillExists = p != null && flatModules.value.some((m) => Number(m.id) === p)
  if (parentStillExists) {
    selectedModule.value = p
    nextTick(() => {
      moduleTreeRef.value?.setCurrentKey?.(p)
    })
  } else {
    selectedModule.value = null
    nextTick(() => {
      moduleTreeRef.value?.setCurrentKey?.(null)
    })
  }
  currentPage.value = 1
  clearCaseSelection()
}

function applyLocalStateAfterModuleDeleted(deletedRootId) {
  const { removeIds, parentIdOfDeleted } = removeModuleSubtreeLocally(deletedRootId)
  syncSelectionAfterModuleDeleted(removeIds, parentIdOfDeleted)
}

/**
 * MessageBox beforeClose 内 await 删除接口：确定按钮 loading + 失败不关窗；
 * 成功后本地移除子树并 fetchTestCases，避免全量 loadModules 丢失展开态。
 */
function onModuleDeleteBtnClick(rawEvent, data) {
  rawEvent?.stopPropagation?.()
  rawEvent?.stopImmediatePropagation?.()
  rawEvent?.preventDefault?.()
  if (!isModuleTreeRowDeletable(data)) return
  const moduleId = data.id
  const moduleName = String(data.name || '').trim() || `模块 #${moduleId}`
  const message = `确定要删除模块【${moduleName}】吗？删除后不可恢复，且该模块下的所有测试用例将一并失效或转移。`

  ElMessageBox.confirm(message, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    distinguishCancelAndClose: true,
    beforeClose: async (action, instance, done) => {
      if (action !== 'confirm') {
        done()
        return
      }
      instance.confirmButtonLoading = true
      try {
        await deleteTestModule(moduleId)
        done()
      } catch (err) {
        instance.confirmButtonLoading = false
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.msg ||
          err?.message ||
          '删除模块失败'
        ElMessage.error(typeof msg === 'string' ? msg : '删除模块失败')
      }
    },
  })
    .then(() => {
      applyLocalStateAfterModuleDeleted(moduleId)
      ElMessage.success('模块已删除')
      fetchTestCases()
    })
    .catch(() => {
      /* 取消或关闭 */
    })
}

async function loadModules() {
  const pid = readCurrentProjectId()
  currentProjectId.value = pid
  if (!pid) {
    flatModules.value = []
    moduleTree.value = []
    return
  }
  try {
    const params = { project: pid }
    const tt = activeTestCaseType.value
    if (TEST_CASE_ROUTE_TYPES.includes(tt)) params.testType = tt
    const { data } = await getModulesApi(params)
    flatModules.value = normalizeListResponse(data)
    moduleTree.value = rebuildModuleTreeFromFlatList(flatModules.value)
  } catch (err) {
    flatModules.value = []
    moduleTree.value = []
    const msg = err?.response?.data?.detail || err?.response?.data?.msg || err?.message
    if (msg) ElMessage.error(typeof msg === 'string' ? msg : '加载模块失败')
  }
}

function moduleIdFromRow(row) {
  const m = row?.module
  if (m == null) return null
  return typeof m === 'object' ? m.id : m
}

function moduleLabel(row) {
  const mid = moduleIdFromRow(row)
  if (mid == null) return '—'
  const mod = flatModules.value.find((x) => x.id === mid)
  return mod?.name ?? `模块 #${mid}`
}

function handleRowMoreCommand(cmd, row) {
  if (cmd === 'copy') copyCase(row)
  else if (cmd === 'rollback') rollbackCaseVersion(row)
  else if (cmd === 'delete') delCase(row)
}

async function rollbackCaseVersion(row) {
  rollbackCaseRow.value = row || null
  selectedRollbackVersionId.value = null
  rollbackVersionRows.value = []
  rollbackDialogVisible.value = true
}

function openRollbackSnapshotDetail(row) {
  rollbackSnapshotDetailRow.value = row || null
  rollbackSnapshotDetailVisible.value = true
}

const rollbackSnapshotSteps = computed(() => {
  const s = rollbackSnapshotDetailRow.value?.case_snapshot?.steps
  return Array.isArray(s) ? s : []
})

const rollbackSnapshotSubtypeText = computed(() => {
  const v = rollbackSnapshotDetailRow.value?.case_snapshot?.subtype || {}
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return "{}"
  }
})

function safeStr(v: unknown): string {
  if (v == null) return ""
  if (typeof v === "string") return v
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}

function currentCaseSubtypeField(caseRow: Record<string, unknown>, field: string): unknown {
  return caseRow?.[field]
}

const rollbackSnapshotDiffRows = computed(() => {
  const current = rollbackCaseRow.value as Record<string, unknown> | null
  const snapshot = rollbackSnapshotDetailRow.value?.case_snapshot as Record<string, unknown> | undefined
  if (!current || !snapshot || typeof snapshot !== "object") return []
  const snapshotBase = (snapshot?.base && typeof snapshot.base === "object")
    ? (snapshot.base as Record<string, unknown>)
    : snapshot

  const out: Array<{ field: string; current: string; snapshot: string }> = []
  const baseFields: Array<[string, string]> = [
    ["用例名称", "case_name"],
    ["优先级", "level"],
  ]
  for (const [label, key] of baseFields) {
    const c = safeStr(current[key])
    const s = safeStr(snapshotBase[key])
    if (c !== s) out.push({ field: label, current: c || "-", snapshot: s || "-" })
  }

  const currentStepsCount = Array.isArray(current?.steps) ? current.steps.length : Number(current?.steps_count || 0)
  const snapshotSteps = Array.isArray(snapshot?.steps) ? snapshot.steps : []
  if (Number(currentStepsCount) !== snapshotSteps.length) {
    out.push({
      field: "步骤数量",
      current: String(currentStepsCount || 0),
      snapshot: String(snapshotSteps.length),
    })
  }

  const currentType = String(current?.test_type || "")
  const snapshotSubtype = (snapshot?.subtype && typeof snapshot.subtype === "object")
    ? (snapshot.subtype as Record<string, unknown>)
    : {}
  if (currentType === "api") {
    const apiPairs: Array<[string, string]> = [
      ["API 地址", "api_url"],
      ["HTTP 方法", "api_method"],
      ["期望状态码", "api_expected_status"],
    ]
    for (const [label, key] of apiPairs) {
      const c = safeStr(currentCaseSubtypeField(current, key))
      const s = safeStr(snapshotSubtype[key])
      if (c !== s) out.push({ field: label, current: c || "-", snapshot: s || "-" })
    }
  }
  return out
})

async function loadCaseVersionsForRollback() {
  const id = rollbackCaseRow.value?.id
  if (!id) return
  rollbackVersionsLoading.value = true
  try {
    const { data } = await getCaseVersionsApi(id, { page_size: 100 })
    const raw = data as { results?: unknown[]; data?: unknown[] }
    const rows = Array.isArray(raw?.results)
      ? raw.results
      : Array.isArray(raw?.data)
        ? raw.data
        : Array.isArray(data)
          ? data
          : []
    rollbackVersionRows.value = rows as Record<string, unknown>[]
    if (rollbackVersionRows.value.length > 0) {
      selectedRollbackVersionId.value = Number(rollbackVersionRows.value[0].id)
    }
  } catch (err) {
    rollbackVersionRows.value = []
    const msg = err?.response?.data?.msg || err?.message || "加载快照版本失败"
    ElMessage.error(typeof msg === "string" ? msg : "加载快照版本失败")
  } finally {
    rollbackVersionsLoading.value = false
  }
}

async function submitRollbackFromDialog() {
  const caseId = rollbackCaseRow.value?.id
  if (!caseId) return
  const versionId = Number(selectedRollbackVersionId.value || 0)
  if (!versionId) {
    ElMessage.warning("请先选择一个快照版本")
    return
  }
  rollbackSubmitting.value = true
  try {
    await rollbackCaseVersionApi(caseId, { version_id: versionId })
    ElMessage.success("回溯成功")
    rollbackDialogVisible.value = false
    await fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || "回溯失败"
    ElMessage.error(typeof msg === "string" ? msg : "回溯失败")
  } finally {
    rollbackSubmitting.value = false
  }
}

function buildCasePayloadForApi() {
  const f = { ...caseForm.value }
  delete f.api_headers_text
  if (activeTestCaseType.value === 'api') {
    try {
      const t = (caseForm.value.api_headers_text || '').trim()
      f.api_headers = t ? JSON.parse(t) : {}
    } catch {
      ElMessage.error('请求头 JSON 格式不正确')
      throw new Error('invalid api_headers json')
    }
  }
  f.test_type = activeTestCaseType.value
  return f
}

function openNewCaseDialog() {
  editingCase.value = null
  caseForm.value = emptyCaseForm()
  showDialog.value = true
}

async function copyCase(row) {
  const tt = row.test_type || activeTestCaseType.value
  const base = {
    case_name: `${row.case_name || '用例'}（副本）`,
    level: row.level || 'P2',
    module: moduleIdFromRow(row),
    test_type: tt,
  }
  const typed = {}
  if (tt === 'api') {
    Object.assign(typed, {
      api_url: row.api_url || '',
      api_method: row.api_method || 'GET',
      api_headers: row.api_headers && typeof row.api_headers === 'object' ? { ...row.api_headers } : {},
      api_body: row.api_body || '',
      api_expected_status: row.api_expected_status ?? null,
    })
  } else if (tt === 'performance') {
    Object.assign(typed, {
      concurrency: row.concurrency ?? 1,
      duration_seconds: row.duration_seconds ?? 60,
      target_rps: row.target_rps ?? null,
    })
  } else if (tt === 'security') {
    Object.assign(typed, {
      attack_surface: row.attack_surface || '',
      tool_preset: row.tool_preset || '',
      risk_level: row.risk_level || '',
    })
  } else if (tt === 'ui-automation') {
    Object.assign(typed, {
      app_under_test: row.app_under_test || '',
      primary_locator: row.primary_locator || '',
      automation_framework: row.automation_framework || '',
    })
  }
  try {
    await createCaseApi({
      ...base,
      ...typed,
    })
    ElMessage.success('已复制为新用例')
    fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '复制失败'
    ElMessage.error(typeof msg === 'string' ? msg : '复制失败')
  }
}

function editFromDrawer() {
  const r = caseDetailRow.value
  if (!r) return
  caseDetailDrawerVisible.value = false
  editCase(r)
}

function editCase(row: TestCaseRow) {
  editingCase.value = row
  const headers = row.api_headers
  let apiHeadersText = '{}'
  try {
    apiHeadersText =
      typeof headers === 'object' && headers !== null ? JSON.stringify(headers) : '{}'
  } catch {
    apiHeadersText = '{}'
  }
  caseForm.value = {
    case_name: row.case_name,
    level: row.level || 'P2',
    module: moduleIdFromRow(row),
    api_url: row.api_url || '',
    api_method: row.api_method || 'GET',
    api_headers_text: apiHeadersText,
    api_body: row.api_body || '',
    api_expected_status: row.api_expected_status ?? null,
    concurrency: row.concurrency ?? 1,
    duration_seconds: row.duration_seconds ?? 60,
    target_rps: row.target_rps ?? null,
    attack_surface: row.attack_surface || '',
    tool_preset: row.tool_preset || '',
    risk_level: row.risk_level || '',
    app_under_test: row.app_under_test || '',
    primary_locator: row.primary_locator || '',
    automation_framework: row.automation_framework || '',
  }
  showDialog.value = true
}

async function delCase(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.case_name}」？`, '警告', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteCaseApi(row.id)
    ElMessage.success('删除成功')
    clearCaseSelection()
    fetchTestCases()
  } catch (err) {
    const msg = err?.response?.data?.msg || err?.message || '删除失败'
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

async function submitCase() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = buildCasePayloadForApi()
    if (editingCase.value) {
      await updateCaseApi(editingCase.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createCaseApi(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    editingCase.value = null
    fetchTestCases()
  } catch (err) {
    const status = err?.response?.status
    const data = err?.response?.data || {}
    const conflictCode = Array.isArray(data?.code) ? data.code[0] : data?.code
    if (
      !editingCase.value &&
      status === 409 &&
      String(conflictCode || '') === 'RECYCLE_CONFLICT'
    ) {
      const recycleId = Array.isArray(data?.recycle_case_id)
        ? data.recycle_case_id[0]
        : data?.recycle_case_id
      const goRecycle = await ElMessageBox.confirm(
        `回收站中已存在相似用例（ID: ${recycleId || '未知'}），是否前往回收站恢复？`,
        '检测到回收站冲突',
        {
          type: 'warning',
          confirmButtonText: '前往回收站',
          cancelButtonText: '取消',
        },
      ).then(() => true).catch(() => false)
      if (goRecycle) {
        router.push({
          name: route.name || 'TestCase',
          params: route.params,
          query: { ...route.query, recycle: '1', recycle_case_id: String(recycleId || '') },
        })
      }
      return
    }
    const msg = err?.response?.data?.msg || err?.message || '保存失败'
    ElMessage.error(typeof msg === 'string' ? msg : '保存失败')
  } finally {
    saving.value = false
  }
}

function toPlan() { ElMessage.info('转测试计划功能开发中') }

onMounted(() => {
  window.addEventListener('app:current-project-changed', onAppProjectChanged)
  window.addEventListener('resize', syncDrawerViewportWidth, { passive: true })
  loadModules()
  if (TEST_CASE_ROUTE_TYPES.includes(activeTestCaseType.value)) {
    fetchTestCases()
  }
})

onUnmounted(() => {
  window.removeEventListener('app:current-project-changed', onAppProjectChanged)
  window.removeEventListener('resize', syncDrawerViewportWidth)
})

</script>

<style scoped>
/* ========== 页面骨架：双卡片（全局 admin-list-page 负责 padding / gap） ========== */
.testcase-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  background: transparent;
  border: none;
  border-radius: 0;
  overflow: hidden;
  position: relative;
  z-index: 0;
}

/* 双栏布局与卡片伸缩见 cyber-ui.css（.testcase-layout--module-dock） */

/* ---------- 模块树：IDE 可折叠侧栏（宽屏 Flex 推挤 / 窄屏绝对定位覆盖） ---------- */
.module-tree-dock {
  --aitesta-module-dock-surface: #111827;
  --aitesta-module-rail-w: 52px;
  --aitesta-module-tree-w: 248px;
  position: relative;
  z-index: 52;
  flex-shrink: 0;
  display: flex;
  flex-direction: row;
  align-items: stretch;
  min-height: 0;
  width: var(--aitesta-module-rail-w);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
}

/* 宽屏：侧栏展开时与主内容并排推挤 */
.module-tree-dock.module-tree-dock--wide.is-expanded {
  width: calc(var(--aitesta-module-rail-w) + var(--aitesta-module-tree-w));
}

.module-tree-dock--wide .module-tree-slide {
  position: relative;
  left: auto;
  top: auto;
  bottom: auto;
  z-index: 1;
  flex: 0 0 0;
  width: 0;
  min-width: 0;
  max-width: 0;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
  transform: none;
  transition:
    flex-basis 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    max-width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease;
  will-change: auto;
}

.module-tree-dock--wide.is-expanded .module-tree-slide.is-open {
  flex: 0 0 var(--aitesta-module-tree-w);
  width: var(--aitesta-module-tree-w);
  min-width: var(--aitesta-module-tree-w);
  max-width: var(--aitesta-module-tree-w);
  opacity: 1;
  pointer-events: auto;
  border-radius: 0 12px 12px 0;
  background: rgba(17, 24, 39, 0.55);
}

/* 窄屏：保持窄轨宽度，树面板覆盖在主内容之上 */
.module-tree-dock--overlay {
  width: var(--aitesta-module-rail-w);
}

.module-tree-dock--overlay .module-tree-slide {
  position: absolute;
  left: var(--aitesta-module-rail-w);
  top: 0;
  bottom: 0;
  width: var(--aitesta-module-tree-w);
  z-index: 55;
  flex: none;
  min-width: auto;
  max-width: none;
  overflow: visible;
  transform: translate3d(-100%, 0, 0);
  opacity: 0;
  pointer-events: none;
  transition:
    transform 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.22s ease,
    box-shadow 0.28s ease;
  will-change: transform;
}

.module-tree-dock--overlay .module-tree-slide.is-open {
  transform: translate3d(0, 0, 0);
  opacity: 1;
  pointer-events: auto;
}

.module-tree-dock--overlay.is-expanded .module-tree-slide.is-open {
  box-shadow:
    12px 0 36px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(0, 216, 255, 0.1);
  border-radius: 0 14px 14px 0;
  overflow: hidden;
  background: rgba(17, 24, 39, 0.9);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.module-tree-rail {
  width: 52px;
  flex-shrink: 0;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 0;
  z-index: 60;
  box-sizing: border-box;
  background: var(--aitesta-module-dock-surface);
  border: 1px solid rgba(0, 216, 255, 0.14);
  border-radius: 12px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.28);
}

.module-tree-rail__expand-btn {
  width: 40px;
  height: 40px;
  min-height: 40px;
  padding: 0;
  margin: 0;
  border-radius: 10px;
  color: rgba(0, 216, 255, 0.88) !important;
  background: rgba(255, 255, 255, 0.04) !important;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}

.module-tree-rail__expand-btn:hover:not(:disabled) {
  background: rgba(0, 216, 255, 0.12) !important;
  color: #7aebff !important;
  box-shadow: 0 0 12px rgba(0, 216, 255, 0.15);
}

.module-tree-rail__expand-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 216, 255, 0.45);
}

.module-tree-rail__expand-btn.is-expanded {
  background: rgba(0, 216, 255, 0.14) !important;
  color: #7aebff !important;
  box-shadow: 0 0 14px rgba(0, 216, 255, 0.12);
}

.module-tree-rail__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  color: rgba(0, 216, 255, 0.88);
  background: rgba(255, 255, 255, 0.04);
  transition:
    background 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}

.module-tree-rail__btn:hover:not(:disabled) {
  background: rgba(0, 216, 255, 0.12);
  color: #7aebff;
  box-shadow: 0 0 12px rgba(0, 216, 255, 0.15);
}

.module-tree-rail__btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 216, 255, 0.45);
}

.module-tree-rail__btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.module-tree-rail__btn.is-active {
  background: rgba(0, 216, 255, 0.16);
  color: #00d8ff;
}

/* 共用：树面板为纵向 flex，具体定位由 --wide / --overlay 规则覆盖 */
.module-tree-slide {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.testcase-main-shell {
  z-index: 1;
}

.module-tree-flyout-backdrop {
  position: absolute;
  inset: 0;
  z-index: 50;
  background: rgba(10, 15, 30, 0.42);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  pointer-events: auto;
}

.module-tree-flyout-backdrop-fade-enter-active,
.module-tree-flyout-backdrop-fade-leave-active {
  transition: opacity 0.26s cubic-bezier(0.4, 0, 0.2, 1);
}

.module-tree-flyout-backdrop-fade-enter-from,
.module-tree-flyout-backdrop-fade-leave-to {
  opacity: 0;
}

/* ========== 左侧模块树面板（深色科技风） ========== */
.tc-tree-panel :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding: 12px 12px 14px;
}

.tree-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-shrink: 0;
  padding-bottom: 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(0, 216, 255, 0.12);
}

.tree-panel__all-cases {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
  outline: none;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
  color: rgba(226, 232, 240, 0.92);
  border: 1px solid transparent;
}

.tree-panel__all-cases:hover {
  background: rgba(0, 216, 255, 0.07);
  color: #7aebff;
  border-color: rgba(0, 216, 255, 0.18);
}

.tree-panel__all-cases:focus-visible {
  box-shadow: 0 0 0 2px rgba(0, 216, 255, 0.35);
}

.tree-panel__all-cases.is-active {
  background: linear-gradient(
    135deg,
    rgba(0, 216, 255, 0.16) 0%,
    rgba(0, 120, 180, 0.12) 100%
  );
  border-color: rgba(0, 216, 255, 0.35);
  color: #00d8ff;
  font-weight: 600;
  box-shadow:
    inset 0 0 0 1px rgba(0, 216, 255, 0.08),
    0 4px 14px rgba(0, 0, 0, 0.2);
}

.tree-panel__all-icon {
  flex-shrink: 0;
  font-size: 18px;
  color: inherit;
  opacity: 0.95;
}

.tree-panel__all-label {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-panel__head-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

.tree-panel__icon-btn {
  padding: 6px 8px !important;
  min-height: auto !important;
  border-radius: 8px !important;
  color: rgba(0, 216, 255, 0.85) !important;
}

.tree-panel__icon-btn:hover:not(:disabled) {
  background: rgba(0, 216, 255, 0.12) !important;
  color: #7aebff !important;
}

.tree-panel__icon-btn:disabled {
  opacity: 0.38;
}

.tc-card__tree-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.tree-panel__body {
  margin-top: 2px;
  padding: 8px 6px;
  border-radius: 10px;
  background: rgba(4, 8, 18, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.module-tree-empty {
  padding: 14px 12px;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(226, 232, 240, 0.5);
  text-align: center;
}

.tree-panel-tree {
  --el-tree-node-hover-bg-color: transparent;
  background: transparent !important;
  font-size: 13px;
}

.tree-panel-tree :deep(.el-tree-node__expand-icon) {
  color: rgba(0, 216, 255, 0.55);
  font-size: 14px;
}

.tree-panel-tree :deep(.el-tree-node__expand-icon.is-leaf) {
  color: transparent;
}

.tree-panel-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 36px;
  padding: 6px 8px 6px 6px !important;
  margin: 3px 0;
  border-radius: 8px;
  background: transparent !important;
  border: 1px solid transparent;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.tree-panel-tree :deep(.el-tree-node__content:hover) {
  background: rgba(0, 216, 255, 0.08) !important;
  border-color: rgba(0, 216, 255, 0.12);
}

.tree-panel-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: linear-gradient(
    90deg,
    rgba(0, 216, 255, 0.15) 0%,
    rgba(0, 216, 255, 0.06) 100%
  ) !important;
  border-color: rgba(0, 216, 255, 0.32);
  color: #00d8ff !important;
  box-shadow: 0 0 12px rgba(0, 216, 255, 0.08);
}

.tree-panel-tree :deep(.el-tree-node.is-current > .el-tree-node__content .module-node__icon) {
  color: #00d8ff;
}

.module-node-row {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  gap: 4px;
}

.module-node-row__actions {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  opacity: 0;
  transition: opacity 0.16s ease;
}

.tree-panel-tree :deep(.el-tree-node__content:hover) .module-node-row__actions,
.tree-panel-tree :deep(.el-tree-node__content:focus-within) .module-node-row__actions,
.tree-panel-tree :deep(.el-tree-node.is-current > .el-tree-node__content) .module-node-row__actions {
  opacity: 1;
}

.module-node__delete-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  margin: 0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: rgba(248, 113, 113, 0.55);
  background: transparent;
  transition:
    color 0.15s ease,
    background 0.15s ease;
}

.module-node__delete-btn:hover {
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.14);
}

.module-node__delete-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(248, 113, 113, 0.45);
}

.module-node {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  font-size: 13px;
  color: rgba(226, 232, 240, 0.92);
}

.module-node--main {
  overflow: hidden;
}

.tree-panel-tree :deep(.el-tree-node.is-current > .el-tree-node__content .module-node) {
  color: #00d8ff;
}

.module-node__icon {
  flex-shrink: 0;
  font-size: 16px;
  color: rgba(0, 216, 255, 0.45);
  transition: color 0.18s ease;
}

.tree-panel-tree :deep(.el-tree-node__content:hover .module-node__icon) {
  color: rgba(0, 216, 255, 0.75);
}

.module-node__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.testcase-route-type-tag {
  flex-shrink: 0;
  margin-right: 6px;
  border-color: rgba(0, 216, 255, 0.35);
  color: rgba(0, 216, 255, 0.92);
  background: rgba(0, 216, 255, 0.06);
}

.case-toolbar__selection-hint {
  font-size: 13px;
  color: rgba(0, 216, 255, 0.9);
  white-space: nowrap;
  margin-left: 4px;
}

.case-toolbar-search {
  width: 240px;
  flex-shrink: 0;
}

/* ========== 表格区域 ========== */
.case-table-panel {
  flex: 1;
  min-height: 0;
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.case-table-panel--master {
  position: relative;
}

.case-table-empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  padding: 24px 16px;
}

.case-empty-hint {
  max-width: 420px;
  margin: 0 auto 16px;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(148, 163, 184, 0.95);
}

.case-table--thin {
  min-width: 720px;
}

.case-name-link--master {
  font-weight: 700 !important;
  font-size: 13px;
}

.case-table :deep(.tc-tag-p0--vivid) {
  background: linear-gradient(135deg, #ef4444, #b91c1c) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 700;
}

.case-table :deep(.tc-tag-p1--vivid) {
  background: linear-gradient(135deg, #f59e0b, #d97706) !important;
  border: none !important;
  color: #1c1917 !important;
  font-weight: 700;
}

.tc-text-valid {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.9);
}

.case-row-actions--compact {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  flex-wrap: nowrap;
}

.case-action-icon {
  padding: 4px 6px !important;
  min-height: auto !important;
}

.case-detail-drawer-head {
  margin-bottom: 12px;
}

.case-detail-drawer-head .case-detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
}

.tc-drawer-status-ghost {
  border-color: rgba(148, 163, 184, 0.35) !important;
  background: transparent !important;
  color: rgba(203, 213, 225, 0.85) !important;
}

.tc-drawer-status-text {
  font-size: 12px;
  color: rgba(148, 163, 184, 0.88);
}

.case-detail-drawer-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  width: 100%;
}

.case-detail-drawer--master :deep(.el-drawer__body) {
  padding-bottom: 8px;
}

.case-detail-drawer--fullscreen :deep(.el-drawer__body) {
  padding-left: 12px;
  padding-right: 12px;
}

.case-drawer-api-skeleton {
  padding: 8px 0 16px;
}

.case-table-scroll {
  flex: 1;
  min-height: 0;
  min-width: 0;
  width: 100%;
  overflow: auto;
}

.case-table--fluid {
  min-width: max(100%, 960px);
}

.case-display-id {
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(147, 197, 253, 0.95);
  white-space: nowrap;
}

.case-table :deep(.col-case-name .cell) {
  overflow: hidden;
}

.case-name-link {
  padding: 0 !important;
  height: auto !important;
  font-weight: 600;
  justify-content: flex-start;
  max-width: 100%;
}

.case-name-link :deep(span) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.case-table :deep(.el-table__body .el-table__row) {
  height: auto;
}

.case-table :deep(.el-table__inner-wrapper::before),
.case-table :deep(.el-table__border-left-patch),
.case-table :deep(.el-table__border-bottom-patch) {
  background: rgba(255, 255, 255, 0.06);
}

/* 固定右侧列：避免与主体区色差过大 */
.case-table :deep(.el-table__fixed-right) {
  box-shadow: -6px 0 12px rgba(0, 0, 0, 0.18);
}

.case-table :deep(.el-table__fixed-right-patch) {
  background: rgba(15, 23, 42, 0.98);
}

.case-table :deep(.el-table__body tr.recycle-focus-row > td) {
  background: rgba(230, 162, 60, 0.2) !important;
}

/* 操作区：编辑外露 + 更多 */
.case-row-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  gap: 2px;
  max-width: 100%;
}

.case-row-actions--recycle {
  flex-direction: column;
  gap: 0;
  line-height: 1.2;
}

.case-row-actions--recycle :deep(.el-button) {
  padding: 2px 4px;
  font-size: 12px;
}

.case-action-edit {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 2px !important;
  font-weight: 500;
}

.case-action-edit__icon {
  font-size: 15px;
}

.case-action-edit__text {
  font-size: 13px;
}

.case-action-exec {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 2px !important;
  font-weight: 600;
}

.case-action-exec__icon {
  font-size: 15px;
}

.case-action-exec__text {
  font-size: 13px;
}

.more-dropdown-btn {
  margin-left: 0;
  padding-left: 4px !important;
}

/* Tag 降噪：仅 P0 / 无效 保持强调，其余低饱和灰/柔和绿 */
.case-table :deep(.tc-tag-p0),
.case-table :deep(.tc-tag-p1) {
  font-weight: 600;
}

.case-table :deep(.tc-tag-invalid) {
  font-weight: 600;
}

.case-table :deep(.tc-tag-level-muted) {
  --el-tag-bg-color: rgba(148, 163, 184, 0.12);
  --el-tag-border-color: rgba(148, 163, 184, 0.28);
  --el-tag-text-color: rgba(203, 213, 225, 0.92);
  border-color: rgba(148, 163, 184, 0.28) !important;
  background: rgba(148, 163, 184, 0.1) !important;
  color: rgba(203, 213, 225, 0.92) !important;
}

.case-table :deep(.tc-tag-valid-soft) {
  border-color: rgba(52, 211, 153, 0.22) !important;
  background: rgba(52, 211, 153, 0.08) !important;
  color: rgba(167, 243, 208, 0.88) !important;
}

.case-table :deep(.tc-tag-muted) {
  border-color: rgba(148, 163, 184, 0.22) !important;
  background: rgba(100, 116, 139, 0.1) !important;
  color: rgba(203, 213, 225, 0.78) !important;
}

.case-table :deep(.tc-tag-secondary-status) {
  --el-tag-bg-color: rgba(51, 65, 85, 0.35);
  --el-tag-border-color: rgba(148, 163, 184, 0.35);
  --el-tag-text-color: rgba(186, 198, 216, 0.88);
  border-color: rgba(148, 163, 184, 0.32) !important;
  background: rgba(51, 65, 85, 0.28) !important;
  color: rgba(203, 213, 225, 0.82) !important;
}

.case-table :deep(.tc-tag-review-done) {
  border-color: rgba(74, 222, 128, 0.22) !important;
  background: rgba(74, 222, 128, 0.08) !important;
  color: rgba(187, 247, 208, 0.85) !important;
}

.case-table :deep(.tc-tag-archive-done) {
  border-color: rgba(96, 165, 250, 0.22) !important;
  background: rgba(96, 165, 250, 0.08) !important;
  color: rgba(191, 219, 254, 0.88) !important;
}

.case-table :deep(.col-actions-pinned .cell) {
  padding-left: 6px;
  padding-right: 6px;
}

/* 抽屉详情 */
.case-detail-section-title {
  margin: 16px 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.88);
  letter-spacing: 0.02em;
}

.case-detail-desc--typed {
  margin-top: 0;
}

.case-detail-meta {
  margin-bottom: 12px;
}

.case-detail-id-tag {
  display: inline-block;
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.28);
  color: rgba(125, 211, 252, 0.95);
}

.case-detail-desc {
  margin-bottom: 16px;
}

.case-detail-desc :deep(.case-detail-desc__label) {
  width: 112px;
  font-weight: 600;
  color: rgba(148, 163, 184, 0.95) !important;
  background: rgba(15, 23, 42, 0.6) !important;
}

.case-detail-text {
  color: rgba(226, 232, 240, 0.92);
  word-break: break-word;
  white-space: pre-wrap;
}

.case-detail-pre {
  margin: 0;
  max-height: 240px;
  overflow: auto;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  color: rgba(226, 232, 240, 0.9);
  background: rgba(6, 10, 20, 0.55);
  border-radius: 6px;
  border: 1px solid rgba(0, 255, 255, 0.1);
}

.case-detail-actions {
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  padding-top: 4px;
}
</style>
