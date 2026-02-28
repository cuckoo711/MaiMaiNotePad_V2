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
						v-if="auth('knowledge_base:Approve')"
						type="success"
						:disabled="!hasSelection"
						@click="handleBatchApprove"
					>
						批量审核通过
					</el-button>
					<!-- 批量审核拒绝 -->
					<el-button
						v-if="auth('knowledge_base:Approve')"
						type="warning"
						:disabled="!hasSelection"
						@click="handleBatchReject"
					>
						批量审核拒绝
					</el-button>
					<!-- 批量删除 -->
					<el-button
						v-if="auth('knowledge_base:Delete')"
						type="danger"
						:disabled="!hasSelection"
						@click="handleBatchDelete"
					>
						批量删除
					</el-button>
					<!-- 导出 -->
					<el-button
						v-if="auth('knowledge_base:Export')"
						type="primary"
						@click="handleAdvancedExport"
					>
						导出
					</el-button>
					<!-- 导入 -->
					<el-button
						v-if="auth('knowledge_base:Create')"
						type="primary"
						@click="openImportDialog"
					>
						导入
					</el-button>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #row-handle="{ row }">
					<el-button
						v-if="auth('knowledge_base:Update')"
						type="text"
						size="small"
						@click="handleEdit(row)"
					>
						编辑
					</el-button>
					<el-button
						v-if="auth('knowledge_base:Delete')"
						type="text"
						size="small"
						@click="handleDelete(row)"
					>
						删除
					</el-button>
					<el-button
						v-if="auth('knowledge_base:Approve') && row.is_pending"
						type="text"
						size="small"
						@click="handleApprove(row)"
					>
						审核通过
					</el-button>
					<el-button
						v-if="auth('knowledge_base:Approve') && row.is_pending"
						type="text"
						size="small"
						@click="handleReject(row)"
					>
						审核拒绝
					</el-button>
					<el-button
						v-if="auth('knowledge_base:List')"
						type="text"
						size="small"
						@click="handleViewFiles(row)"
					>
						查看文件
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 审核拒绝对话框 -->
		<el-dialog
			v-model="rejectDialogVisible"
			title="审核拒绝"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-form :model="rejectForm" :rules="rejectRules" ref="rejectFormRef" label-width="100px">
				<el-form-item label="拒绝原因" prop="reason">
					<el-input
						v-model="rejectForm.reason"
						type="textarea"
						:rows="4"
						placeholder="请输入拒绝原因"
					/>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="rejectDialogVisible = false">取消</el-button>
				<el-button type="primary" @click="submitReject">确定</el-button>
			</template>
		</el-dialog>

		<!-- 查看关联文件对话框 -->
		<el-dialog
			v-model="filesDialogVisible"
			title="关联文件列表"
			width="800px"
		>
			<el-table :data="filesList" border stripe>
				<el-table-column type="index" label="序号" width="70" align="center" />
				<el-table-column prop="file_name" label="文件名" min-width="200" />
				<el-table-column prop="file_path" label="文件路径" min-width="200" show-overflow-tooltip />
				<el-table-column prop="file_size" label="文件大小" width="120" align="right">
					<template #default="{ row }">
						{{ formatFileSize(row.file_size) }}
					</template>
				</el-table-column>
				<el-table-column prop="create_datetime" label="创建时间" width="180">
					<template #default="{ row }">
						{{ formatDateTime(row.create_datetime) }}
					</template>
				</el-table-column>
			</el-table>
			<template #footer>
				<el-button @click="filesDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<!-- 高级导出对话框 -->
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

		<!-- 导入对话框 -->
		<el-dialog
			v-model="importDialogVisible"
			title="导入数据"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-form label-width="100px">
				<el-form-item label="导入模板">
					<el-button type="text" @click="handleDownloadTemplate">下载导入模板</el-button>
				</el-form-item>
				<el-form-item label="选择文件">
					<el-upload
						:auto-upload="false"
						:show-file-list="true"
						:limit="1"
						accept=".xlsx,.csv"
						:before-upload="handleFileChange"
						:on-change="(file: any) => handleFileChange(file.raw)"
					>
						<el-button type="primary">选择文件</el-button>
						<template #tip>
							<div class="el-upload__tip">仅支持 .xlsx 和 .csv 格式文件</div>
						</template>
					</el-upload>
				</el-form-item>
			</el-form>
			<!-- 导入结果摘要 -->
			<div v-if="importResult" style="margin-top: 16px;">
				<el-alert
					:title="`导入完成：${importResult.success_count} 条成功，${importResult.fail_count} 条失败`"
					:type="importResult.fail_count === 0 ? 'success' : 'warning'"
					:closable="false"
				/>
				<el-table
					v-if="importResult.errors && importResult.errors.length > 0"
					:data="importResult.errors"
					border
					stripe
					style="margin-top: 12px;"
					max-height="200"
				>
					<el-table-column prop="row" label="行号" width="80" align="center" />
					<el-table-column prop="message" label="错误信息" />
				</el-table>
			</div>
			<template #footer>
				<el-button @click="importDialogVisible = false">关闭</el-button>
				<el-button
					type="primary"
					:loading="importLoading"
					:disabled="!importFile"
					@click="handleImport"
				>
					开始导入
				</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts" setup name="contentKnowledgeBase">
