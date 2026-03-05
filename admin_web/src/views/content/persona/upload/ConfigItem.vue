<template>
	<div class="config-item" :class="{ 'is-deleted': item.is_deleted, 'has-sensitive': hasSensitiveInfo }">
		<!-- 配置项头部 -->
		<div class="item-header">
			<div class="item-info">
				<span class="item-key">{{ item.key }}</span>
				<el-tag :type="getTypeTagType(item.type)" size="small">{{ item.type }}</el-tag>
				<el-tag v-if="hasSensitiveInfo" type="warning" size="small">
					<el-icon><Warning /></el-icon>
					包含敏感信息
				</el-tag>
			</div>
		</div>

		<!-- 配置项值编辑 -->
		<div class="item-value">
			<!-- 字符串类型 -->
			<el-input
				v-if="item.type === 'string'"
				v-model="localValue"
				placeholder="请输入值"
				:disabled="readonly"
				@input="handleValueChange"
			/>

			<!-- 整数类型 -->
			<el-input-number
				v-else-if="item.type === 'integer'"
				v-model="localValue"
				:step="1"
				:precision="0"
				:disabled="readonly"
				:controls-position="'right'"
				style="width: 100%"
				@change="handleValueChange"
			/>

			<!-- 浮点数类型 -->
			<el-input-number
				v-else-if="item.type === 'float'"
				v-model="localValue"
				:step="0.1"
				:precision="2"
				:disabled="readonly"
				:controls-position="'right'"
				style="width: 100%"
				@change="handleValueChange"
			/>

			<!-- 布尔类型 -->
			<div v-else-if="item.type === 'boolean'" class="boolean-control">
				<el-switch
					v-model="localValue"
					:disabled="readonly"
					@change="handleValueChange"
				/>
				<span class="boolean-label">{{ localValue ? '是' : '否' }}</span>
			</div>

			<!-- 数组类型 -->
			<div v-else-if="item.type === 'array'" class="array-control">
				<el-input
					v-model="localValue"
					type="textarea"
					:rows="4"
					placeholder="JSON 数组格式，例如：[1, 2, 3] 或 ['a', 'b', 'c']"
					:disabled="readonly"
					@input="handleValueChange"
				/>
				<div v-if="arrayParseError" class="error-hint">
					<el-icon><WarningFilled /></el-icon>
					<span>{{ arrayParseError }}</span>
				</div>
			</div>

			<!-- 对象类型 -->
			<div v-else-if="item.type === 'object'" class="object-control">
				<el-input
					v-model="localValue"
					type="textarea"
					:rows="6"
					placeholder="JSON 对象格式，例如：{'key': 'value'}"
					:disabled="readonly"
					@input="handleValueChange"
				/>
				<div v-if="objectParseError" class="error-hint">
					<el-icon><WarningFilled /></el-icon>
					<span>{{ objectParseError }}</span>
				</div>
			</div>

			<!-- 其他类型 -->
			<el-input
				v-else
				v-model="localValue"
				placeholder="请输入值"
				:disabled="readonly"
				@input="handleValueChange"
			/>
		</div>

		<!-- 配置项注释 -->
		<div class="item-comment">
			<el-input
				v-model="localComment"
				placeholder="添加注释（可选）"
				size="small"
				:disabled="readonly"
				@input="handleCommentChange"
			>
				<template #prepend>
					<el-icon><Comment /></el-icon>
				</template>
			</el-input>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, watch, computed } from 'vue';
import { Comment, Warning, WarningFilled } from '@element-plus/icons-vue';
import type { ConfigItem } from '/@/stores/personaUpload';

/**
 * 配置项组件
 * 
 * 功能：
 * - 实现配置项组件
 * - 根据数据类型渲染不同的输入控件：
 *   - boolean: Element Plus Switch
 *   - string: Element Plus Input
 *   - integer/float: Element Plus InputNumber
 *   - array: Element Plus Table（可编辑）
 *   - object: JSON 编辑器
 * - 实现注释编辑功能
 * - 高亮显示包含敏感信息的配置项
 * 
 * 验证需求：7.2, 7.3, 7.5, 8.3
 */

// Props
interface Props {
	item: ConfigItem;
	readonly?: boolean;
	sensitiveMatches?: string[]; // 敏感信息匹配列表
}

const props = withDefaults(defineProps<Props>(), {
	readonly: false,
	sensitiveMatches: () => [],
});

