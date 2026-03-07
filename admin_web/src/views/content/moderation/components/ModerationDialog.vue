<template>
	<el-dialog
		:model-value="visible"
		:title="dialogTitle"
		width="600px"
		:close-on-click-modal="false"
		@update:model-value="handleClose"
	>
		<el-form
			ref="formRef"
			:model="form"
			:rules="rules"
			label-width="100px"
		>
			<el-form-item label="用户" prop="user_id">
				<el-input
					v-model="form.user_id"
					placeholder="请输入用户ID"
					disabled
				/>
			</el-form-item>
			
			<el-form-item label="时长" prop="duration">
				<el-radio-group v-model="durationPreset" @change="handlePresetChange">
					<el-radio value="1h">1小时</el-radio>
					<el-radio value="3h">3小时</el-radio>
					<el-radio value="1d">1天</el-radio>
					<el-radio value="3d">3天</el-radio>
					<el-radio value="7d">7天</el-radio>
					<el-radio value="1w">1周</el-radio>
					<el-radio value="1m">1个月</el-radio>
					<el-radio value="permanent">永久</el-radio>
					<el-radio value="custom">自定义</el-radio>
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
		
		<template #footer>
			<el-button @click="handleClose">取消</el-button>
			<el-button type="primary" :loading="loading" @click="handleSubmit">
				确定
			</el-button>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch, nextTick } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import * as api from '/@/api/moderation';
import { successMessage, errorMessage } from '/@/utils/message';

interface Props {
	visible: boolean;
	type: 'mute' | 'ban';
	mode: 'create' | 'modify';
	preSelectedUser?: any; // 预选用户
}

const props = defineProps<Props>();
const emit = defineEmits(['update:visible', 'success']);

const formRef = ref<FormInstance>();
const loading = ref(false);

// 表单数据
const form = ref({
	user_id: undefined as string | undefined,
	duration: '',
	reason: '',
});

// 时长预设
const durationPreset = ref('1d');
const customDurationValue = ref(1);
const customDurationUnit = ref('d');

// 对话框标题
const dialogTitle = computed(() => {
	if (props.type === 'mute') {
		return props.mode === 'create' ? '添加禁言' : '修改禁言';
	}
	return props.mode === 'create' ? '添加封禁' : '修改封禁';
});

// 表单验证规则
const rules: FormRules = {
	user_id: [
		{ required: true, message: '请输入用户ID', trigger: 'blur' },
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
 * 监听对话框打开，自动填充预选用户
 */
watch(() => props.visible, async (isVisible) => {
	if (isVisible) {
		// 先重置表单
		await nextTick();
		formRef.value?.clearValidate();
		
		// 如果有预选用户，填充用户ID
		if (props.preSelectedUser) {
			form.value.user_id = props.preSelectedUser.id;
		}
		
		// 设置默认时长
		form.value.duration = '1d';
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
		user_id: undefined,
		duration: '',
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
					user_id: form.value.user_id!,
					duration: form.value.duration,
					reason: form.value.reason,
				};
				
				if (props.type === 'mute') {
					await api.muteUser(data);
					successMessage('禁言成功');
				} else {
					await api.banUser(data);
					successMessage('封禁成功');
				}
				
				emit('success');
				handleClose();
			} catch (error: any) {
				errorMessage('操作失败：' + (error.message || '未知错误'));
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
