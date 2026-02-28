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
						v-if="auth('comment:Delete')"
						type="danger"
						:disabled="!hasSelection"
						@click="handleBatchDelete"
					>
						批量删除
					</el-button>
					<!-- 导出 -->
					<el-button
						v-if="auth('comment:Export')"
						type="primary"
						@click="handleAdvancedExport"
					>
						导出
					</el-button>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #cell_is_deleted="scope">
					<el-tag :type="scope.row.is_deleted ? 'danger' : 'success'" size="small">
						{{ scope.row.is_deleted ? '已删除' : '正常' }}
					</el-tag>
				</template>

				<template #cell_parent="scope">
					<el-tag :type="scope.row.parent ? 'info' : 'primary'" size="small">
						{{ scope.row.parent ? '二级评论' : '一级评论' }}
					</el-tag>
				</template>

				<template #row-handle="{ row }">
					<el-button
						v-if="auth('comment:List')"
						type="text"
						size="small"
						@click="handleViewDetail(row)"
					>
						详情
					</el-button>
					<el-button
						v-if="auth('comment:List') && !row.parent"
						type="text"
						size="small"
						@click="handleViewReplies(row)"
					>
						回复
					</el-button>
					<el-button
						v-if="auth('comment:Delete') && !row.is_deleted"
						type="text"
						size="small"
						@click="handleDelete(row)"
					>
						删除
					</el-button>
					<el-button
						v-if="auth('comment:Delete') && row.is_deleted"
						type="text"
						size="small"
						@click="handleRestore(row)"
					>
						恢复
					</el-button>
					<el-button
						v-if="auth('comment:Delete') && !row.is_deleted"
						type="text"
						size="small"
						style="color: #f56c6c"
						@click="handleBanUser(row)"
					>
						封禁
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 评论详情对话框 -->
		<el-dialog
			v-model="detailDialogVisible"
			title="评论详情"
			width="600px"
		>
			<el-descriptions :column="1" border>
				<el-descriptions-item label="评论ID">{{ currentComment?.id }}</el-descriptions-item>
				<el-descriptions-item label="用户">{{ currentComment?.user_name || '-' }}</el-descriptions-item>
				<el-descriptions-item label="目标类型">{{ targetTypeText(currentComment?.target_type) }}</el-descriptions-item>
				<el-descriptions-item label="评论层级">{{ currentComment?.parent ? '二级评论' : '一级评论' }}</el-descriptions-item>
				<el-descriptions-item label="评论内容">
					<div style="white-space: pre-wrap; word-break: break-all;">{{ currentComment?.content }}</div>
				</el-descriptions-item>
				<el-descriptions-item label="点赞数">{{ currentComment?.like_count ?? 0 }}</el-descriptions-item>
				<el-descriptions-item label="点踩数">{{ currentComment?.dislike_count ?? 0 }}</el-descriptions-item>
				<el-descriptions-item label="状态">
					<el-tag :type="currentComment?.is_deleted ? 'danger' : 'success'" size="small">
						{{ currentComment?.is_deleted ? '已删除' : '正常' }}
					</el-tag>
				</el-descriptions-item>
				<el-descriptions-item label="创建时间">{{ formatDateTime(currentComment?.create_datetime) }}</el-descriptions-item>
			</el-descriptions>
			<template #footer>
				<el-button @click="detailDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<!-- 回复列表对话框 -->
		<el-dialog
			v-model="repliesDialogVisible"
			title="回复列表"
			width="800px"
		>
			<el-table :data="repliesList" border stripe empty-text="暂无回复">
				<el-table-column type="index" label="序号" width="70" align="center" />
				<el-table-column prop="user_name" label="用户" width="120" />
				<el-table-column prop="content" label="回复内容" min-width="250" show-overflow-tooltip />
				<el-table-column prop="like_count" label="点赞" width="80" align="right" />
				<el-table-column prop="is_deleted" label="状态" width="80" align="center">
					<template #default="{ row }">
						<el-tag :type="row.is_deleted ? 'danger' : 'success'" size="small">
							{{ row.is_deleted ? '已删除' : '正常' }}
						</el-tag>
					</template>
				</el-table-column>
				<el-table-column prop="create_datetime" label="创建时间" width="180">
					<template #default="{ row }">
						{{ formatDateTime(row.create_datetime) }}
					</template>
				</el-table-column>
			</el-table>
			<template #footer>
				<el-button @click="repliesDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<!-- 封禁用户对话框 -->
		<el-dialog
			v-model="banDialogVisible"
			title="封禁用户"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-alert
				v-if="banTargetUser"
				:title="`即将封禁用户：${banTargetUser}`"
				type="warning"
				:closable="false"
				style="margin-bottom: 16px"
			/>
			<el-form :model="banForm" :rules="banRules" ref="banFormRef" label-width="100px">
				<el-form-item label="封禁原因" prop="reason">
					<el-input
						v-model="banForm.reason"
						type="textarea"
						:rows="3"
						placeholder="请输入封禁原因"
					/>
				</el-form-item>
				<el-form-item label="封禁时长" prop="duration_hours">
					<el-select v-model="banForm.duration_hours" placeholder="请选择封禁时长" style="width: 100%">
						<el-option label="永久封禁" :value="0" />
						<el-option label="1 小时" :value="1" />
						<el-option label="6 小时" :value="6" />
						<el-option label="24 小时" :value="24" />
						<el-option label="3 天" :value="72" />
						<el-option label="7 天" :value="168" />
						<el-option label="30 天" :value="720" />
					</el-select>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="banDialogVisible = false">取消</el-button>
				<el-button type="danger" @click="submitBan">确定封禁</el-button>
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

