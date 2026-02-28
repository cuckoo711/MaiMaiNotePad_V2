<!-- 上传记录管理页面 -->
<template>
	<fs-page>
		<el-card>
			<fs-crud ref="crudRef" v-bind="crudBinding" @selection-change="handleSelectionChange">
				<!-- 自定义操作按钮 -->
				<template #actionbar-right>
					<!-- 已选中数量显示 -->
					<span v-if="hasSelection" style="margin-right: 12px; color: #409eff; font-size: 14px;">
						{{ formatSelectionText(selectedCount) }}
					</span>
					<!-- 批量审核通过 -->
					<el-button
						v-if="auth('upload_record:Approve')"
						type="success"
						:disabled="!hasSelection"
						@click="handleBatchApprove"
					>
						批量审核通过
					</el-button>
					<!-- 批量审核拒绝 -->
					<el-button
						v-if="auth('upload_record:Approve')"
						type="warning"
						:disabled="!hasSelection"
						@click="handleBatchReject"
					>
						批量审核拒绝
					</el-button>
					<!-- 导出 -->
					<el-button
						v-if="auth('upload_record:Export')"
						type="primary"
						@click="handleAdvancedExport"
					>
						导出
					</el-button>
				</template>

				<!-- 审核状态标签 -->
				<template #cell_status="scope">
					<el-tag :type="statusTagType(scope.row.status)">
						{{ statusText(scope.row.status) }}
					</el-tag>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #row-handle="{ row }">
					<el-button
						v-if="auth('upload_record:View')"
						type="text"
						size="small"
						@click="handleViewDetail(row)"
					>
						查看详情
					</el-button>
					<el-button
						v-if="auth('upload_record:Approve') && row.status === 'pending'"
						type="text"
						size="small"
						@click="handleApprove(row)"
					>
						审核通过
					</el-button>
					<el-button
						v-if="auth('upload_record:Approve') && row.status === 'pending'"
						type="text"
						size="small"
						@click="handleReject(row)"
					>
						审核拒绝
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 上传记录详情对话框 -->
		<el-dialog
			v-model="detailDialogVisible"
			title="上传记录详情"
			width="600px"
		>
			<el-descriptions :column="1" border>
				<el-descriptions-item label="记录ID">{{ currentRecord?.id }}</el-descriptions-item>
				<el-descriptions-item label="上传者">{{ currentRecord?.uploader_name || '-' }}</el-descriptions-item>
				<el-descriptions-item label="目标类型">{{ targetTypeText(currentRecord?.target_type) }}</el-descriptions-item>
				<el-descriptions-item label="名称">{{ currentRecord?.name || '-' }}</el-descriptions-item>
				<el-descriptions-item label="描述">
					<div style="white-space: pre-wrap;">{{ currentRecord?.description || '-' }}</div>
				</el-descriptions-item>
				<el-descriptions-item label="审核状态">
					<el-tag :type="statusTagType(currentRecord?.status)">
						{{ statusText(currentRecord?.status) }}
					</el-tag>
				</el-descriptions-item>
				<el-descriptions-item label="创建时间">{{ formatDateTime(currentRecord?.create_datetime) }}</el-descriptions-item>
			</el-descriptions>
			<template #footer>
				<el-button @click="detailDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<!-- 导出配置对话框 -->
		<el-dialog
			v-model="advancedExportDialogVisible"
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
					<el-tag v-if="exportForm.ids && exportForm.ids.length > 0" type="info">
						导出选中的 {{ exportForm.ids.length }} 条记录
					</el-tag>
					<el-tag v-else type="info">导出全部记录</el-tag>
				</el-form-item>
				<el-form-item label="导出字段">
					<el-checkbox-group v-model="exportForm.fields">
						<el-checkbox
							v-for="field in exportFields"
							:key="field.key"
							:label="field.key"
						>
							{{ field.label }}
						</el-checkbox>
					</el-checkbox-group>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="advancedExportDialogVisible = false">取消</el-button>
				<el-button type="primary" @click="executeExport()">导出</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts" setup name="contentUploadRecord">
