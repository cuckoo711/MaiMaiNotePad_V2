<template>
	<el-dialog
		:model-value="visible"
		:title="dialogTitle"
		width="700px"
		:close-on-click-modal="false"
		@update:model-value="handleClose"
	>
		<!-- 第一步：输入参数 -->
		<div v-if="step === 1">
			<el-form
				ref="formRef"
				:model="form"
				:rules="rules"
				label-width="100px"
			>
				<el-form-item label="用户ID" prop="user_ids_text">
					<el-input
						v-model="form.user_ids_text"
						type="textarea"
						:rows="4"
						placeholder="请输入用户ID，多个ID用逗号分隔，最多20个"
					/>
					<div style="margin-top: 8px; font-size: 12px; color: #909399;">
						已输入 {{ parsedUserIds.length }} 个用户ID
						<span v-if="parsedUserIds.length > 20" style="color: #f56c6c;">
							（超过限制，最多20个）
						</span>
					</div>
				</el-form-item>
				
				<el-form-item v-if="type === 'mute'" label="时长" prop="duration">
					<el-radio-group v-model="durationPreset" @change="handlePresetChange">
						<el-radio label="1h">1小时</el-radio>
						<el-radio label="3h">3小时</el-radio>
						<el-radio label="1d">1天</el-radio>
						<el-radio label="3d">3天</el-radio>
						<el-radio label="7d">7天</el-radio>
						<el-radio label="1w">1周</el-radio>
						<el-radio label="1m">1个月</el-radio>
						<el-radio label="permanent">永久</el-radio>
						<el-radio label="custom">自定义</el-radio>
					</el-radio-group>
					
					<div v-if="durationPreset === 'custom'" style="margin-top: 12px; display: flex; gap: 8px;">
						<el-input-number
							v-model="customDurationValue"
							:min="1"
							:max="9999"
							placeholder="数值"
							style="width: 150px;"
						/>
						<el-select v-model="customDurationUnit" style="width: 100px;">
							<el-option label="小时" value="h" />
							<el-option label="天" value="d" />
							<el-option label="周" value="w" />
							<el-option label="月" value="m" />
						</el-select>
					</div>
				</el-form-item>
				
				<el-form-item label="原因" prop="reason">
					<el-input
						v-model="form.reason"
						type="textarea"
						:rows="4"
						placeholder="请输入原因"
					/>
				</el-form-item>
			</el-form>
		</div>
		
		<!-- 第二步：确认信息 -->
		<div v-else-if="step === 2">
			<el-alert
				:title="`即将批量${operationText} ${parsedUserIds.length} 个用户`"
				type="warning"
				:closable="false"
				style="margin-bottom: 16px"
			/>
			
			<el-descriptions :column="1" border>
				<el-descriptions-item label="操作类型">
					{{ operationText }}
				</el-descriptions-item>
				<el-descriptions-item label="用户数量">
					{{ parsedUserIds.length }} 个
				</el-descriptions-item>
				<el-descriptions-item v-if="type === 'mute'" label="时长">
					{{ form.duration }}
				</el-descriptions-item>
				<el-descriptions-item label="原因">
					{{ form.reason }}
				</el-descriptions-item>
			</el-descriptions>
		</div>
		
		<!-- 第三步：显示结果 -->
		<div v-else-if="step === 3">
			<el-alert
				:title="`批量操作完成：成功 ${result.success} 个，失败 ${result.failed} 个`"
				:type="result.failed === 0 ? 'success' : 'warning'"
				:closable="false"
				style="margin-bottom: 16px"
			/>
			
			<el-table :data="result.results" border stripe max-height="400">
				<el-table-column type="index" label="序号" width="70" align="center" />
				<el-table-column prop="user_id" label="用户ID" width="100" />
				<el-table-column prop="user_name" label="用户名" width="120" />
				<el-table-column prop="status" label="状态" width="100" align="center">
					<template #default="{ row }">
						<el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
							{{ row.status === 'success' ? '成功' : '失败' }}
						</el-tag>
					</template>
				</el-table-column>
				<el-table-column prop="reason" label="失败原因" min-width="200" show-overflow-tooltip />
			</el-table>
		</div>
		
		<template #footer>
			<el-button v-if="step === 1" @click="handleClose">取消</el-button>
			<el-button v-if="step === 1" type="primary" @click="handleNext">
				下一步
			</el-button>
			
			<el-button v-if="step === 2" @click="step = 1">上一步</el-button>
			<el-button v-if="step === 2" type="primary" :loading="loading" @click="handleSubmit">
				确定执行
			</el-button>
			
			<el-button v-if="step === 3" type="primary" @click="handleClose">
				关闭
			</el-button>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import * as api from '/@/api/moderation';
import type { BatchOperationResponse } from '/@/api/moderation';
import { successMessage, errorMessage } from '/@/utils/message';

interface Props {
	visible: boolean;
	type: 'mute' | 'unmute' | 'ban' | 'unban';
	preSelectedUsers?: any[]; // 预选用户列表
}

