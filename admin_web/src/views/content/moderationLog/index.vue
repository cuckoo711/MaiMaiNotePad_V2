<template>
	<fs-page>
		<!-- 统计卡片 -->
		<el-row :gutter="16" style="margin-bottom: 16px; flex-shrink: 0">
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">总调用次数</div>
					<div class="stat-value">{{ stats.total_count }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">今日调用</div>
					<div class="stat-value" style="color: #409eff">{{ stats.today_count }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">成功率</div>
					<div class="stat-value" style="color: #67c23a">{{ stats.success_rate }}%</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">总 Token 消耗</div>
					<div class="stat-value" style="color: #e6a23c">{{ formatNumber(stats.total_tokens) }}</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">平均耗时</div>
					<div class="stat-value" style="color: #909399">{{ stats.avg_latency_ms }}ms</div>
				</el-card>
			</el-col>
			<el-col :span="4">
				<el-card shadow="hover" class="stat-card">
					<div class="stat-label">成功次数</div>
					<div class="stat-value" style="color: #67c23a">{{ stats.success_count }}</div>
				</el-card>
			</el-col>
		</el-row>

		<!-- 日志列表 -->
		<el-card class="crud-card">
			<fs-crud ref="crudRef" v-bind="crudBinding">
				<!-- 审核决策标签 -->
				<template #cell_decision="scope">
					<el-tag
						v-if="scope.row.decision === 'true'"
						type="success"
						size="small"
					>
						通过
					</el-tag>
					<el-tag
						v-else-if="scope.row.decision === 'false'"
						type="danger"
						size="small"
					>
						拒绝
					</el-tag>
					<el-tag
						v-else-if="scope.row.decision === 'unknown'"
						type="warning"
						size="small"
					>
						不确定
					</el-tag>
					<el-tag
						v-else-if="scope.row.decision === 'error'"
						type="info"
						size="small"
					>
						异常
					</el-tag>
					<span v-else style="color: #c0c4cc; font-size: 12px">-</span>
				</template>

				<!-- 调用状态标签 -->
				<template #cell_is_success="scope">
					<el-tag
						:type="scope.row.is_success ? 'success' : 'danger'"
						size="small"
					>
						{{ scope.row.is_success ? '成功' : '失败' }}
					</el-tag>
				</template>

				<!-- 审核来源标签 -->
				<template #cell_source="scope">
					<el-tag
						:type="sourceTagType(scope.row.source)"
						size="small"
					>
						{{ sourceLabel(scope.row.source) }}
					</el-tag>
				</template>

				<!-- 行操作 -->
				<template #row-handle="{ row }">
					<el-button
						type="text"
						size="small"
						@click="handleViewDetail(row)"
					>
						详情
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 详情对话框 -->
		<el-dialog
			v-model="detailDialogVisible"
			title="审核日志详情"
			width="700px"
		>
			<el-descriptions :column="2" border v-if="currentLog">
				<el-descriptions-item label="审核来源">
					<el-tag :type="sourceTagType(currentLog.source)" size="small">
						{{ sourceLabel(currentLog.source) }}
					</el-tag>
				</el-descriptions-item>
				<el-descriptions-item label="审核决策">
					<el-tag
						:type="decisionTagType(currentLog.decision)"
						size="small"
					>
						{{ currentLog.decision_label }}
					</el-tag>
				</el-descriptions-item>
				<el-descriptions-item label="触发用户">{{ currentLog.user_name || '-' }}</el-descriptions-item>
				<el-descriptions-item label="关联内容ID">{{ currentLog.content_id || '-' }}</el-descriptions-item>
				<el-descriptions-item label="模型名称">{{ currentLog.model_name }}</el-descriptions-item>
				<el-descriptions-item label="API 提供商">{{ currentLog.api_provider }}</el-descriptions-item>
				<el-descriptions-item label="文本类型">{{ currentLog.text_type }}</el-descriptions-item>
				<el-descriptions-item label="输入文本长度">{{ currentLog.input_text_length }} 字符</el-descriptions-item>
				<el-descriptions-item label="提示词 Token">{{ currentLog.prompt_tokens }}</el-descriptions-item>
				<el-descriptions-item label="生成 Token">{{ currentLog.completion_tokens }}</el-descriptions-item>
				<el-descriptions-item label="总 Token">{{ currentLog.total_tokens }}</el-descriptions-item>
				<el-descriptions-item label="响应耗时">{{ currentLog.latency_ms }}ms</el-descriptions-item>
				<el-descriptions-item label="置信度">{{ currentLog.confidence }}</el-descriptions-item>
				<el-descriptions-item label="调用状态">
					<el-tag :type="currentLog.is_success ? 'success' : 'danger'" size="small">
						{{ currentLog.is_success ? '成功' : '失败' }}
					</el-tag>
				</el-descriptions-item>
				<el-descriptions-item label="温度参数">{{ currentLog.temperature }}</el-descriptions-item>
				<el-descriptions-item label="创建时间">{{ currentLog.create_datetime }}</el-descriptions-item>
				<el-descriptions-item label="违规类型" :span="2">
					<template v-if="currentLog.violation_types && currentLog.violation_types.length">
						<el-tag
							v-for="vt in currentLog.violation_types"
							:key="vt"
							type="danger"
							size="small"
							style="margin-right: 4px"
						>
							{{ vt }}
						</el-tag>
					</template>
					<span v-else style="color: #c0c4cc">无</span>
				</el-descriptions-item>
				<el-descriptions-item label="审核输入文本" :span="2">
					<div style="white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto;">
						{{ currentLog.input_text }}
					</div>
				</el-descriptions-item>
				<el-descriptions-item v-if="currentLog.raw_output" label="模型原始输出" :span="2">
					<div style="white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px;">
						{{ currentLog.raw_output }}
					</div>
				</el-descriptions-item>
				<el-descriptions-item v-if="currentLog.error_message" label="错误信息" :span="2">
					<div style="color: #f56c6c; white-space: pre-wrap;">{{ currentLog.error_message }}</div>
				</el-descriptions-item>
			</el-descriptions>
			<template #footer>
				<el-button @click="detailDialogVisible = false">关闭</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts" setup name="contentModerationLog">
import { ref, onMounted } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import * as api from './api';

// crud 初始化
const crudRef = ref();
const crudBinding = ref();
const { crudExpose } = useExpose({ crudRef, crudBinding });
const { crudOptions } = createCrudOptions({ crudExpose });
const { resetCrudOptions } = useCrud({ crudExpose, crudOptions });

// 统计数据
const stats = ref({
	total_count: 0,
	success_count: 0,
	success_rate: 0,
	today_count: 0,
	total_tokens: 0,
	avg_latency_ms: 0,
});

// 详情对话框
const detailDialogVisible = ref(false);
const currentLog = ref<any>(null);

/** 来源标签类型映射 */
const sourceTagType = (source: string) => {
	const map: Record<string, string> = {
		comment: '',
		knowledge: 'success',
		persona: 'warning',
		knowledge_file: 'info',
	};
	return map[source] || 'info';
};

/** 来源中文映射 */
const sourceLabel = (source: string) => {
	const map: Record<string, string> = {
		comment: '评论审核',
		knowledge: '知识库审核',
		persona: '人设卡审核',
		knowledge_file: '文件审核',
	};
	return map[source] || source;
};

/** 决策标签类型映射 */
const decisionTagType = (decision: string) => {
	const map: Record<string, string> = {
		'true': 'success',
		'false': 'danger',
		unknown: 'warning',
		error: 'info',
	};
	return map[decision] || 'info';
};

/** 格式化大数字 */
const formatNumber = (num: number) => {
	if (!num) return '0';
	if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
	if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
	return num.toString();
};

/** 查看详情 */
const handleViewDetail = (row: any) => {
	currentLog.value = row;
	detailDialogVisible.value = true;
};

/** 加载统计数据 */
const loadStats = async () => {
	try {
		const res = await api.GetStats();
		const data = res.data || res;
		if (data) {
			stats.value = { ...stats.value, ...data };
		}
	} catch (error) {
		console.error('获取审核统计失败:', error);
	}
};

onMounted(() => {
	crudExpose.doRefresh();
	loadStats();
});
</script>

<style lang="scss" scoped>
.stat-card {
	text-align: center;
	padding: 8px 0;
}
.stat-label {
	font-size: 13px;
	color: #909399;
	margin-bottom: 6px;
}
.stat-value {
	font-size: 22px;
	font-weight: 600;
	color: #303133;
}

/* 让 fs-page 内部的 content 区域也用 flex 布局 */
:deep(.fs-page-content) {
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.crud-card {
	flex: 1;
	min-height: 0;
	display: flex;
	flex-direction: column;
	:deep(.el-card__body) {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
}
</style>
