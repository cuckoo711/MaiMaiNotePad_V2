<template>
	<fs-page>
		<el-card>
			<fs-crud ref="crudRef" v-bind="crudBinding" @selection-change="handleSelectionChange">
				<!-- 自定义操作按钮 -->
				<template #actionbar-right>
					<!-- 已选中数量显示 -->
					<span v-if="hasSelection" style="margin-right: 12px; color: #409eff; font-size: 14px;">
						已选中 {{ selectedCount }} 条
					</span>
					<!-- 批量封禁 -->
					<el-button
						v-if="auth('ban:BatchBan')"
						type="danger"
						:disabled="!hasSelection"
						@click="handleBatchBan"
					>
						批量封禁
					</el-button>
					<!-- 批量解除 -->
					<el-button
						v-if="auth('ban:BatchUnban')"
						type="success"
						:disabled="!hasSelection"
						@click="handleBatchUnban"
					>
						批量解除
					</el-button>
					<!-- 导出 -->
					<el-button
						v-if="auth('ban:Export')"
						type="primary"
						@click="handleExport"
					>
						导出
					</el-button>
				</template>

				<!-- 自定义列显示 -->
				<template #cell_is_active="scope">
					<el-tag :type="scope.row.is_active ? 'success' : 'danger'" size="small">
						{{ scope.row.is_active ? '正常' : '封禁中' }}
					</el-tag>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #row-handle="{ row }">
					<el-button
						v-if="auth('ban:Unban') && !row.is_active"
						link
						size="small"
						type="success"
						@click="handleUnban(row)"
					>
						解除封禁
					</el-button>
					<el-button
						v-if="auth('ban:ModifyDuration') && !row.is_active"
						link
						size="small"
						type="primary"
						@click="handleModifyDuration(row)"
					>
						修改时长
					</el-button>
					<el-button
						v-if="auth('ban:Detail')"
						link
						size="small"
						@click="handleViewDetail(row)"
					>
						查看详情
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 添加/编辑封禁对话框 -->
		<ModerationDialog
			v-model:visible="dialogVisible"
			:type="'ban'"
			:mode="dialogMode"
			@success="handleDialogSuccess"
		/>

		<!-- 修改时长对话框 -->
		<DurationModifyDialog
			v-model:visible="durationDialogVisible"
			:user-id="currentUserId"
			:current-duration="currentDuration"
			:operation-type="'ban'"
			@success="handleDialogSuccess"
		/>

		<!-- 操作日志抽屉 -->
		<ModerationLogDrawer
			v-model:visible="logDrawerVisible"
			:user-id="currentUserId"
		/>

		<!-- 导出对话框 -->
		<el-dialog
			v-model="exportDialogVisible"
			title="导出数据"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-form label-width="100px">
				<el-form-item label="导出格式">
					<el-radio-group v-model="exportForm.format">
						<el-radio label="excel">Excel (.xlsx)</el-radio>
						<el-radio label="csv">CSV (.csv)</el-radio>
					</el-radio-group>
				</el-form-item>
				<el-form-item label="导出范围">
					<el-tag v-if="hasSelection" type="info">
						导出选中的 {{ selectedCount }} 条记录
					</el-tag>
					<el-tag v-else type="info">导出全部记录</el-tag>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="exportDialogVisible = false">取消</el-button>
				<el-button type="primary" @click="executeExport">导出</el-button>
			</template>
		</el-dialog>

		<!-- 批量操作对话框 -->
		<BatchOperationDialog
			v-model:visible="batchDialogVisible"
			:type="batchOperationType"
			@success="handleDialogSuccess"
		/>
	</fs-page>
</template>

<script lang="ts" setup name="contentModerationBan">
import { ref, onMounted } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from '/@/api/moderation';
import { auth } from '/@/utils/authFunction';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox } from 'element-plus';
import ModerationDialog from '../components/ModerationDialog.vue';
import DurationModifyDialog from '../components/DurationModifyDialog.vue';
import ModerationLogDrawer from '../components/ModerationLogDrawer.vue';
import BatchOperationDialog from '../components/BatchOperationDialog.vue';