<script lang="ts" setup name="contentComment">
import { ref, onMounted, watch } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from './api';
import { auth } from '/@/utils/authFunction';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox } from 'element-plus';
import type { FormInstance } from 'element-plus';
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

// 评论模块可导出字段列表
const exportFields: ExportField[] = [
	{ key: 'content', label: '评论内容' },
	{ key: 'user_name', label: '用户' },
	{ key: 'target_type', label: '目标类型' },
	{ key: 'parent', label: '评论层级' },
	{ key: 'like_count', label: '点赞数' },
	{ key: 'dislike_count', label: '点踩数' },
	{ key: 'is_deleted', label: '删除状态' },
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
	moduleName: '评论',
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
	moduleName: '评论',
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

// 评论详情对话框
const detailDialogVisible = ref(false);
const currentComment = ref<api.Comment | null>(null);

// 回复列表对话框
const repliesDialogVisible = ref(false);
const repliesList = ref<api.Comment[]>([]);

// 封禁用户对话框
const banDialogVisible = ref(false);
const banFormRef = ref<FormInstance>();
const banTargetUser = ref('');
const banForm = ref({
	id: '',
	reason: '',
	duration_hours: 0,
});
const banRules = {
	reason: [
		{ required: true, message: '封禁原因为必填项', trigger: 'blur' },
	],
};

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
 * 查看评论详情
 */
const handleViewDetail = (row: any) => {
	currentComment.value = row;
	detailDialogVisible.value = true;
};

/**
 * 查看回复列表
 */
const handleViewReplies = async (row: any) => {
	try {
		const response = await api.GetReplies(row.id);
		repliesList.value = response.data || [];
		repliesDialogVisible.value = true;
	} catch (error: any) {
		errorMessage('获取回复列表失败：' + (error.message || '未知错误'));
	}
};

/**
 * 删除评论（软删除）
 */
const handleDelete = (row: any) => {
	const levelText = row.parent ? '' : '（一级评论将连带删除其子评论）';
	ElMessageBox.confirm(`确定删除该评论吗？${levelText}`, '提示', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		type: 'warning',
	})
		.then(async () => {
			try {
				const res = await api.AdminDeleteObj(row.id);
				successMessage(res.msg || '删除成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('删除失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {});
};

/**
 * 恢复已删除的评论
 */
const handleRestore = (row: any) => {
	ElMessageBox.confirm('确定恢复该评论吗？', '提示', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		type: 'info',
	})
		.then(async () => {
			try {
				await api.RestoreObj(row.id);
				successMessage('恢复成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('恢复失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {});
};

/**
 * 封禁用户
 */
const handleBanUser = (row: any) => {
	banForm.value.id = row.id;
	banForm.value.reason = '';
	banForm.value.duration_hours = 0;
	banTargetUser.value = row.user_name || '未知用户';
	banDialogVisible.value = true;
};

/**
 * 提交封禁
 */
const submitBan = async () => {
	if (!banFormRef.value) return;

	await banFormRef.value.validate(async (valid) => {
		if (valid) {
			try {
				const durationHours = banForm.value.duration_hours || undefined;
				const res = await api.BanUser(banForm.value.id, banForm.value.reason, durationHours);
				successMessage(res.msg || '封禁成功');
				banDialogVisible.value = false;
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('封禁失败：' + (error.message || '未知错误'));
			}
		}
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
