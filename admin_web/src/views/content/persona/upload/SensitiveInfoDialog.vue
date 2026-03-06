<template>
	<el-dialog
		v-model="dialogVisible"
		title="敏感信息确认"
		width="600px"
		:close-on-click-modal="false"
		:close-on-press-escape="false"
	>
		<div class="sensitive-info-dialog">
			<!-- 提示信息 -->
			<el-alert
				title="检测到配置中包含疑似敏感信息"
				type="warning"
				:closable="false"
				show-icon
			>
				<template #default>
					<p>系统检测到您的配置文件中包含 5-11 位连续数字，可能是 QQ 号或群号等敏感信息。</p>
					<p>为保护隐私，请确认这些信息不涉及个人隐私。</p>
				</template>
			</el-alert>

			<!-- 敏感信息列表 -->
			<div class="sensitive-list">
				<h4>检测到的敏感信息位置：</h4>
				<el-table :data="props.sensitiveItems" border stripe max-height="300">
					<el-table-column prop="path" label="配置项路径" min-width="150" />
					<el-table-column prop="value" label="包含的值" min-width="150" show-overflow-tooltip />
					<el-table-column label="匹配的数字" min-width="120">
						<template #default="{ row }">
							<el-tag
								v-for="(match, index) in row.matches"
								:key="index"
								type="danger"
								size="small"
								style="margin: 2px"
							>
								{{ match }}
							</el-tag>
						</template>
					</el-table-column>
				</el-table>
			</div>

			<!-- 确认声明 -->
			<div class="confirmation-section">
				<h4>确认声明：</h4>
				<p class="confirmation-required">请在下方输入框中输入：<strong>{{ confirmationText }}</strong></p>
				<el-input
					v-model="userInput"
					placeholder="请输入确认声明"
					clearable
				/>
			</div>

			<!-- 验证码 -->
			<div class="captcha-section">
				<h4>验证码验证：</h4>
				<div class="captcha-container">
					<el-input
						v-model="captchaValue"
						placeholder="请输入验证码"
						clearable
					/>
					<img
						v-if="captchaImage"
						:src="captchaImage"
						alt="验证码"
						class="captcha-image"
						@click="refreshCaptcha"
						title="点击刷新验证码"
					/>
				</div>
				<p class="tip">点击验证码图片可刷新</p>
			</div>

			<!-- 重试提示 -->
			<el-alert
				v-if="retryCount > 0"
				:title="`验证码错误次数：${retryCount}/10`"
				type="warning"
				:closable="false"
				show-icon
			/>

			<!-- 冷却期提示 -->
			<el-alert
				v-if="cooldownRemaining > 0"
				:title="`验证失败次数过多，请等待 ${cooldownRemaining} 秒后重试`"
				type="error"
				:closable="false"
				show-icon
			/>
		</div>

		<template #footer>
			<span class="dialog-footer">
				<el-button @click="handleCancel">取消</el-button>
				<el-button
					type="primary"
					@click="handleConfirm"
					:disabled="!canConfirm"
					:loading="isConfirming"
				>
					确认提交
				</el-button>
			</span>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { getBaseURL } from '/@/utils/baseUrl';
import type { SensitiveItem } from '/@/stores/personaUpload';

/**
 * 敏感信息确认对话框组件
 * 
 * 功能：
 * - 实现敏感信息确认对话框（Element Plus Dialog）
 * - 以表格形式列出所有敏感信息的位置
 * - 实现确认声明输入框（自动生成模板）
 * - 集成验证码组件（显示验证码图片）
 * - 实现验证码输入和刷新功能
 * - 显示重试次数和冷却期提示
 * 
 * 验证需求：9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7
 */

// Props
interface Props {
	visible: boolean;
	sensitiveItems: SensitiveItem[];
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
	'update:visible': [value: boolean];
	confirm: [data: {
		confirmation_text: string;
		captcha_key: string;
		captcha_value: string;
	}];
}>();

// 对话框可见性
const dialogVisible = computed({
	get: () => props.visible,
	set: (value: boolean) => emit('update:visible', value),
});

// 确认声明文本（固定文本）
const confirmationText = computed(() => {
	return '我确认这些内容不涉及个人隐私信息';
});

// 用户输入的确认声明
const userInput = ref('');

// 验证码相关
const captchaKey = ref('');
const captchaImage = ref('');
const captchaValue = ref('');

// 重试次数
const retryCount = ref(0);

// 冷却期剩余时间（秒）
const cooldownRemaining = ref(0);

// 是否正在确认
const isConfirming = ref(false);

// 是否可以确认
const canConfirm = computed(() => {
	return (
		userInput.value === confirmationText.value &&
		captchaValue.value.length > 0 &&
		cooldownRemaining.value === 0 &&
		!isConfirming.value
	);
});

/**
 * 刷新验证码
 */
