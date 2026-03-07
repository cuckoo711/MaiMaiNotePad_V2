<template>
	<el-drawer
		:model-value="visible"
		title="操作日志"
		size="600px"
		@update:model-value="handleClose"
	>
		<div v-loading="loading">
			<el-timeline v-if="logs.length > 0">
				<el-timeline-item
					v-for="log in logs"
					:key="log.id"
					:timestamp="formatDateTime(log.create_datetime)"
					placement="top"
					:color="getOperationColor(log.operation_type)"
				>
					<el-card>
						<template #header>
							<div style="display: flex; align-items: center; justify-content: space-between;">
								<span>
									<el-tag :type="getOperationTagType(log.operation_type)" size="small">
										{{ getOperationText(log.operation_type) }}
									</el-tag>
								</span>
								<span style="font-size: 12px; color: #909399;">
									操作人：{{ log.operator_name || '未知' }}
								</span>
							</div>
						</template>
						
						<el-descriptions :column="1" size="small">
							<el-descriptions-item label="目标用户">
								{{ log.target_user_name || log.target_user }}
							</el-descriptions-item>
							<el-descriptions-item label="操作原因">
								{{ log.reason || '-' }}
							</el-descriptions-item>
							<el-descriptions-item v-if="log.duration_hours !== undefined" label="时长">
								{{ formatDuration(log.duration_hours) }}
							</el-descriptions-item>
							<el-descriptions-item v-if="log.old_duration_hours !== undefined" label="原时长">
								{{ formatDuration(log.old_duration_hours) }}
							</el-descriptions-item>
							<el-descriptions-item v-if="log.extra_data && log.extra_data.user_ids" label="批量操作">
								共 {{ log.extra_data.user_ids.length }} 个用户
							</el-descriptions-item>
							<el-descriptions-item label="IP地址">
								{{ log.ip_address || '-' }}
							</el-descriptions-item>
						</el-descriptions>
					</el-card>
				</el-timeline-item>
			</el-timeline>
			
			<el-empty v-else description="暂无操作日志" />
			
			<!-- 分页 -->
			<div v-if="total > pageSize" style="margin-top: 16px; text-align: center;">
				<el-pagination
					v-model:current-page="currentPage"
					v-model:page-size="pageSize"
					:total="total"
					:page-sizes="[10, 20, 50]"
					layout="total, sizes, prev, pager, next"
					@current-change="fetchLogs"
					@size-change="fetchLogs"
				/>
			</div>
		</div>
	</el-drawer>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue';
import * as api from '/@/api/moderation';
import type { ModerationLog } from '/@/api/moderation';
import { errorMessage } from '/@/utils/message';
import dayjs from 'dayjs';

interface Props {
	visible: boolean;
	userId: number;
}

const props = defineProps<Props>();
const emit = defineEmits(['update:visible']);

const loading = ref(false);
const logs = ref<ModerationLog[]>([]);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);

/**
 * 获取操作日志
 */
const fetchLogs = async () => {
	if (!props.userId) return;
	
	loading.value = true;
	try {
		const response = await api.getModerationLogs({
			target_user_id: props.userId,
			page: currentPage.value,
			page_size: pageSize.value,
		});
		logs.value = response.data || [];
		total.value = response.total || 0;
	} catch (error: any) {
		errorMessage('获取操作日志失败：' + (error.message || '未知错误'));
	} finally {
		loading.value = false;
	}
};

/**
 * 监听visible变化，打开时加载数据
 */
watch(() => props.visible, (newVal) => {
	if (newVal) {
		currentPage.value = 1;
		fetchLogs();
	}
});

/**
 * 关闭抽屉
 */
const handleClose = () => {
	emit('update:visible', false);
};

/**
 * 格式化日期时间
 */
const formatDateTime = (dateTime: string) => {
	return dayjs(dateTime).format('YYYY-MM-DD HH:mm:ss');
};

/**
 * 格式化时长
 */
const formatDuration = (hours?: number) => {
	if (hours === undefined || hours === null) return '永久';
	if (hours === 0) return '永久';
	
	const days = Math.floor(hours / 24);
	const remainingHours = hours % 24;
	
	if (days > 0) {
		return remainingHours > 0 ? `${days}天${remainingHours}小时` : `${days}天`;
	}
	return `${hours}小时`;
};

/**
 * 获取操作类型文本
 */
const getOperationText = (type: string) => {
	const map: Record<string, string> = {
		mute: '禁言',
		unmute: '解除禁言',
		ban: '封禁',
		unban: '解除封禁',
		modify_duration: '修改时长',
	};
	return map[type] || type;
};

/**
 * 获取操作类型标签类型
 */
const getOperationTagType = (type: string) => {
	const map: Record<string, any> = {
		mute: 'danger',
		unmute: 'success',
		ban: 'danger',
		unban: 'success',
		modify_duration: 'warning',
	};
	return map[type] || 'info';
};

/**
 * 获取操作类型颜色
 */
const getOperationColor = (type: string) => {
	const map: Record<string, string> = {
		mute: '#f56c6c',
		unmute: '#67c23a',
		ban: '#f56c6c',
		unban: '#67c23a',
		modify_duration: '#e6a23c',
	};
	return map[type] || '#909399';
};
</script>

<style lang="scss" scoped>
:deep(.el-timeline-item__timestamp) {
	color: #909399;
	font-size: 12px;
}
</style>
