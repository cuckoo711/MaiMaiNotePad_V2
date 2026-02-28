<!-- 收藏记录管理页面 -->
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
					<!-- 批量删除 -->
					<el-button
						v-if="auth('star_record:Delete')"
						type="danger"
						:disabled="!hasSelection"
						@click="handleBatchDelete"
					>
						批量删除
					</el-button>
					<!-- 导出 -->
					<el-button
						v-if="auth('star_record:Export')"
						type="primary"
						@click="handleAdvancedExport"
					>
						导出
					</el-button>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #row-handle="{ row }">
					<el-button
						v-if="auth('star_record:View')"
						type="text"
						size="small"
						@click="handleViewDetail(row)"
					>
						详情
					</el-button>
					<el-button
						v-if="auth('star_record:Delete')"
						type="text"
						size="small"
						@click="handleDelete(row)"
					>
						删除
					</el-button>
				</template>

				<!-- 工具栏追加统计按钮 -->
				<template #actionbar-append>
					<el-button
						v-if="auth('star_record:List')"
						type="primary"
						icon="DataAnalysis"
						@click="handleStats"
					>
						统计
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 收藏详情对话框 -->
		<el-dialog
			v-model="detailDialogVisible"
			title="收藏记录详情"
			width="600px"
		>
			<el-descriptions :column="1" border>
				<el-descriptions-item label="记录ID">{{ currentRecord?.id }}</el-descriptions-item>
				<el-descriptions-item label="用户">{{ currentRecord?.user_name || '-' }}</el-descriptions-item>
				<el-descriptions-item label="目标类型">{{ targetTypeText(currentRecord?.target_type) }}</el-descriptions-item>
				<el-descriptions-item label="目标ID">{{ currentRecord?.target_id }}</el-descriptions-item>
				<el-descriptions-item label="创建时间">{{ formatDateTime(currentRecord?.create_datetime) }}</el-descriptions-item>
			</el-descriptions>
			<template #footer>
				<el-button @click="detailDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<!-- 统计对话框 -->
		<el-dialog
			v-model="statsDialogVisible"
			title="收藏统计"
			width="500px"
		>
			<el-table :data="statsList" border stripe empty-text="暂无统计数据">
				<el-table-column prop="target_type" label="目标类型" align="center">
					<template #default="{ row }">
						{{ targetTypeText(row.target_type) }}
					</template>
				</el-table-column>
				<el-table-column prop="count" label="收藏数" align="right" />
			</el-table>
			<template #footer>
				<el-button @click="statsDialogVisible = false">关闭</el-button>
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

<script lang="ts" setup name="contentStarRecord">
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

// 收藏记录模块可导出字段列表
const exportFields: ExportField[] = [
	{ key: 'user_name', label: '用户' },
	{ key: 'target_type', label: '目标类型' },
	{ key: 'target_id', label: '目标ID' },
	{ key: 'create_datetime', label: '创建时间' },
];

// 批量操作（仅批量删除，无批量审核）
const {
	selectedRows,
	selectedCount,
	hasSelection,
	handleSelectionChange,
	clearSelection,
	handleBatchDelete,
} = useBatchOperation({
	moduleName: '收藏记录',
	batchDeleteApi: api.batchDelete,
	onSuccess: () => crudExpose.doRefresh(),
});

// 数据导出（无导入功能）
const {
	exportDialogVisible: advancedExportDialogVisible,
	exportForm,
	openExportDialog,
	handleExport: executeExport,
} = useDataExport({
	moduleName: '收藏记录',
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
const currentRecord = ref<api.StarRecord | null>(null);

// 统计对话框
const statsDialogVisible = ref(false);
const statsList = ref<Array<{ target_type: string; count: number }>>([]);

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
 * 格式化日期时间
 */
const formatDateTime = (dateTime?: string) => {
	if (!dateTime) return '-';
	return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * 查看收藏记录详情
 */
const handleViewDetail = (row: any) => {
	currentRecord.value = row;
	detailDialogVisible.value = true;
};

/**
 * 删除收藏记录
 */
const handleDelete = (row: any) => {
	ElMessageBox.confirm('确定删除该收藏记录吗？', '提示', {
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
		.catch(() => {});
};

/**
 * 获取收藏统计数据
 */
const handleStats = async () => {
	try {
		const response = await api.GetStats();
		statsList.value = response.data || [];
		statsDialogVisible.value = true;
	} catch (error: any) {
		errorMessage('获取统计数据失败：' + (error.message || '未知错误'));
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
