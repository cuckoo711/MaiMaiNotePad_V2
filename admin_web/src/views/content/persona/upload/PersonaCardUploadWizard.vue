<template>
	<div class="persona-upload-wizard-container">
		<!-- 页面标题 -->
		<div class="page-header">
			<h2>上传人设卡</h2>
			<p class="subtitle">按照步骤填写信息并上传配置文件</p>
		</div>

		<!-- 步骤指示器 -->
		<el-steps :active="currentStep - 1" finish-status="success" align-center class="wizard-steps">
			<el-step title="基本信息" description="填写人设卡基本信息并上传文件" />
			<el-step title="配置编辑" description="编辑配置项并确认提交" />
		</el-steps>

		<!-- 步骤内容 -->
		<div class="wizard-content">
			<!-- 第一步：基本信息表单 -->
			<div v-show="currentStep === 1" class="step-content">
				<BasicInfoForm
					v-model:basic-info="basicInfo"
					v-model:parsed-config="parsedConfig"
					@next="handleNextStep"
				/>
			</div>

			<!-- 第二步：配置编辑器 -->
			<div v-show="currentStep === 2" class="step-content">
				<ConfigEditor
					v-if="parsedConfig"
					v-model:sections="parsedConfig.sections"
					@update:sensitiveInfo="handleSensitiveInfoUpdate"
					@prev="handlePrevStep"
					@submit="handleSubmit"
				/>
			</div>
		</div>

		<!-- 草稿恢复提示 -->
		<el-dialog
			v-model="showDraftDialog"
			title="发现草稿"
			width="400px"
			:close-on-click-modal="false"
		>
			<p>检测到您有未完成的上传草稿，是否恢复？</p>
			<template #footer>
				<span class="dialog-footer">
					<el-button @click="handleDiscardDraft">放弃草稿</el-button>
					<el-button type="primary" @click="handleRestoreDraft">恢复草稿</el-button>
				</span>
			</template>
		</el-dialog>

		<!-- 敏感信息确认对话框 -->
		<SensitiveInfoDialog
			v-model:visible="showSensitiveDialog"
			:sensitive-items="sensitiveItems"
			@confirm="handleSensitiveConfirm"
		/>
	</div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { usePersonaUploadStore } from '/@/stores/personaUpload';
import { createPersonaCardWithConfig } from '/@/api/persona';
import BasicInfoForm from './BasicInfoForm.vue';
import ConfigEditor from './ConfigEditor.vue';
import SensitiveInfoDialog from './SensitiveInfoDialog.vue';
import type { BasicInfo, ParsedConfig, SensitiveItem } from '/@/stores/personaUpload';

/**
 * 人设卡上传向导组件
 * 
 * 功能：
 * - 分步向导界面（Element Plus Steps 组件）
 * - 第一步：基本信息表单
 * - 第二步：配置编辑器
 * - 实现步骤切换逻辑
 * - 实现草稿自动保存和恢复
 * - 实现最终提交逻辑
 * 
 * 验证需求：14.4, 7.6, 7.7
 */

const router = useRouter();
const uploadStore = usePersonaUploadStore();

// 响应式状态
const showDraftDialog = ref(false);
const showSensitiveDialog = ref(false);
const isSubmitting = ref(false);

// 从 store 获取状态
const currentStep = computed(() => uploadStore.currentStep);
const basicInfo = computed({
	get: () => uploadStore.basicInfo,
	set: (value: BasicInfo) => uploadStore.updateBasicInfo(value),
});
const parsedConfig = computed({
	get: () => uploadStore.parsedConfig,
	set: (value: ParsedConfig | null) => {
		if (value) {
			uploadStore.setParsedConfig(value);
		}
	},
});
const sensitiveItems = computed(() => uploadStore.sensitiveItems);
const hasSensitiveInfo = computed(() => uploadStore.hasSensitiveInfo);

/**
 * 处理敏感信息更新
 */
const handleSensitiveInfoUpdate = (sensitiveItems: any[]) => {
	// 更新 store 中的敏感信息
	uploadStore.setSensitiveItems(sensitiveItems);
	console.log('检测到敏感信息:', sensitiveItems);
};

/**
 * 处理下一步
 * 验证需求：14.4
 */
const handleNextStep = () => {
	// 验证基本信息
	if (!uploadStore.isBasicInfoValid) {
		ElMessage.warning('请填写完整的基本信息');
		return;
	}

	// 验证是否有配置数据
	if (!uploadStore.hasConfigData) {
		ElMessage.warning('请先上传并解析配置文件');
		return;
	}

	// 进入下一步
	uploadStore.nextStep();
	
	// 自动保存草稿
	uploadStore.saveDraft();
};

/**
 * 处理上一步
 * 验证需求：14.4
 */
const handlePrevStep = () => {
	uploadStore.prevStep();
	
	// 自动保存草稿
	uploadStore.saveDraft();
};

/**
 * 处理提交
 * 验证需求：14.4, 9.1, 9.2, 9.3
 */
const handleSubmit = async () => {
	try {
		// 检查是否可以提交
		if (!uploadStore.canSubmit) {
			ElMessage.warning('数据不完整，无法提交');
			return;
		}

		// 如果包含敏感信息，显示确认对话框
		if (hasSensitiveInfo.value) {
			showSensitiveDialog.value = true;
			return;
		}

		// 直接提交（无敏感信息）
		await submitPersonaCard();
	} catch (error: any) {
		console.error('提交失败:', error);
		ElMessage.error(error.message || '提交失败，请稍后重试');
	}
};

