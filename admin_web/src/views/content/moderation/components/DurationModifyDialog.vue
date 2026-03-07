<template>
	<el-dialog
		:model-value="visible"
		title="修改时长"
		width="600px"
		:close-on-click-modal="false"
		@update:model-value="handleClose"
	>
		<el-alert
			title="当前时长信息"
			type="info"
			:closable="false"
			style="margin-bottom: 16px"
		>
			<div>{{ currentDurationText }}</div>
		</el-alert>
		
		<el-form
			ref="formRef"
			:model="form"
			:rules="rules"
			label-width="100px"
		>
			<el-form-item label="新时长" prop="new_duration">
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
			
			<el-form-item label="修改原因" prop="reason">
				<el-input
					v-model="form.reason"
					type="textarea"
					:rows="4"
					placeholder="请输入修改原因（必填）"
				/>
			</el-form-item>
		</el-form>
		
		<template #footer>
			<el-button @click="handleClose">取消</el-button>
			<el-button type="primary" :loading="loading" @click="handleSubmit">
				确定修改
			</el-button>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import * as api from '/@/api/moderation';
import { successMessage, errorMessage } from '/@/utils/message';
import dayjs from 'dayjs';

interface Props {
	visible: boolean;
	userId: number;
	currentDuration?: string;
	operationType: 'mute' | 'ban';
}

const props = defineProps<Props>();
const emit = defineEmits(['update:visible', 'success']);

const formRef = ref<FormInstance>();
const loading = ref(false);

// 表单数据
const form = ref({
	new_duration: '',
	reason: '',
});

// 时长预设
const durationPreset = ref('1d');
const customDurationValue = ref(1);
const customDurationUnit = ref('d');

// 当前时长文本
const currentDurationText = computed(() => {
	if (!props.currentDuration) {
		return '当前：永久';
	}
	const until = dayjs(props.currentDuration);
	const now = dayjs();
	const diff = until.diff(now);
	
	if (diff <= 0) {
		return '当前：已过期';
	}
	
	const days = Math.floor(diff / (1000 * 60 * 60 * 24));
	const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
	
	if (days > 0) {
		return `当前：还剩${days}天${hours}小时（截止 ${until.format('YYYY-MM-DD HH:mm:ss')}）`;
	}
	return `当前：还剩${hours}小时（截止 ${until.format('YYYY-MM-DD HH:mm:ss')}）`;
});

// 表单验证规则
const rules: FormRules = {
	new_duration: [
		{ required: true, message: '请选择新时长', trigger: 'change' },
	],
	reason: [
		{ required: true, message: '请输入修改原因', trigger: 'blur' },
		{ min: 2, max: 500, message: '原因长度在 2 到 500 个字符', trigger: 'blur' },
	],
};

/**
 * 处理预设时长变化
 */
const handlePresetChange = (value: string) => {
	if (value === 'custom') {
		form.value.new_duration = `${customDurationValue.value}${customDurationUnit.value}`;
	} else {
		form.value.new_duration = value;
	}
};

/**
 * 监听自定义时长变化
 */
watch([customDurationValue, customDurationUnit], () => {
	if (durationPreset.value === 'custom') {
		form.value.new_duration = `${customDurationValue.value}${customDurationUnit.value}`;
	}
});

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
		new_duration: '',
		reason: '',
	};
	durationPreset.value = '1d';
	customDurationValue.value = 1;
	customDurationUnit.value = 'd';
};

/**
 * 提交表单
 */
const handleSubmit = async () => {
	if (!formRef.value) return;
	
	await formRef.value.validate(async (valid) => {
		if (valid) {
			loading.value = true;
			try {
				const data = {
					user_id: props.userId,
					operation_type: props.operationType,
					new_duration: form.value.new_duration,
					reason: form.value.reason,
				};
				
				await api.modifyDuration(data);
				successMessage('修改时长成功');
				
				emit('success');
				handleClose();
			} catch (error: any) {
				errorMessage('修改时长失败：' + (error.message || '未知错误'));
			} finally {
				loading.value = false;
			}
		}
	});
};
</script>

<style lang="scss" scoped>
:deep(.el-radio) {
	margin-right: 12px;
	margin-bottom: 8px;
}
</style>