// Emits
const emit = defineEmits<{
	'update:value': [value: any];
	'update:comment': [comment: string];
}>();

// 本地值
const localValue = ref<any>(props.item.value);
const localComment = ref<string>(props.item.comment || '');

// 数组解析错误
const arrayParseError = ref<string>('');
// 对象解析错误
const objectParseError = ref<string>('');

/**
 * 是否包含敏感信息
 */
const hasSensitiveInfo = computed(() => {
	return props.sensitiveMatches && props.sensitiveMatches.length > 0;
});

/**
 * 获取类型标签颜色
 */
const getTypeTagType = (type: string) => {
	const typeMap: Record<string, any> = {
		string: '',
		integer: 'success',
		float: 'success',
		boolean: 'warning',
		array: 'info',
		object: 'info',
	};
	return typeMap[type] || '';
};

/**
 * 验证 JSON 数组格式
 */
const validateArray = (value: string): boolean => {
	if (!value || value.trim() === '') {
		arrayParseError.value = '';
		return true;
	}

	try {
		const parsed = JSON.parse(value);
		if (!Array.isArray(parsed)) {
			arrayParseError.value = '格式错误：必须是数组格式';
			return false;
		}
		arrayParseError.value = '';
		return true;
	} catch (error) {
		arrayParseError.value = 'JSON 格式错误：' + (error as Error).message;
		return false;
	}
};

/**
 * 验证 JSON 对象格式
 */
const validateObject = (value: string): boolean => {
	if (!value || value.trim() === '') {
		objectParseError.value = '';
		return true;
	}

	try {
		const parsed = JSON.parse(value);
		if (typeof parsed !== 'object' || Array.isArray(parsed)) {
			objectParseError.value = '格式错误：必须是对象格式';
			return false;
		}
		objectParseError.value = '';
		return true;
	} catch (error) {
		objectParseError.value = 'JSON 格式错误：' + (error as Error).message;
		return false;
	}
};

/**
 * 处理值变化
 */
const handleValueChange = () => {
	// 验证复杂类型
	if (props.item.type === 'array') {
		validateArray(localValue.value);
	} else if (props.item.type === 'object') {
		validateObject(localValue.value);
	}

	emit('update:value', localValue.value);
};

/**
 * 处理注释变化
 */
const handleCommentChange = () => {
	emit('update:comment', localComment.value);
};

// 监听 props 变化，同步到本地数据
watch(
	() => props.item.value,
	(newValue) => {
		localValue.value = newValue;
	}
);

watch(
	() => props.item.comment,
	(newValue) => {
		localComment.value = newValue || '';
	}
);
</script>

<style scoped lang="scss">
.config-item {
	padding: 15px;
	background: var(--el-fill-color-lighter);
	border-radius: 4px;
	border: 1px solid var(--el-border-color-lighter);
	transition: all 0.3s;

	&.is-deleted {
		opacity: 0.5;
		background: var(--el-fill-color-light);
	}

	&.has-sensitive {
		border-color: var(--el-color-warning);
		background: var(--el-color-warning-light-9);
	}

	.item-header {
		margin-bottom: 12px;

		.item-info {
			display: flex;
			align-items: center;
			gap: 8px;
			flex-wrap: wrap;

			.item-key {
				font-weight: 500;
				font-size: 14px;
				color: var(--el-text-color-primary);
			}
		}
	}

	.item-value {
		margin-bottom: 12px;

		.boolean-control {
			display: flex;
			align-items: center;
			gap: 10px;

			.boolean-label {
				font-size: 14px;
				color: var(--el-text-color-regular);
			}
		}

		.array-control,
		.object-control {
			.error-hint {
				display: flex;
				align-items: center;
				gap: 6px;
				margin-top: 8px;
				padding: 8px;
				background: var(--el-color-error-light-9);
				border-radius: 4px;
				font-size: 12px;
				color: var(--el-color-error);

				.el-icon {
					flex-shrink: 0;
				}
			}
		}

		:deep(.el-input),
		:deep(.el-input-number),
		:deep(.el-switch) {
			width: 100%;
		}

		:deep(.el-textarea__inner) {
			font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
			font-size: 13px;
		}
	}

	.item-comment {
		:deep(.el-input-group__prepend) {
			padding: 0 10px;
			background: var(--el-fill-color-light);
		}
	}
}
</style>
