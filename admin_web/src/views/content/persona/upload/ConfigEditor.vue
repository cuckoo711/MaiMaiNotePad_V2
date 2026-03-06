<template>
	<div class="config-editor">
		<div class="editor-header">
			<h3>配置编辑</h3>
			<p class="subtitle">您可以编辑配置项的值和注释，或标记配置块为已删除</p>
		</div>

		<!-- 配置块列表 -->
		<div class="config-sections">
			<el-collapse v-model="activeNames" accordion>
				<el-collapse-item
					v-for="(section, index) in localSections"
					:key="section.name"
					:name="section.name"
					:disabled="section.is_deleted"
				>
					<template #title>
						<div class="section-title">
							<span class="section-name">
								<span class="original">{{ section.name }}</span>
								<span v-if="section.translated_name && section.translated_name !== section.name" class="translated">{{ section.translated_name }}</span>
							</span>
							<el-tag v-if="section.is_deleted" type="danger" size="small">已删除</el-tag>
							<el-tag v-else type="success" size="small">{{ section.items.length }} 项</el-tag>
						</div>
					</template>

					<!-- 配置块注释 -->
					<div v-if="section.comment" class="section-comment">
						<el-icon><InfoFilled /></el-icon>
						<span>{{ section.comment }}</span>
					</div>

					<!-- 配置项列表 -->
					<div class="config-items">
						<div
							v-for="(item, itemIndex) in section.items"
							:key="item.key"
							class="config-item"
							:class="{ 'is-deleted': item.is_deleted }"
						>
							<div class="item-header">
								<span class="item-key">
									<span class="original">{{ item.key }}</span>
									<span v-if="item.translated_key && item.translated_key !== item.key" class="translated">{{ item.translated_key }}</span>
								</span>
								<div class="item-tags">
									<el-tag :type="getTypeTagType(item.type)" size="small">{{ item.type }}</el-tag>
									<el-tag 
										v-if="hasSensitiveInfo(section.name, item.key)" 
										type="warning" 
										size="small" 
										effect="dark"
										class="sensitive-tag"
									>
										<el-icon><Warning /></el-icon>
										可能包含敏感信息
									</el-tag>
								</div>
							</div>

							<!-- 配置项值编辑 -->
							<div class="item-value">
								<!-- 字符串类型 - 使用多行文本框 -->
								<el-input
									v-if="item.type === 'string'"
									v-model="item.value"
									type="textarea"
									:rows="3"
									placeholder="请输入值"
									@input="handleItemChange(section.name, item.key)"
								/>

								<!-- 整数类型 -->
								<el-input-number
									v-else-if="item.type === 'integer'"
									v-model="item.value"
									:step="1"
									:precision="0"
									@change="handleItemChange(section.name, item.key)"
								/>

								<!-- 浮点数类型 -->
								<el-input-number
									v-else-if="item.type === 'float'"
									v-model="item.value"
									:step="0.1"
									:precision="2"
									@change="handleItemChange(section.name, item.key)"
								/>

								<!-- 布尔类型 -->
								<el-switch
									v-else-if="item.type === 'boolean'"
									v-model="item.value"
									@change="handleItemChange(section.name, item.key)"
								/>

								<!-- 数组和对象类型 -->
								<el-input
									v-else
									v-model="item.value"
									type="textarea"
									:rows="3"
									placeholder="JSON 格式"
									@input="handleItemChange(section.name, item.key)"
								/>
							</div>

							<!-- 配置项注释 -->
							<div class="item-comment">
								<el-input
									v-model="item.comment"
									placeholder="添加注释（可选）"
									size="small"
									@input="handleItemChange(section.name, item.key)"
								>
									<template #prepend>
										<el-icon><Comment /></el-icon>
									</template>
								</el-input>
							</div>
						</div>
					</div>

					<!-- 配置块操作 -->
					<div class="section-actions">
						<el-button
							v-if="!section.is_deleted"
							type="danger"
							size="small"
							plain
							@click="handleDeleteSection(section.name)"
						>
							<el-icon><Delete /></el-icon>
							删除此配置块
						</el-button>
						<el-button
							v-else
							type="success"
							size="small"
							plain
							@click="handleRestoreSection(section.name)"
						>
							<el-icon><RefreshLeft /></el-icon>
							恢复此配置块
						</el-button>
					</div>
				</el-collapse-item>
			</el-collapse>
		</div>

		<!-- 操作按钮 -->
		<div class="editor-actions">
			<el-button @click="handlePrev">上一步</el-button>
			<el-button type="primary" @click="handleSubmit">提交</el-button>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, watch, computed } from 'vue';
