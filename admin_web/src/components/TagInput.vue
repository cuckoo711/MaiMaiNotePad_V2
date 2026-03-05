<template>
	<div class="tag-input">
		<div class="tag-list">
			<el-tag
				v-for="(tag, index) in tags"
				:key="index"
				closable
				:disable-transitions="false"
				@close="handleRemoveTag(index)"
				class="tag-item"
			>
				{{ tag }}
			</el-tag>
			<el-input
				v-if="inputVisible"
				ref="inputRef"
				v-model="inputValue"
				class="tag-input-field"
				size="small"
				:placeholder="placeholder"
				:disabled="isMaxTagsReached"
				@keydown="handleKeyDown"
				@blur="handleInputConfirm"
			/>
			<el-button
				v-else
				class="button-new-tag"
				size="small"
				:disabled="isMaxTagsReached"
				@click="showInput"
			>
				+ 添加标签
			</el-button>
			<span class="tag-count-hint">{{ tagCountHint }}</span>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, nextTick, watch, computed } from 'vue';
import { ElInput, ElMessage } from 'element-plus';

/**
 * 标签输入组件
 * 
 * 功能：
 * - 显示标签列表，支持删除
 * - 输入框支持多种分隔符：空格、逗号（中英文）、顿号、回车
 * - 自动去重和去空格
 * - 支持标签数量和长度限制
 */

interface Props {
	modelValue: string | string[]; // 标签数据，支持字符串（逗号分隔）或数组格式
	placeholder?: string;
	disabled?: boolean;
	maxTags?: number; // 最大标签数量
	maxLength?: number; // 单个标签最大长度
}

const props = withDefaults(defineProps<Props>(), {
	placeholder: '输入标签后按空格、逗号或回车添加',
	disabled: false,
	maxTags: 20,
	maxLength: 50,
});

const emit = defineEmits<{
	(e: 'update:modelValue', value: string[]): void;
}>();

// 标签数组
const tags = ref<string[]>([]);

// 输入框相关
const inputVisible = ref(false);
const inputValue = ref('');
const inputRef = ref<InstanceType<typeof ElInput>>();

// 分隔符正则：空格、中英文逗号、顿号
const separatorRegex = /[\s,，、]+/;

// 计算当前标签数量提示
const tagCountHint = computed(() => {
	return `${tags.value.length}/${props.maxTags}`;
});

// 是否达到标签数量限制
const isMaxTagsReached = computed(() => {
	return tags.value.length >= props.maxTags;
});

/**
 * 解析标签数据为数组
 * 支持字符串（逗号分隔）和数组格式
 */
const parseTagsString = (tagsData: string | string[]): string[] => {
	if (!tagsData) return [];
	
	// 如果已经是数组，直接返回处理后的数组
	if (Array.isArray(tagsData)) {
		return tagsData.map(tag => tag.trim()).filter(tag => tag.length > 0);
	}
	
	// 如果是字符串，按逗号分割
	return tagsData
		.split(',')
		.map(tag => tag.trim())
		.filter(tag => tag.length > 0);
};

/**
 * 将标签数组转换为字符串（已废弃，现在直接发送数组）
 */
const tagsToString = (tagArray: string[]): string => {
	return tagArray.join(',');
};

/**
 * 初始化标签
 */
watch(
	() => props.modelValue,
	(newValue) => {
		tags.value = parseTagsString(newValue);
	},
	{ immediate: true }
);

/**
 * 显示输入框
 */
const showInput = () => {
	if (props.disabled) return;
	
	// 检查是否达到标签数量限制
	if (isMaxTagsReached.value) {
		ElMessage.warning(`最多只能添加 ${props.maxTags} 个标签`);
		return;
	}
	
	inputVisible.value = true;
	nextTick(() => {
		inputRef.value?.focus();
	});
};

/**
 * 处理键盘事件
 */
const handleKeyDown = (event: KeyboardEvent) => {
	const value = inputValue.value.trim();
	
	// 检查是否按下了分隔符键
	const isSeparator = 
		event.key === 'Enter' || 
		event.key === ' ' || 
		event.key === ',' || 
		event.key === '，' || 
		event.key === '、';
	
	if (isSeparator && value) {
		event.preventDefault();
		addTag(value);
		inputValue.value = '';
	}
	
	// 如果输入框为空且按下退格键，删除最后一个标签
	if (event.key === 'Backspace' && !inputValue.value && tags.value.length > 0) {
		handleRemoveTag(tags.value.length - 1);
	}
};

/**
 * 处理输入框失焦
 */
const handleInputConfirm = () => {
	const value = inputValue.value.trim();
	if (value) {
		addTag(value);
	}
	inputVisible.value = false;
	inputValue.value = '';
};

/**
 * 添加标签
 */
const addTag = (tag: string) => {
	// 检查标签数量限制
	if (tags.value.length >= props.maxTags) {
		ElMessage.warning(`最多只能添加 ${props.maxTags} 个标签`);
		return;
	}
	
	// 分割可能包含多个标签的字符串
	const newTags = tag
		.split(separatorRegex)
		.map(t => t.trim())
		.filter(t => t.length > 0);
	
	// 检查每个标签的长度
	for (const newTag of newTags) {
		if (newTag.length > props.maxLength) {
			ElMessage.warning(`标签"${newTag}"长度超过 ${props.maxLength} 个字符`);
			return;
		}
	}
	
	// 过滤重复标签
	const uniqueNewTags = newTags.filter(t => !tags.value.includes(t));
	
	if (uniqueNewTags.length === 0) {
		if (newTags.length > 0 && newTags.length === newTags.filter(t => tags.value.includes(t)).length) {
			ElMessage.warning('标签已存在');
		}
		return;
	}
	
	// 检查添加后是否超过限制
	if (tags.value.length + uniqueNewTags.length > props.maxTags) {
		ElMessage.warning(`最多只能添加 ${props.maxTags} 个标签`);
		return;
	}
	
	tags.value.push(...uniqueNewTags);
	// 发送数组格式给父组件
	emit('update:modelValue', tags.value);
};

/**
 * 删除标签
 */
const handleRemoveTag = (index: number) => {
	if (props.disabled) return;
	tags.value.splice(index, 1);
	// 发送数组格式给父组件
	emit('update:modelValue', tags.value);
};
</script>

<style scoped lang="scss">
.tag-input {
	.tag-list {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		align-items: center;
		min-height: 32px;
		padding: 4px;
		border: 1px solid var(--el-border-color);
		border-radius: 4px;
		background: var(--el-fill-color-blank);
		transition: border-color 0.2s;

		&:hover {
			border-color: var(--el-border-color-hover);
		}

		&:focus-within {
			border-color: var(--el-color-primary);
		}

		.tag-item {
			margin: 0;
			cursor: default;
			user-select: none;
		}

		.tag-input-field {
			flex: 1;
			min-width: 120px;
			
			:deep(.el-input__wrapper) {
				box-shadow: none;
				padding: 0 4px;
			}
		}

		.button-new-tag {
			height: 24px;
			padding: 0 8px;
			font-size: 12px;
			border-style: dashed;
		}

		.tag-count-hint {
			margin-left: auto;
			font-size: 12px;
			color: var(--el-text-color-secondary);
			white-space: nowrap;
		}
	}
}
</style>
