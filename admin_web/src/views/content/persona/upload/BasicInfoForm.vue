<template>
	<div class="basic-info-form">
		<el-form :model="formData" :rules="rules" ref="formRef" label-width="120px">
			<!-- 人设卡名称 -->
			<el-form-item label="人设卡名称" prop="name" required>
				<el-input
					v-model="formData.name"
					placeholder="请输入人设卡名称（1-200 个字符）"
					maxlength="200"
					show-word-limit
					@input="handleFormChange"
				/>
			</el-form-item>

			<!-- 人设卡描述 -->
			<el-form-item label="人设卡描述" prop="description" required>
				<el-input
					v-model="formData.description"
					type="textarea"
					:rows="4"
					placeholder="请输入人设卡描述（至少 10 个字符）"
					show-word-limit
					@input="handleFormChange"
				/>
			</el-form-item>

			<!-- 版权所有者 -->
			<el-form-item label="版权所有者" prop="copyright_owner">
				<el-input
					v-model="formData.copyright_owner"
					placeholder="可选，默认为您的用户名"
					@input="handleFormChange"
				/>
			</el-form-item>

			<!-- 标签 -->
			<el-form-item label="标签" prop="tags">
				<el-input
					v-model="formData.tags"
					placeholder="可选，多个标签用逗号分隔"
					@input="handleFormChange"
				/>
			</el-form-item>

			<!-- 公开状态 -->
			<el-form-item label="公开状态" prop="is_public">
				<el-switch
					v-model="formData.is_public"
					active-text="公开"
					inactive-text="私有"
					@change="handleFormChange"
				/>
				<div class="form-tip">
					公开的人设卡需要经过审核，审核通过后其他用户可以下载使用
				</div>
			</el-form-item>

			<!-- 配置文件上传 -->
			<el-form-item label="配置文件" prop="file" required>
				<el-upload
					ref="uploadRef"
					:auto-upload="false"
					:limit="1"
					:on-change="handleFileChange"
					:on-remove="handleFileRemove"
					:before-upload="beforeUpload"
					accept=".toml"
					drag
				>
					<el-icon class="el-icon--upload"><upload-filled /></el-icon>
					<div class="el-upload__text">
						将 bot_config.toml 文件拖到此处，或<em>点击上传</em>
					</div>
					<template #tip>
						<div class="el-upload__tip">
							只能上传 bot_config.toml 文件，且文件大小在 1KB-2MB 之间
						</div>
					</template>
				</el-upload>
			</el-form-item>

			<!-- 解析状态 -->
			<el-form-item v-if="parseStatus" label="解析状态">
				<el-alert
					:title="parseStatus.message"
					:type="parseStatus.type"
					:closable="false"
					show-icon
				/>
			</el-form-item>

			<!-- 敏感信息提示 -->
			<el-form-item v-if="hasSensitiveInfo" label="敏感信息">
				<el-alert
					title="检测到配置中包含疑似敏感信息（5-11 位数字），提交时需要确认"
					type="warning"
					:closable="false"
					show-icon
				/>
			</el-form-item>

			<!-- 操作按钮 -->
			<el-form-item>
				<el-button type="primary" @click="handleNext" :disabled="!canNext">
					下一步
				</el-button>
			</el-form-item>
		</el-form>
	</div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import { parseToml } from '/@/api/persona';
import type { FormInstance, FormRules, UploadFile, UploadInstance } from 'element-plus';
import type { BasicInfo, ParsedConfig } from '/@/stores/personaUpload';

/**
 * 基本信息表单组件
 * 
 * 功能：
 * - 实现基本信息表单（名称、描述、版权所有者、标签、公开状态）
 * - 实现文件上传组件（Element Plus Upload）
 * - 实现文件验证（文件名、大小、类型）
 * - 调用 parseToml API 解析文件
 * - 显示解析结果和敏感信息提示
 * 
 * 验证需求：2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3
 */

// Props
interface Props {
	basicInfo: BasicInfo;
	parsedConfig: ParsedConfig | null;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
	'update:basicInfo': [value: BasicInfo];
	'update:parsedConfig': [value: ParsedConfig | null];
	next: [];
}>();

// 表单引用
const formRef = ref<FormInstance>();
const uploadRef = ref<UploadInstance>();

// 表单数据
const formData = reactive<BasicInfo>({
	name: props.basicInfo.name,
	description: props.basicInfo.description,
	copyright_owner: props.basicInfo.copyright_owner,
	tags: props.basicInfo.tags,
	is_public: props.basicInfo.is_public,
});