import { ref, onMounted } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from './api';
import { auth } from '/@/utils/authFunction';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox, ElMessage } from 'element-plus';
import type { FormInstance } from 'element-plus';
import dayjs from 'dayjs';
import { useBatchOperation, formatSelectionText } from '/@/composables/content/useBatchOperation';
import { useDataExport, type ExportField } from '/@/composables/content/useDataExport';
import { useDataImport } from '/@/composables/content/useDataImport';

// crud组件的ref
const crudRef = ref();
// crud 配置的ref
const crudBinding = ref();
// 暴露的方法
const { crudExpose } = useExpose({ crudRef, crudBinding });
// 你的crud配置
const { crudOptions } = createCrudOptions({ crudExpose });
// 初始化crud配置
const { resetCrudOptions } = useCrud({ crudExpose, crudOptions });

// 可导出字段列表
const exportFields: ExportField[] = [
	{ key: 'name', label: '名称' },
	{ key: 'description', label: '描述' },
	{ key: 'uploader_name', label: '上传者' },
	{ key: 'copyright_owner', label: '版权所有者' },
	{ key: 'tags', label: '标签' },
	{ key: 'star_count', label: '收藏数' },
	{ key: 'downloads', label: '下载次数' },
	{ key: 'is_public', label: '公开状态' },
	{ key: 'is_pending', label: '审核状态' },
	{ key: 'version', label: '版本号' },
	{ key: 'create_datetime', label: '创建时间' },
];

// 批量操作
const {
	selectedRows,
	selectedCount,
	hasSelection,
	handleSelectionChange,
	clearSelection,
	handleBatchApprove,
	handleBatchReject,
	handleBatchDelete,
} = useBatchOperation({
	moduleName: '知识库',
	batchApproveApi: api.batchApprove,
	batchRejectApi: api.batchReject,
	batchDeleteApi: api.batchDelete,
	onSuccess: () => crudExpose.doRefresh(),
});

// 数据导出
const {
	exportDialogVisible: advancedExportDialogVisible,
	exportForm,
	openExportDialog,
	handleExport: executeExport,
} = useDataExport({
	moduleName: '知识库',
	exportApi: api.exportDataAdvanced,
	availableFields: exportFields,
});

// 数据导入
const {
	importDialogVisible,
	importFile,
	importLoading,
	importResult,
	openImportDialog,
	handleImport,
	handleDownloadTemplate,
	handleFileChange,
} = useDataImport({
	moduleName: '知识库',
	importApi: api.importData,
	templateApi: api.downloadImportTemplate,
});

/** 打开高级导出对话框 */
const handleAdvancedExport = () => {
	const selectedIds = hasSelection.value
		? selectedRows.value.map((row: any) => row.id)
		: undefined;
	openExportDialog(selectedIds);
};

// 审核拒绝对话框
const rejectDialogVisible = ref(false);
const rejectFormRef = ref<FormInstance>();
const rejectForm = ref({
	id: '',
	reason: '',
});
const rejectRules = {
	reason: [
		{ required: true, message: '拒绝原因为必填项', trigger: 'blur' },
	],
};

// 查看关联文件对话框
const filesDialogVisible = ref(false);
const filesList = ref<api.KnowledgeBaseFile[]>([]);

/**
 * 格式化日期时间
 */
const formatDateTime = (dateTime: string) => {
	if (!dateTime) return '-';
	return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * 格式化文件大小
 */
const formatFileSize = (size: number) => {
	if (!size) return '0 B';
	const units = ['B', 'KB', 'MB', 'GB', 'TB'];
	let unitIndex = 0;
	let fileSize = size;
	while (fileSize >= 1024 && unitIndex < units.length - 1) {
		fileSize /= 1024;
		unitIndex++;
	}
	return `${fileSize.toFixed(2)} ${units[unitIndex]}`;
};

/**
 * 处理编辑
 */
const handleEdit = (row: any) => {
	crudExpose.openEdit({ row });
};

/**
 * 处理删除
 */
const handleDelete = (row: any) => {
	ElMessageBox.confirm('确定删除该知识库吗？', '提示', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		type: 'warning',
	})
		.then(async () => {
			try {
				await api.DelObj(row.id);
				successMessage('删除成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('删除失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {
			// 用户取消删除
		});
};

/**
 * 处理审核通过
 */
const handleApprove = (row: any) => {
	ElMessageBox.confirm('确定审核通过该知识库吗？', '提示', {
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
			// 用户取消审核
		});
};

/**
 * 处理审核拒绝
 */
const handleReject = (row: any) => {
	rejectForm.value.id = row.id;
	rejectForm.value.reason = '';
	rejectDialogVisible.value = true;
};

/**
 * 提交审核拒绝
 */
const submitReject = async () => {
	if (!rejectFormRef.value) return;
	
	await rejectFormRef.value.validate(async (valid) => {
		if (valid) {
			try {
				await api.RejectObj(rejectForm.value.id, rejectForm.value.reason);
				successMessage('审核拒绝成功');
				rejectDialogVisible.value = false;
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('审核拒绝失败：' + (error.message || '未知错误'));
			}
		}
	});
};

/**
 * 处理查看关联文件
 */
const handleViewFiles = async (row: any) => {
	try {
		const response = await api.GetFiles(row.id);
		filesList.value = response.data || [];
		filesDialogVisible.value = true;
	} catch (error: any) {
		errorMessage('获取文件列表失败：' + (error.message || '未知错误'));
	}
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