const refreshCaptcha = async () => {
	try {
		// 使用 getBaseURL 构建完整的API路径
		const apiUrl = getBaseURL('api/captcha/');
		
		const response = await fetch(apiUrl, {
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
			},
		});
		
		if (!response.ok) {
			throw new Error('获取验证码失败');
		}
		
		const data = await response.json();
		
		if (data.code === 2000 && data.data) {
			captchaKey.value = String(data.data.key);
			captchaImage.value = data.data.image_base; // 后端返回的字段是 image_base
		} else {
			throw new Error(data.msg || '获取验证码失败');
		}
	} catch (error) {
		console.error('刷新验证码失败:', error);
		ElMessage.error('刷新验证码失败，请稍后重试');
	}
};

/**
 * 处理确认
 */
const handleConfirm = async () => {
	try {
		// 验证确认声明
		if (userInput.value !== confirmationText.value) {
			ElMessage.warning('确认声明输入不正确，请重新输入');
			return;
		}

		// 验证验证码
		if (!captchaValue.value) {
			ElMessage.warning('请输入验证码');
			return;
		}

		// 检查冷却期
		if (cooldownRemaining.value > 0) {
			ElMessage.warning(`请等待 ${cooldownRemaining.value} 秒后重试`);
			return;
		}

		isConfirming.value = true;

		// 触发确认事件
		emit('confirm', {
			confirmation_text: confirmationText.value,
			captcha_key: captchaKey.value,
			captcha_value: captchaValue.value,
		});

		// 重置状态
		resetState();
	} catch (error: any) {
		console.error('确认失败:', error);
		
		// 增加重试次数
		retryCount.value++;

		// 检查是否达到重试限制
		if (retryCount.value >= 10) {
			// 进入冷却期（60 秒）
			cooldownRemaining.value = 60;
			startCooldownTimer();
			ElMessage.error('验证失败次数过多，请等待 1 分钟后重试');
		} else {
			ElMessage.error(error.message || '确认失败，请检查验证码是否正确');
		}

		// 刷新验证码
		await refreshCaptcha();
	} finally {
		isConfirming.value = false;
	}
};

/**
 * 处理取消
 */
const handleCancel = () => {
	dialogVisible.value = false;
	resetState();
};

/**
 * 重置状态
 */
const resetState = () => {
	userInput.value = '';
	captchaValue.value = '';
	retryCount.value = 0;
	cooldownRemaining.value = 0;
};

/**
 * 启动冷却期计时器
 */
const startCooldownTimer = () => {
	const timer = setInterval(() => {
		cooldownRemaining.value--;
		if (cooldownRemaining.value <= 0) {
			clearInterval(timer);
			retryCount.value = 0; // 重置重试次数
		}
	}, 1000);
};

// 监听对话框可见性变化
watch(
	() => props.visible,
	async (newValue) => {
		if (newValue) {
			// 对话框打开时，刷新验证码
			await refreshCaptcha();
			resetState();
		}
	}
);
</script>

<style scoped lang="scss">
.sensitive-info-dialog {
	.el-alert {
		margin-bottom: 20px;

		p {
			margin: 5px 0;
			font-size: 14px;
		}
	}

	.sensitive-list {
		margin-bottom: 20px;

		h4 {
			font-size: 14px;
			font-weight: 600;
			margin-bottom: 10px;
			color: var(--el-text-color-primary);
		}
	}

	.confirmation-section {
		margin-bottom: 20px;

		h4 {
			font-size: 14px;
			font-weight: 600;
			margin-bottom: 10px;
			color: var(--el-text-color-primary);
		}

		.confirmation-required {
			font-size: 14px;
			color: var(--el-text-color-regular);
			margin: 10px 0;
			padding: 12px;
			background-color: var(--el-fill-color-light);
			border-radius: 4px;

			strong {
				color: var(--el-color-danger);
				font-weight: 600;
			}
		}

		.confirmation-text {
			margin-bottom: 10px;

			:deep(.el-textarea__inner) {
				background-color: var(--el-fill-color-light);
				color: var(--el-text-color-regular);
			}
		}

		.tip {
			font-size: 12px;
			color: var(--el-text-color-secondary);
			margin: 10px 0;
		}
	}

	.captcha-section {
		margin-bottom: 20px;

		h4 {
			font-size: 14px;
			font-weight: 600;
			margin-bottom: 10px;
			color: var(--el-text-color-primary);
		}

		.captcha-container {
			display: flex;
			align-items: center;
			gap: 10px;

			.el-input {
				flex: 1;
			}

			.captcha-image {
				height: 32px;
				border: 1px solid var(--el-border-color);
				border-radius: 4px;
				cursor: pointer;
				transition: opacity 0.3s;
				flex-shrink: 0;

				&:hover {
					opacity: 0.8;
				}
			}
		}

		.tip {
			font-size: 12px;
			color: var(--el-text-color-secondary);
			margin: 5px 0 0 0;
		}
	}
}

.dialog-footer {
	display: flex;
	justify-content: flex-end;
	gap: 10px;
}
</style>