import { InfoFilled, Comment, Delete, RefreshLeft, Warning } from '@element-plus/icons-vue';
import { ElMessageBox } from 'element-plus';
import type { ConfigSection } from '/@/stores/personaUpload';

/**
 * 配置编辑器组件
 * 
 * 功能：
 * - 实现配置编辑器主组件
 * - 按配置块分组展示配置项
 * - 实现配置块折叠/展开功能
 * - 实时高亮显示包含敏感信息的配置项
 * - 实现保存按钮和验证逻辑
 * 
 * 验证需求：7.1, 7.2, 7.8, 8.3
 */

// Props
interface Props {
	sections: ConfigSection[];
	sensitiveInfo?: any[]; // 敏感信息列表
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
	'update:sections': [value: ConfigSection[]];
	'update:sensitiveInfo': [value: any[]];
	prev: [];
	submit: [];
}>();

// 本地配置块数据
const localSections = ref<ConfigSection[]>([...props.sections]);

// 当前展开的配置块
const activeNames = ref<string[]>([]);

// 实时检测到的敏感信息
const realtimeSensitiveInfo = ref<Map<string, string[]>>(new Map());

/**
 * 敏感信息检测正则表达式（5-11 位连续数字）
 */
const SENSITIVE_PATTERN = /\b\d{5,11}\b/g;

/**
 * 检测字符串中的敏感信息
 */
const detectSensitiveInfo = (value: any): string[] => {
	if (typeof value !== 'string') {
		value = String(value);
	}
	
	const matches = value.match(SENSITIVE_PATTERN);
	return matches ? Array.from(new Set(matches)) : [];
};

/**
 * 更新配置项的敏感信息检测
 */
const updateSensitiveDetection = (sectionName: string, itemKey: string, value: any) => {
	const path = `${sectionName}.${itemKey}`;
	const matches = detectSensitiveInfo(value);
	
	if (matches.length > 0) {
		realtimeSensitiveInfo.value.set(path, matches);
	} else {
		realtimeSensitiveInfo.value.delete(path);
	}
	
	// 通知父组件敏感信息变化
	emitSensitiveInfo();
};

/**
 * 将实时检测到的敏感信息转换为标准格式并发送给父组件
 */
const emitSensitiveInfo = () => {
	const sensitiveItems: any[] = [];
	
	realtimeSensitiveInfo.value.forEach((matches, path) => {
		const [section, key] = path.split('.');
		const sectionObj = localSections.value.find(s => s.name === section);
		if (!sectionObj) return;
		
		const item = sectionObj.items.find(i => i.key === key);
		if (!item) return;
		
		sensitiveItems.push({
			section,
			key,
			value: item.value,
			matches,
			path
		});
	});
	
	emit('update:sensitiveInfo', sensitiveItems);
};

/**
 * 初始化所有配置项的敏感信息检测
 */
const initializeSensitiveDetection = () => {
	realtimeSensitiveInfo.value.clear();
	
	localSections.value.forEach(section => {
		section.items.forEach(item => {
			updateSensitiveDetection(section.name, item.key, item.value);
		});
	});
	
	// 初始化后通知父组件
	emitSensitiveInfo();
};

/**
 * 检查配置项是否包含敏感信息（实时检测）
 */
const hasSensitiveInfo = (sectionName: string, itemKey: string) => {
	const path = `${sectionName}.${itemKey}`;
	return realtimeSensitiveInfo.value.has(path);
};

/**
 * 获取配置项的敏感信息匹配列表
 */
const getSensitiveMatches = (sectionName: string, itemKey: string) => {
	const path = `${sectionName}.${itemKey}`;
	return realtimeSensitiveInfo.value.get(path) || [];
};

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
 * 处理配置项变化
 */
const handleItemChange = (sectionName: string, itemKey: string) => {
	// 查找配置项
	const section = localSections.value.find(s => s.name === sectionName);
	if (!section) return;
	
	const item = section.items.find(i => i.key === itemKey);
	if (!item) return;
	
	// 实时检测敏感信息
	updateSensitiveDetection(sectionName, itemKey, item.value);
	
	// 触发更新事件
	emit('update:sections', localSections.value);
};

/**
 * 处理删除配置块
 */
