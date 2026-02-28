<template>
	<fs-page>
		<!-- 审核统计卡片 -->
		<el-row :gutter="16" style="margin-bottom: 16px">
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">待审核总数</div>
					<div class="stat-value">{{ stats.pending_total }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">待审核知识库</div>
					<div class="stat-value" style="color: #409eff">{{ stats.pending_knowledge }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">待审核人设卡</div>
					<div class="stat-value" style="color: #e6a23c">{{ stats.pending_persona }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">今日已通过</div>
					<div class="stat-value" style="color: #67c23a">{{ stats.approved_today }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">今日已拒绝</div>
					<div class="stat-value" style="color: #f56c6c">{{ stats.rejected_today }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">通过率(30天)</div>
					<div class="stat-value" style="color: #909399">{{ stats.approval_rate }}%</div>
				</el-card>
			</el-col>
		</el-row>

		<!-- 审核列表 -->
		<el-card>
			<fs-crud ref="crudRef" v-bind="crudBinding" @selection-change="handleSelectionChange">
				<!-- 操作栏右侧按钮 -->
				<template #actionbar-right>
					<span v-if="hasSelection" style="margin-right: 12px; color: #409eff; font-size: 14px">
						{{ formatSelectionText(selectedCount) }}
					</span>
					<!-- 批量操作需要选择内容类型 -->
					<el-select
						v-if="hasSelection"
						v-model="batchContentType"
						placeholder="选择内容类型"
						size="default"
						style="width: 130px; margin-right: 8px"
					>
						<el-option label="知识库" value="knowledge" />
						<el-option label="人设卡" value="persona" />
					</el-select>
					<el-button
						v-if="auth('review:Approve')"
						type="success"
						:disabled="!hasSelection || !batchContentType"
						@click="handleBatchApprove"
					>
						批量通过
					</el-button>
					<el-button
						v-if="auth('review:Reject')"
						type="danger"
						:disabled="!hasSelection || !batchContentType"
						@click="handleBatchReject"
					>
						批量拒绝
					</el-button>
					<el-button
						v-if="auth('review:AIReview')"
						type="primary"
						:disabled="!hasSelection || !batchContentType"
						:loading="aiReviewLoading"
						@click="handleBatchAIReview"
					>
						批量 AI 审核
					</el-button>
				</template>

				<!-- 内容类型标签 -->
				<template #cell_content_type="scope">
					<el-tag
						:type="scope.row.content_type === 'knowledge' ? '' : 'warning'"
						size="small"
					>
						{{ scope.row.content_type === 'knowledge' ? '知识库' : '人设卡' }}
					</el-tag>
				</template>

				<!-- AI 审核状态标签 -->
				<template #cell_ai_review_decision="scope">
					<el-tag
						v-if="scope.row.ai_review_decision"
						:type="aiDecisionTagType(scope.row.ai_review_decision)"
						size="small"
					>
						{{ aiDecisionLabel(scope.row.ai_review_decision) }}
					</el-tag>
					<span v-else style="color: #c0c4cc; font-size: 12px">未审核</span>
				</template>

				<!-- 自定义行操作 -->
				<template #row-handle="{ row }">
					<el-button
						v-if="auth('review:Approve')"
						type="text"
						size="small"
						style="color: #67c23a"
						@click="handleApprove(row)"
					>
						通过
					</el-button>
					<el-button
						v-if="auth('review:Reject')"
						type="text"
						size="small"
						style="color: #f56c6c"
						@click="handleReject(row)"
					>
						拒绝
					</el-button>
					<el-button
						v-if="auth('review:Return')"
						type="text"
						size="small"
						style="color: #e6a23c"
						@click="handleReturn(row)"
					>
						退回
					</el-button>
					<el-button
						type="text"
						size="small"
						@click="handleViewDetail(row)"
					>
						详情
					</el-button>
					<!-- AI 审核按钮：仅对待审核状态的内容显示 -->
					<el-button
						v-if="auth('review:AIReview')"
						type="text"
						size="small"
						style="color: #409eff"
						:loading="aiReviewLoading"
						@click="handleAIReview(row)"
					>
						AI 审核
					</el-button>
					<!-- 查看 AI 审核报告 -->
					<el-button
						type="text"
						size="small"
						style="color: #909399"
						@click="handleViewReport(row)"
					>
						查看报告
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 内容详情对话框 -->
		<el-dialog v-model="detailDialogVisible" title="内容详情" width="600px">
			<el-descriptions :column="1" border>
				<el-descriptions-item label="内容ID">{{ currentItem?.id }}</el-descriptions-item>
				<el-descriptions-item label="名称">{{ currentItem?.name }}</el-descriptions-item>
				<el-descriptions-item label="描述">
					<div style="white-space: pre-wrap; word-break: break-all">{{ currentItem?.description || '-' }}</div>
				</el-descriptions-item>
				<el-descriptions-item label="内容类型">
					{{ currentItem?.content_type === 'knowledge' ? '知识库' : '人设卡' }}
				</el-descriptions-item>
				<el-descriptions-item label="上传者">{{ currentItem?.uploader_name || '-' }}</el-descriptions-item>
				<el-descriptions-item label="标签">{{ currentItem?.tags || '-' }}</el-descriptions-item>
				<el-descriptions-item label="文件数">{{ currentItem?.file_count ?? 0 }}</el-descriptions-item>
				<el-descriptions-item label="创建时间">{{ formatDateTime(currentItem?.create_datetime) }}</el-descriptions-item>
			</el-descriptions>
			<template #footer>
				<el-button @click="detailDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>

		<!-- 拒绝原因对话框 -->
		<el-dialog
			v-model="rejectDialogVisible"
			title="审核拒绝"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-alert
				v-if="rejectTarget"
				:title="`即将拒绝：${rejectTarget}`"
				type="warning"
				:closable="false"
				style="margin-bottom: 16px"
			/>
			<el-form :model="rejectForm" :rules="rejectRules" ref="rejectFormRef" label-width="100px">
				<el-form-item label="拒绝原因" prop="reason">
					<el-input
						v-model="rejectForm.reason"
						type="textarea"
						:rows="4"
						placeholder="请输入拒绝原因（最多 500 字符）"
						maxlength="500"
						show-word-limit
					/>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="rejectDialogVisible = false">取消</el-button>
				<el-button type="danger" @click="submitReject">确定拒绝</el-button>
			</template>
		</el-dialog>

		<!-- 退回原因对话框 -->
		<el-dialog
			v-model="returnDialogVisible"
			title="退回内容"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-alert
				v-if="returnTarget"
				:title="`即将退回：${returnTarget}`"
				type="info"
				:closable="false"
				style="margin-bottom: 16px"
			/>
			<el-form :model="returnForm" label-width="100px">
				<el-form-item label="退回原因">
					<el-input
						v-model="returnForm.reason"
						type="textarea"
						:rows="4"
						placeholder="请输入退回原因（可选）"
					/>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="returnDialogVisible = false">取消</el-button>
				<el-button type="warning" @click="submitReturn">确定退回</el-button>
			</template>
		</el-dialog>

		<!-- AI 审核报告对话框 -->
		<el-dialog v-model="reportDialogVisible" title="AI 审核报告" width="700px">
			<template v-if="currentReport">
				<el-descriptions :column="2" border>
					<el-descriptions-item label="内容名称" :span="2">
						{{ currentReport.content_name }}
					</el-descriptions-item>
					<el-descriptions-item label="审核决策">
						<el-tag
							:type="reportDecisionTagType"
							size="small"
						>
							{{ reportDecisionLabel }}
						</el-tag>
					</el-descriptions-item>
					<el-descriptions-item label="置信度">
						<el-progress
							:percentage="Number((currentReport.final_confidence * 100).toFixed(1))"
							:color="confidenceColor(currentReport.final_confidence)"
							:stroke-width="16"
							:text-inside="true"
							style="width: 180px"
						/>
					</el-descriptions-item>
					<el-descriptions-item label="违规类型" :span="2">
						<el-tag
							v-for="vt in currentReport.violation_types"
							:key="vt"
							type="danger"
							size="small"
							style="margin-right: 4px"
						>
							{{ vt }}
						</el-tag>
						<span v-if="!currentReport.violation_types?.length">无</span>
					</el-descriptions-item>
					<el-descriptions-item label="审核时间" :span="2">
						{{ formatDateTime(currentReport.create_datetime) }}
					</el-descriptions-item>
				</el-descriptions>

				<!-- 分段审核详情 -->
				<div v-if="reportParts.length" style="margin-top: 16px">
					<h4 style="margin-bottom: 8px">审核详情</h4>
					<el-table :data="reportParts" border size="small" row-key="part_name" :default-expand-all="false">
						<el-table-column type="expand">
							<template #default="{ row }">
								<div v-if="row.segments && row.segments.length" style="padding: 8px 16px">
									<el-table :data="row.segments" size="small" border>
										<el-table-column label="分段" width="70" align="center">
											<template #default="{ row: seg }">
												#{{ seg.segment_index ?? '-' }}
											</template>
										</el-table-column>
										<el-table-column label="摘要" min-width="200">
											<template #default="{ row: seg }">
												{{ seg.text_summary || '-' }}
											</template>
										</el-table-column>
										<el-table-column label="置信度" width="160" align="center">
											<template #default="{ row: seg }">
												<el-progress
													:percentage="Number((seg.confidence * 100).toFixed(1))"
													:color="confidenceColor(seg.confidence)"
													:stroke-width="12"
													:text-inside="true"
													style="width: 120px"
												/>
											</template>
										</el-table-column>
										<el-table-column label="违规类型" min-width="120">
											<template #default="{ row: seg }">
												<el-tag
													v-for="vt in seg.violation_types"
													:key="vt"
													type="danger"
													size="small"
													style="margin-right: 4px"
												>
													{{ vt }}
												</el-tag>
												<span v-if="!seg.violation_types?.length">无</span>
											</template>
										</el-table-column>
									</el-table>
								</div>
								<div v-else style="padding: 8px 16px; color: #909399">无分段详情</div>
							</template>
						</el-table-column>
						<el-table-column prop="part_name" label="审核部分" min-width="120" />
						<el-table-column prop="part_type" label="类型" width="80" align="center">
							<template #default="{ row }">
								{{ row.part_type === 'text_field' ? '文本' : '文件' }}
							</template>
						</el-table-column>
						<el-table-column prop="confidence" label="置信度" width="160" align="center">
							<template #default="{ row }">
								<el-progress
									:percentage="Number((row.confidence * 100).toFixed(1))"
									:color="confidenceColor(row.confidence)"
									:stroke-width="12"
									:text-inside="true"
									style="width: 120px"
								/>
							</template>
						</el-table-column>
						<el-table-column prop="violation_types" label="违规类型" min-width="120">
							<template #default="{ row }">
								<el-tag
									v-for="vt in row.violation_types"
									:key="vt"
									type="danger"
									size="small"
									style="margin-right: 4px"
								>
									{{ vt }}
								</el-tag>
								<span v-if="!row.violation_types?.length">无</span>
							</template>
						</el-table-column>
					</el-table>
				</div>
			</template>
			<el-empty v-else description="暂无报告数据" />
			<template #footer>
				<el-button @click="reportDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts" setup name="contentReview">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from './api';
import { triggerAIReview, getAIReport } from './api';
import type { AIReviewReport } from './api';
import { auth } from '/@/utils/authFunction';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox, ElMessage } from 'element-plus';
import type { FormInstance } from 'element-plus';
import dayjs from 'dayjs';
import { formatSelectionText } from '/@/composables/content/useBatchOperation';

// ==================== CRUD 初始化 ====================
const crudRef = ref();
const crudBinding = ref();
const { crudExpose } = useExpose({ crudRef, crudBinding });
const { crudOptions } = createCrudOptions({ crudExpose });
const { resetCrudOptions } = useCrud({ crudExpose, crudOptions });

// ==================== 统计数据 ====================
const stats = reactive<api.ReviewStats>({
	pending_total: 0,
	pending_knowledge: 0,
	pending_persona: 0,
	approved_today: 0,
	rejected_today: 0,
	approval_rate: 0,
});

/** 加载统计数据 */
const loadStats = async () => {
	try {
		const res: any = await api.GetStats();
		const data = res.data || res;
		Object.assign(stats, data);
	} catch {
		// 统计加载失败不影响主功能
	}
};

// ==================== 选择状态 ====================
const selectedRows = ref<any[]>([]);
const selectedCount = computed(() => selectedRows.value.length);
const hasSelection = computed(() => selectedRows.value.length > 0);
const batchContentType = ref('');

const handleSelectionChange = (rows: any[]) => {
	selectedRows.value = rows;
	// 如果选中项都是同一类型，自动设置 batchContentType
	if (rows.length > 0) {
		const types = new Set(rows.map((r) => r.content_type));
		if (types.size === 1) {
			batchContentType.value = rows[0].content_type;
		}
	}
};

// 翻页时清空选中
watch(
	() => crudBinding.value?.pagination?.currentPage,
	() => {
		selectedRows.value = [];
		batchContentType.value = '';
	}
);

// ==================== 详情对话框 ====================
const detailDialogVisible = ref(false);
const currentItem = ref<api.ReviewItem | null>(null);

const formatDateTime = (dateTime?: string) => {
	if (!dateTime) return '-';
	return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss');
};

const handleViewDetail = (row: any) => {
	currentItem.value = row;
	detailDialogVisible.value = true;
};

// ==================== 单条审核通过 ====================
const handleApprove = (row: any) => {
	ElMessageBox.confirm(`确定审核通过「${row.name}」吗？`, '审核通过', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		type: 'success',
	})
		.then(async () => {
			try {
				await api.approveItem(row.id, row.content_type);
				successMessage('内容已批准');
				crudExpose.doRefresh();
				loadStats();
			} catch (error: any) {
				errorMessage('操作失败：' + (error.msg || error.message || '未知错误'));
			}
		})
		.catch(() => {});
};

// ==================== 单条审核拒绝 ====================
const rejectDialogVisible = ref(false);
const rejectFormRef = ref<FormInstance>();
const rejectTarget = ref('');
const rejectForm = ref({ id: '', content_type: '', reason: '' });
const rejectRules = {
	reason: [{ required: true, message: '拒绝原因为必填项', trigger: 'blur' }],
};

const handleReject = (row: any) => {
	rejectForm.value = { id: row.id, content_type: row.content_type, reason: '' };
	rejectTarget.value = row.name;
	rejectDialogVisible.value = true;
};

const submitReject = async () => {
	if (!rejectFormRef.value) return;
	await rejectFormRef.value.validate(async (valid) => {
		if (valid) {
			try {
				await api.rejectItem(
					rejectForm.value.id,
					rejectForm.value.content_type,
					rejectForm.value.reason
				);
				successMessage('内容已拒绝');
				rejectDialogVisible.value = false;
				crudExpose.doRefresh();
				loadStats();
			} catch (error: any) {
				errorMessage('操作失败：' + (error.msg || error.message || '未知错误'));
			}
		}
	});
};

// ==================== 退回操作 ====================
const returnDialogVisible = ref(false);
const returnTarget = ref('');
const returnForm = ref({ id: '', content_type: '', reason: '' });

const handleReturn = (row: any) => {
	returnForm.value = { id: row.id, content_type: row.content_type, reason: '' };
	returnTarget.value = row.name;
	returnDialogVisible.value = true;
};

const submitReturn = async () => {
	try {
		await api.returnDraft(
			returnForm.value.id,
			returnForm.value.content_type,
			returnForm.value.reason
		);
		successMessage('内容已退回');
		returnDialogVisible.value = false;
		crudExpose.doRefresh();
		loadStats();
	} catch (error: any) {
		errorMessage('操作失败：' + (error.msg || error.message || '未知错误'));
	}
};

// ==================== AI 审核 ====================
const aiReviewLoading = ref(false);
const reportDialogVisible = ref(false);
const currentReport = ref<AIReviewReport | null>(null);

/** AI 审核决策 → 标签类型（用于列表列） */
const aiDecisionTagType = (decision: string): string => {
	const map: Record<string, string> = { auto_approved: 'success', auto_rejected: 'danger', pending_manual: 'warning' };
	return map[decision] || 'info';
};

/** AI 审核决策 → 中文标签（用于列表列） */
const aiDecisionLabel = (decision: string): string => {
	const map: Record<string, string> = { auto_approved: '自动通过', auto_rejected: '自动拒绝', pending_manual: '待人工复核' };
	return map[decision] || decision;
};

/** 审核决策对应的标签类型 */
const reportDecisionTagType = computed(() => {
	if (!currentReport.value) return 'info';
	const map: Record<string, string> = {
		auto_approved: 'success',
		auto_rejected: 'danger',
		pending_manual: 'warning',
	};
	return map[currentReport.value.decision] || 'info';
});

/** 审核决策对应的中文标签 */
const reportDecisionLabel = computed(() => {
	if (!currentReport.value) return '';
	const map: Record<string, string> = {
		auto_approved: '自动通过',
		auto_rejected: '自动拒绝',
		pending_manual: '待人工复核',
	};
	return map[currentReport.value.decision] || currentReport.value.decision;
});

/** 报告中的审核分段详情 */
const reportParts = computed(() => {
	return currentReport.value?.report_data?.parts || [];
});

/** 置信度颜色（用于进度条） */
const confidenceColor = (confidence: number): string => {
	if (confidence >= 0.8) return '#67c23a';
	if (confidence >= 0.5) return '#e6a23c';
	return '#f56c6c';
};

/** 触发单条 AI 审核 */
const handleAIReview = async (row: any) => {
	try {
		await ElMessageBox.confirm(
			`确定对「${row.name}」执行 AI 审核吗？`,
			'AI 审核',
			{ confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
		);
		aiReviewLoading.value = true;
		await triggerAIReview(row.id, row.content_type);
		successMessage('AI 审核任务已创建');
		crudExpose.doRefresh();
		loadStats();
	} catch (error: any) {
		if (error !== 'cancel') {
			errorMessage('AI 审核失败：' + (error.msg || error.message || '未知错误'));
		}
	} finally {
		aiReviewLoading.value = false;
	}
};

/** 查看 AI 审核报告 */
const handleViewReport = async (row: any) => {
	try {
		const res: any = await getAIReport(row.id, row.content_type);
		const data = res.data || res;
		currentReport.value = data;
		reportDialogVisible.value = true;
	} catch (error: any) {
		errorMessage('获取报告失败：' + (error.msg || error.message || '未知错误'));
	}
};

// ==================== 批量 AI 审核 ====================
const handleBatchAIReview = async () => {
	const ids = selectedRows.value.map((r) => r.id);
	if (!ids.length || !batchContentType.value) return;

	try {
		await ElMessageBox.confirm(
			`确定对选中的 ${ids.length} 条记录执行 AI 审核吗？`,
			'批量 AI 审核',
			{ confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
		);
	} catch {
		return;
	}

	try {
		aiReviewLoading.value = true;
		await api.batchAIReview(ids, batchContentType.value);
		successMessage(`已创建 ${ids.length} 条 AI 审核任务`);
		selectedRows.value = [];
		batchContentType.value = '';
		crudExpose.doRefresh();
		loadStats();
	} catch (error: any) {
		errorMessage('批量 AI 审核失败：' + (error.msg || error.message || '未知错误'));
	} finally {
		aiReviewLoading.value = false;
	}
};

// ==================== 批量审核通过 ====================
const handleBatchApprove = async () => {
	const ids = selectedRows.value.map((r) => r.id);
	if (!ids.length || !batchContentType.value) return;

	try {
		await ElMessageBox.confirm(
			`确定批量审核通过选中的 ${ids.length} 条记录吗？`,
			'批量审核通过',
			{ confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
		);
	} catch {
		return;
	}

	try {
		const res: any = await api.batchApprove(ids, batchContentType.value);
		const result = res.data || res;
		showBatchResult(result, '批量审核通过');
		selectedRows.value = [];
		batchContentType.value = '';
		crudExpose.doRefresh();
		loadStats();
	} catch (error: any) {
		errorMessage('批量操作失败：' + (error.msg || error.message || '未知错误'));
	}
};

// ==================== 批量审核拒绝 ====================
const handleBatchReject = async () => {
	const ids = selectedRows.value.map((r) => r.id);
	if (!ids.length || !batchContentType.value) return;

	let reason = '';
	try {
		const { value } = await ElMessageBox.prompt(
			`请输入拒绝原因（将应用于选中的 ${ids.length} 条记录）`,
			'批量审核拒绝',
			{
				confirmButtonText: '确定',
				cancelButtonText: '取消',
				inputType: 'textarea',
				inputPlaceholder: '请输入拒绝原因（最多 500 字符）',
				inputValidator: (val: string) => {
					if (!val || !val.trim()) return '拒绝原因为必填项';
					if (val.length > 500) return '拒绝原因不能超过 500 个字符';
					return true;
				},
			}
		);
		reason = value;
	} catch {
		return;
	}

	try {
		const res: any = await api.batchReject(ids, batchContentType.value, reason);
		const result = res.data || res;
		showBatchResult(result, '批量审核拒绝');
		selectedRows.value = [];
		batchContentType.value = '';
		crudExpose.doRefresh();
		loadStats();
	} catch (error: any) {
		errorMessage('批量操作失败：' + (error.msg || error.message || '未知错误'));
	}
};

// ==================== 批量结果展示 ====================
const showBatchResult = (result: api.BatchOperationResponse, operationName: string) => {
	if (result.fail_count === 0) {
		ElMessage.success(`${operationName}完成：${result.success_count} 条记录操作成功`);
	} else if (result.success_count === 0) {
		ElMessage.error(`${operationName}失败：${result.fail_count} 条记录操作失败`);
	} else {
		ElMessage.warning(
			`${operationName}完成：${result.success_count} 条成功，${result.fail_count} 条失败`
		);
	}
	// 显示失败详情
	if (result.failures && result.failures.length > 0) {
		const failDetails = result.failures
			.map((f) => `ID: ${f.id}，原因: ${f.reason}`)
			.join('\n');
		ElMessageBox.alert(`失败记录详情：\n${failDetails}`, '操作结果详情', {
			type: 'warning',
			confirmButtonText: '确定',
		});
	}
};

// ==================== 生命周期 ====================
onMounted(() => {
	crudExpose.doRefresh();
	loadStats();
});
</script>

<style lang="scss" scoped>
.stat-card {
	text-align: center;
	.stat-label {
		font-size: 13px;
		color: #909399;
		margin-bottom: 8px;
	}
	.stat-value {
		font-size: 24px;
		font-weight: 600;
		color: #303133;
	}
}
.el-card {
	height: 100%;
}
</style>