const props = defineProps<Props>();
const emit = defineEmits(['update:visible', 'success']);

const formRef = ref<FormInstance>();
const loading = ref(false);
const step = ref(1);

// 表单数据
const form = ref({
	user_ids_text: '',
	duration: '',
	reason: '',
});

// 时长预设
const durationPreset = ref('1d');
const customDurationValue = ref(1);
const customDurationUnit = ref('d');

// 操作结果
const result = ref<BatchOperationResponse>({
	total: 0,
	success: 0,
	failed: 0,
	results: [],
});

// 解析用户ID列表
const parsedUserIds = computed(() => {
	if (!form.value.user_ids_text) return [];
	return form.value.user_ids_text
		.split(',')
		.map(id => id.trim())
		.filter(id => id && /^\d+$/.test(id))
		.map(id => parseInt(id));
});

// 操作文本
const operationText = computed(() => {
	const map: Record<string, string> = {
		mute: '禁言',
		unmute: '解除禁言',
		ban: '封禁',
		unban: '解除封禁',
	};
	return map[props.type] || '';
});

// 对话框标题
const dialogTitle = computed(() => {
	if (step.value === 1) return `批量${operationText.value}`;
	if (step.value === 2) return '确认操作';
	return '操作结果';
});

// 表单验证规则
const rules: FormRules = {
	user_ids_text: [
		{ required: true, message: '请输入用户ID', trigger: 'blur' },
		{
			validator: (rule, value, callback) => {
				if (parsedUserIds.value.length === 0) {
					callback(new Error('请输入有效的用户ID'));
				} else if (parsedUserIds.value.length > 20) {
					callback(new Error('最多支持20个用户'));
				} else {
					callback();
				}
			},
			trigger: 'blur',
		},
	],
	duration: [
		{ required: true, message: '请选择时长', trigger: 'change' },
	],
	reason: [
		{ required: true, message: '请输入原因', trigger: 'blur' },
		{ min: 2, max: 500, message: '原因长度在 2 到 500 个字符', trigger: 'blur' },
	],
};

/**
 * 处理预设时长变化
 */
const handlePresetChange = (value: string) => {
	if (value === 'custom') {
		form.value.duration = `${customDurationValue.value}${customDurationUnit.value}`;
	} else {
		form.value.duration = value;
	}
};

/**
 * 监听自定义时长变化
 */
watch([customDurationValue, customDurationUnit], () => {
	if (durationPreset.value === 'custom') {
		form.value.duration = `${customDurationValue.value}${customDurationUnit.value}`;
	}
});

/**
 * 监听预选用户变化
 */
watch(() => props.preSelectedUsers, (newUsers) => {
	if (newUsers && newUsers.length > 0 && props.visible) {
		const userIds = newUsers.map(user => user.id).join(', ');
		form.value.user_ids_text = userIds;
	}
}, { immediate: true });

/**
 * 下一步
 */
const handleNext = async () => {
	if (!formRef.value) return;
	
	await formRef.value.validate((valid) => {
		if (valid) {
			step.value = 2;
		}
	});
};

/**
 * 提交表单
 */
const handleSubmit = async () => {
	loading.value = true;
	try {
		const data: any = {
			user_ids: parsedUserIds.value,
			reason: form.value.reason,
		};
		
		if (props.type === 'mute' || props.type === 'ban') {
			data.duration = form.value.duration;
		}
		
		let response: BatchOperationResponse;
		
		if (props.type === 'mute') {
			response = await api.batchMute(data);
		} else if (props.type === 'unmute') {
			response = await api.batchUnmute(data);
		} else if (props.type === 'ban') {
			response = await api.batchBan(data);
		} else {
			response = await api.batchUnban(data);
		}
		
		result.value = response;
		step.value = 3;
		
		if (response.failed === 0) {
			successMessage(`批量${operationText.value}成功`);
		} else {
			successMessage(`批量${operationText.value}完成：成功 ${response.success} 个，失败 ${response.failed} 个`);
		}
		
		emit('success');
	} catch (error: any) {
		errorMessage(`批量${operationText.value}失败：` + (error.message || '未知错误'));
	} finally {
		loading.value = false;
	}
};

/**
 * 关闭对话框
 */
const handleClose = () => {
	emit('update:visible', false);
	resetForm();
};

/**
 * 重置表单
 */
const resetForm = () => {
	formRef.value?.resetFields();
	form.value = {
		user_ids_text: '',
		duration: '',
		reason: '',
	};
	durationPreset.value = '1d';
	customDurationValue.value = 1;
	customDurationUnit.value = 'd';
	step.value = 1;
	result.value = {
		total: 0,
		success: 0,
		failed: 0,
		results: [],
	};
};
</script>

<style lang="scss" scoped>
:deep(.el-radio) {
	margin-right: 12px;
	margin-bottom: 8px;
}
</style>