/**
 * 处理敏感信息确认
 * 验证需求：9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8
 */
const handleSensitiveConfirm = async (confirmationData: {
	confirmation_text: string;
	captcha_key: string;
	captcha_value: string;
}) => {
	try {
		// 关闭对话框
		showSensitiveDialog.value = false;

		// 提交人设卡（包含敏感信息确认）
		await submitPersonaCard(confirmationData);
	} catch (error: any) {
		console.error('敏感信息确认失败:', error);
		
		// 如果是验证码错误，重新打开对话框
		if (error.message?.includes('验证码')) {
			showSensitiveDialog.value = true;
		}
		
		ElMessage.error(error.message || '确认失败，请稍后重试');
	}
};

/**
 * 提交人设卡
 * 验证需求：2.1, 2.2, 6.1, 10.1, 10.2
 */
const submitPersonaCard = async (sensitiveConfirmation?: {
	confirmation_text: string;
	captcha_key: string;
	captcha_value: string;
}) => {
	try {
		isSubmitting.value = true;

		// 生成提交数据
		const submitData = uploadStore.generateSubmitData();

		// 如果有敏感信息确认，添加到提交数据
		if (sensitiveConfirmation) {
			(submitData as any).sensitive_confirmation = {
				text: sensitiveConfirmation.confirmation_text,
				locations: sensitiveItems.value,
				captcha_key: sensitiveConfirmation.captcha_key,
				captcha_value: sensitiveConfirmation.captcha_value,
			};
		}

		// 调用 API 创建人设卡
		const response = await createPersonaCardWithConfig(submitData);

		// 提交成功
		ElMessage.success('人设卡创建成功！');

		// 清除草稿
		uploadStore.clearDraft();

		// 重置状态
		uploadStore.reset();

		// 根据是否公开跳转到不同页面
		if (basicInfo.value.is_public) {
			// 公开人设卡，提示审核中
			await ElMessageBox.alert(
				'您的人设卡已提交审核，审核通过后将在广场展示。',
				'提交成功',
				{
					confirmButtonText: '查看我的人设卡',
					type: 'success',
				}
			);
			router.push('/content/persona/manage');
		} else {
			// 私有人设卡，直接跳转到管理页面
			router.push('/content/persona/manage');
		}
	} catch (error: any) {
		console.error('提交人设卡失败:', error);
		throw error;
	} finally {
		isSubmitting.value = false;
	}
};

/**
 * 恢复草稿
 * 验证需求：7.7
 */
const handleRestoreDraft = () => {
	showDraftDialog.value = false;
	ElMessage.success('草稿已恢复');
};

/**
 * 放弃草稿
 * 验证需求：7.7
 */
const handleDiscardDraft = () => {
	uploadStore.clearDraft();
	uploadStore.reset();
	showDraftDialog.value = false;
	ElMessage.info('草稿已清除');
};

/**
 * 自动保存草稿
 * 验证需求：7.6
 */
const autoSaveDraft = () => {
	if (uploadStore.hasConfigData || uploadStore.basicInfo.name) {
		uploadStore.saveDraft();
	}
};

// 设置自动保存定时器
let autoSaveTimer: number | null = null;

/**
 * 组件挂载时
 */
onMounted(() => {
	// 尝试恢复草稿
	const hasDraft = uploadStore.loadDraft();
	
	if (hasDraft) {
		// 如果有草稿，显示恢复对话框
		showDraftDialog.value = true;
	}

	// 设置自动保存定时器（每 30 秒保存一次）
	autoSaveTimer = window.setInterval(autoSaveDraft, 30000);
});

/**
 * 组件卸载前
 */
onBeforeUnmount(() => {
	// 清除自动保存定时器
	if (autoSaveTimer !== null) {
		clearInterval(autoSaveTimer);
		autoSaveTimer = null;
	}

	// 最后保存一次草稿
	autoSaveDraft();
});
</script>

<style scoped lang="scss">
.persona-upload-wizard-container {
	padding: 20px;
	max-width: 1200px;
	margin: 0 auto;

	.page-header {
		margin-bottom: 30px;
		text-align: center;

		h2 {
			font-size: 24px;
			font-weight: 600;
			margin-bottom: 8px;
			color: var(--el-text-color-primary);
		}

		.subtitle {
			font-size: 14px;
			color: var(--el-text-color-secondary);
			margin: 0;
		}
	}

	.wizard-steps {
		margin-bottom: 40px;
		padding: 0 20px;
	}

	.wizard-content {
		background: var(--el-bg-color);
		border-radius: 8px;
		padding: 30px;
		box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

		.step-content {
			min-height: 400px;
		}
	}

	.dialog-footer {
		display: flex;
		justify-content: flex-end;
		gap: 10px;
	}
}

// 响应式布局
@media (max-width: 768px) {
	.persona-upload-wizard-container {
		padding: 10px;

		.wizard-content {
			padding: 20px 15px;
		}

		.wizard-steps {
			padding: 0 10px;
		}
	}
}
</style>