const handleDeleteSection = async (sectionName: string) => {
	try {
		await ElMessageBox.confirm(
			'删除后，该配置块将在导出的文件中显示为空块并添加注释。确定要删除吗？',
			'确认删除',
			{
				confirmButtonText: '确定',
				cancelButtonText: '取消',
				type: 'warning',
			}
		);

		// 标记配置块为已删除
		const section = localSections.value.find((s) => s.name === sectionName);
		if (section) {
			section.is_deleted = true;
			section.items.forEach((item) => {
				item.is_deleted = true;
			});
		}

		// 触发更新事件
		emit('update:sections', localSections.value);
	} catch {
		// 用户取消
	}
};

/**
 * 处理恢复配置块
 */
const handleRestoreSection = (sectionName: string) => {
	// 取消删除标记
	const section = localSections.value.find((s) => s.name === sectionName);
	if (section) {
		section.is_deleted = false;
		section.items.forEach((item) => {
			item.is_deleted = false;
		});
	}

	// 触发更新事件
	emit('update:sections', localSections.value);
};

/**
 * 处理上一步
 */
const handlePrev = () => {
	emit('prev');
};

/**
 * 处理提交
 */
const handleSubmit = () => {
	emit('submit');
};

// 监听 props 变化，同步到本地数据
watch(
	() => props.sections,
	(newValue) => {
		localSections.value = [...newValue];
		// 重新初始化敏感信息检测
		initializeSensitiveDetection();
	},
	{ deep: true }
);

// 监听 sensitiveInfo 变化
watch(
	() => props.sensitiveInfo,
	(newValue) => {
		console.log('ConfigEditor 接收到 sensitiveInfo 更新:', newValue);
	},
	{ immediate: true, deep: true }
);

// 组件初始化时进行敏感信息检测
initializeSensitiveDetection();

// 计算属性：获取所有敏感信息的数量
const sensitiveCount = computed(() => realtimeSensitiveInfo.value.size);
</script>

<style scoped lang="scss">
.config-editor {
	.editor-header {
		margin-bottom: 20px;

		h3 {
			font-size: 18px;
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

	.config-sections {
		margin-bottom: 30px;

		.section-title {
			display: flex;
			align-items: center;
			gap: 10px;
			width: 100%;

			.section-name {
				flex: 1;
				font-weight: 500;
				color: var(--el-text-color-primary);
				display: flex;
				align-items: center;
				gap: 8px;

				.original {
					font-size: 15px;
					color: var(--el-text-color-primary);
					font-weight: 500;
				}

				.translated {
					font-size: 13px;
					color: var(--el-text-color-secondary);
					font-weight: 400;
				}
			}
		}

		.section-comment {
			display: flex;
			align-items: center;
			gap: 8px;
			padding: 10px;
			margin-bottom: 15px;
			background: var(--el-fill-color-light);
			border-radius: 4px;
			font-size: 13px;
			color: var(--el-text-color-secondary);

			.el-icon {
				color: var(--el-color-info);
			}
		}

		.config-items {
			.config-item {
				padding: 15px;
				margin-bottom: 15px;
				background: var(--el-fill-color-lighter);
				border-radius: 4px;
				border: 1px solid var(--el-border-color-lighter);

				&.is-deleted {
					opacity: 0.5;
					background: var(--el-fill-color-light);
				}

				.item-header {
					display: flex;
					align-items: center;
					justify-content: space-between;
					margin-bottom: 10px;

					.item-key {
						font-weight: 500;
						color: var(--el-text-color-primary);
						display: flex;
						align-items: center;
						gap: 8px;

						.original {
							font-size: 14px;
							color: var(--el-text-color-primary);
							font-weight: 500;
						}

						.translated {
							font-size: 12px;
							color: var(--el-text-color-secondary);
							font-weight: 400;
						}
					}

					.item-tags {
						display: flex;
						align-items: center;
						gap: 8px;

						:deep(.sensitive-tag) {
							display: inline-flex;
							align-items: center;
							gap: 4px;

							.el-icon {
								display: inline-flex;
								align-items: center;
							}
						}
					}
				}

				.item-value {
					margin-bottom: 10px;

					:deep(.el-input),
					:deep(.el-input-number),
					:deep(.el-switch) {
						width: 100%;
					}
				}

				.item-comment {
					:deep(.el-input-group__prepend) {
						padding: 0 10px;
					}
				}
			}
		}

		.section-actions {
			margin-top: 15px;
			padding-top: 15px;
			border-top: 1px solid var(--el-border-color-lighter);
		}
	}

	.editor-actions {
		display: flex;
		justify-content: space-between;
		padding-top: 20px;
		border-top: 1px solid var(--el-border-color-lighter);
	}
}
</style>