// 表单验证规则
const rules: FormRules = {
	name: [
		{ required: true, message: '请输入人设卡名称', trigger: 'blur' },
		{ min: 1, max: 200, message: '名称长度应在 1-200 个字符之间', trigger: 'blur' },
	],
	description: [
		{ required: true, message: '请输入人设卡描述', trigger: 'blur' },
		{ min: 10, message: '描述至少需要 10 个字符', trigger: 'blur' },
	],
};

// 上传的文件
const uploadedFile = ref<File | null>(null);

// 解析状态
const parseStatus = ref<{
	type: 'success' | 'error' | 'warning' | 'info';
	message: string;
} | null>(null);

// 是否包含敏感信息
const hasSensitiveInfo = ref(false);

// 是否可以进入下一步
const canNext = computed(() => {
	return (
		formData.name.length >= 1 &&
		formData.name.length <= 200 &&
		formData.description.length >= 10 &&
		uploadedFile.value !== null &&
		props.parsedConfig !== null
	);
});

/**
 * 处理表单变化
 */
const handleFormChange = () => {
	emit('update:basicInfo', { ...formData });
};

/**
 * 文件上传前验证
 */
const beforeUpload = (file: File) => {
	// 验证文件名
	if (file.name !== 'bot_config.toml') {
		ElMessage.error('只能上传名为 bot_config.toml 的文件');
		return false;
	}

	// 验证文件大小（1KB - 2MB）
	const minSize = 1 * 1024; // 1KB
	const maxSize = 2 * 1024 * 1024; // 2MB
	if (file.size < minSize || file.size > maxSize) {
		ElMessage.error('文件大小必须在 1KB 到 2MB 之间');
		return false;
	}

	return true;
};

/**
 * 处理文件变化
 */
const handleFileChange = async (file: UploadFile) => {
	if (!file.raw) return;

	// 验证文件
	if (!beforeUpload(file.raw)) {
		uploadRef.value?.clearFiles();
		return;
	}

	uploadedFile.value = file.raw;

	// 解析文件
	await parseFile(file.raw);
};

/**
 * 处理文件移除
 */
const handleFileRemove = () => {
	uploadedFile.value = null;
	parseStatus.value = null;
	hasSensitiveInfo.value = false;
	emit('update:parsedConfig', null);
};

/**
 * 解析 TOML 文件
 */
const parseFile = async (file: File) => {
	try {
		parseStatus.value = {
			type: 'info',
			message: '正在解析文件...',
		};

		// 调用 API 解析文件
		const response = await parseToml(file);
		const { data } = response;

		if (!data) {
			throw new Error('解析失败：未返回数据');
		}

		// 更新解析结果
		const parsedConfig: ParsedConfig = {
			sections: data.sections || [],
			version: data.version || '',
			file_name: file.name,
			file_size: file.size,
		};

		emit('update:parsedConfig', parsedConfig);

		// 检查敏感信息
		if (data.sensitive_info && data.sensitive_info.length > 0) {
			hasSensitiveInfo.value = true;
			parseStatus.value = {
				type: 'warning',
				message: `文件解析成功，检测到 ${data.sensitive_info.length} 处疑似敏感信息`,
			};
		} else {
			hasSensitiveInfo.value = false;
			parseStatus.value = {
				type: 'success',
				message: '文件解析成功',
			};
		}
	} catch (error: any) {
		console.error('解析文件失败:', error);
		parseStatus.value = {
			type: 'error',
			message: error.message || '文件解析失败，请检查文件格式',
		};
		emit('update:parsedConfig', null);
	}
};

/**
 * 处理下一步
 */
const handleNext = async () => {
	if (!formRef.value) return;

	try {
		// 验证表单
		await formRef.value.validate();

		// 触发下一步事件
		emit('next');
	} catch (error) {
		ElMessage.warning('请填写完整的表单信息');
	}
};

// 监听 props 变化，同步到表单数据
watch(
	() => props.basicInfo,
	(newValue) => {
		Object.assign(formData, newValue);
	},
	{ deep: true }
);
</script>

<style scoped lang="scss">
.basic-info-form {
	max-width: 800px;
	margin: 0 auto;

	.form-tip {
		font-size: 12px;
		color: var(--el-text-color-secondary);
		margin-top: 5px;
	}

	:deep(.el-upload-dragger) {
		padding: 40px;
	}

	:deep(.el-icon--upload) {
		font-size: 67px;
		color: var(--el-text-color-placeholder);
		margin-bottom: 16px;
	}

	:deep(.el-upload__text) {
		color: var(--el-text-color-regular);
		font-size: 14px;

		em {
			color: var(--el-color-primary);
			font-style: normal;
		}
	}

	:deep(.el-upload__tip) {
		font-size: 12px;
		color: var(--el-text-color-secondary);
		margin-top: 7px;
	}
}
</style>