import { ref, onMounted, watch } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from './api';
import { auth } from '/@/utils/authFunction';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox } from 'element-plus';
import dayjs from 'dayjs';
import { useBatchOperation, formatSelectionText } from '/@/composables/content/useBatchOperation';
import { useDataExport, type ExportField } from '/@/composables/content/useDataExport';

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

// 上传记录模块可导出字段列表
const exportFields: ExportField[] = [
	{ key: 'name', label: '名称' },
	{ key: 'uploader_name', label: '上传者' },
	{ key: 'target_type', label: '目标类型' },
	{ key: 'description', label: '描述' },
	{ key: 'status', label: '审核状态' },
	{ key: 'create_datetime', label: '创建时间' },
];

// 批量操作（批量审核通过 + 批量审核拒绝，无批量删除）
const {
	selectedRows,
	selectedCount,
	hasSelection,
	handleSelectionChange,
	clearSelection,
	handleBatchApprove,
	handleBatchReject,
} = useBatchOperation({
	moduleName: '上传记录',
	batchApproveApi: api.batchApprove,
	batchRejectApi: api.batchReject,
	onSuccess: () => crudExpose.doRefresh(),
});

// 数据导出（无导入功能）
const {
	exportDialogVisible: advancedExportDialogVisible,
	exportForm,
	openExportDialog,
	handleExport: executeExport,
} = useDataExport({
	moduleName: '上传记录',
	exportApi: api.exportDataAdvanced,
	availableFields: exportFields,
});

/** 打开导出对话框 */
const handleAdvancedExport = () => {
	const selectedIds = hasSelection.value
		? selectedRows.value.map((row: any) => row.id)
		: undefined;
	openExportDialog(selectedIds);
};

// 监听分页变化时清空选中状态
watch(
	() => crudBinding.value?.pagination?.currentPage,
	() => {
		clearSelection();
	}
);

// 详情对话框
const detailDialogVisible = ref(false);
const currentRecord = ref<api.UploadRecord | null>(null);

/**
 * 目标类型中文映射
 */
const targetTypeText = (type?: string) => {
	const map: Record<string, string> = {
		knowledge: '知识库',
		persona: '人设卡',
	};
	return type ? map[type] || type : '-';
};

/**
 * 审核状态中文映射
 */
const statusText = (status?: string) => {
	const map: Record<string, string> = {
		pending: '待审核',
		approved: '已通过',
		rejected: '已拒绝',
	};
	return status ? map[status] || status : '-';
};

/**
 * 审核状态标签颜色
 */
const statusTagType = (status?: string) => {
	const map: Record<string, string> = {
		pending: 'warning',
		approved: 'success',
		rejected: 'danger',
	};
	return status ? map[status] || 'info' : 'info';
};

/**
 * 格式化日期时间
 */
const formatDateTime = (dateTime?: string) => {
	if (!dateTime) return '-';
	return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * 查看上传记录详情
 */
const handleViewDetail = (row: any) => {
	currentRecord.value = row;
	detailDialogVisible.value = true;
};

/**
 * 审核通过上传记录
 */
const handleApprove = (row: any) => {
	ElMessageBox.confirm('确定审核通过该上传记录吗？', '提示', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		type: 'warning',
	})
		.then(async () => {
			try {
				await api.ApproveObj(row.id);
				successMessage('审核通过成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('审核通过失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {
			// 用户取消操作
		});
};

/**
 * 审核拒绝上传记录
 */
const handleReject = (row: any) => {
	ElMessageBox.prompt('请输入拒绝原因', '审核拒绝', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		inputPattern: /.+/,
		inputErrorMessage: '拒绝原因为必填项',
	})
		.then(async ({ value }) => {
			try {
				await api.RejectObj(row.id, value);
				successMessage('审核拒绝成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('审核拒绝失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {
			// 用户取消操作
		});
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