// crud 组件的 ref
const crudRef = ref();
// crud 配置的 ref
const crudBinding = ref();
// 暴露的方法
const { crudExpose } = useExpose({ crudRef, crudBinding });
// crud 配置
const { crudOptions } = createCrudOptions({ crudExpose });
// 初始化 crud 配置
const { resetCrudOptions } = useCrud({ crudExpose, crudOptions });

// 选中的行
const selectedRows = ref<any[]>([]);
const selectedCount = ref(0);
const hasSelection = ref(false);

// 对话框状态
const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'modify'>('create');
const durationDialogVisible = ref(false);
const logDrawerVisible = ref(false);
const exportDialogVisible = ref(false);
const batchDialogVisible = ref(false);
const batchOperationType = ref<'ban' | 'unban'>('ban');

// 当前操作的用户
const currentUserId = ref(0);
const currentDuration = ref<string | undefined>(undefined);

// 导出表单
const exportForm = ref({
	format: 'excel',
});

/**
 * 处理选择变化
 */
const handleSelectionChange = (selection: any[]) => {
	selectedRows.value = selection;
	selectedCount.value = selection.length;
	hasSelection.value = selection.length > 0;
};

/**
 * 解除封禁
 */
const handleUnban = (row: any) => {
	ElMessageBox.prompt('请输入解除原因（可选）', '解除封禁', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		inputType: 'textarea',
	})
		.then(async ({ value }) => {
			try {
				const res = await api.unbanUser({
					user_id: row.id,
					reason: value || undefined,
				});
				successMessage(res.msg || '解除封禁成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('解除封禁失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {});
};

/**
 * 修改时长
 */
const handleModifyDuration = (row: any) => {
	currentUserId.value = row.id;
	currentDuration.value = row.locked_until;
	durationDialogVisible.value = true;
};

/**
 * 查看详情
 */
const handleViewDetail = (row: any) => {
	currentUserId.value = row.id;
	logDrawerVisible.value = true;
};

/**
 * 批量封禁
 */
const handleBatchBan = () => {
	if (!hasSelection.value) {
		errorMessage('请先选择要封禁的用户');
		return;
	}
	if (selectedCount.value > 20) {
		errorMessage('批量操作最多支持20个用户');
		return;
	}
	batchOperationType.value = 'ban';
	batchDialogVisible.value = true;
};

/**
 * 批量解除
 */
const handleBatchUnban = () => {
	if (!hasSelection.value) {
		errorMessage('请先选择要解除的用户');
		return;
	}
	if (selectedCount.value > 20) {
		errorMessage('批量操作最多支持20个用户');
		return;
	}
	
	ElMessageBox.confirm(
		`确定要批量解除 ${selectedCount.value} 个用户的封禁吗？`,
		'批量解除封禁',
		{
			confirmButtonText: '确定',
			cancelButtonText: '取消',
			type: 'warning',
		}
	)
		.then(async () => {
			try {
				const userIds = selectedRows.value.map((row: any) => row.id);
				const res = await api.batchUnban({ user_ids: userIds });
				successMessage(`批量解除成功：成功 ${res.success} 个，失败 ${res.failed} 个`);
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('批量解除失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {});
};

/**
 * 导出
 */
const handleExport = () => {
	exportDialogVisible.value = true;
};

/**
 * 执行导出
 */
const executeExport = async () => {
	try {
		const params: any = {
			type: 'ban',
			format: exportForm.value.format,
		};
		
		// 如果有选中的行，只导出选中的
		if (hasSelection.value) {
			params.user_ids = selectedRows.value.map((row: any) => row.id).join(',');
		}
		
		await api.exportData(params);
		successMessage('导出成功');
		exportDialogVisible.value = false;
	} catch (error: any) {
		errorMessage('导出失败：' + (error.message || '未知错误'));
	}
};

/**
 * 对话框成功回调
 */
const handleDialogSuccess = () => {
	crudExpose.doRefresh();
};

// 页面打开后获取列表数据
onMounted(() => {
	crudExpose.doRefresh();
});
</script>

<style lang="scss" scoped>
.el-card {
	height: 100%;
}
</style>
