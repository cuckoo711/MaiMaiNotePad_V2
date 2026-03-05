<template>
	<el-dialog
		v-model="dialogVisible"
		title="配置块删除提醒"
		width="600px"
		:close-on-click-modal="false"
		:close-on-press-escape="false"
	>
		<!-- 提醒内容 -->
		<div class="dialog-content">
			<div class="warning-message">
				<el-icon class="warning-icon"><WarningFilled /></el-icon>
				<div class="message-text">
					<p class="message-title">此人设卡包含已删除的配置块</p>
					<p class="message-desc">
						下载的配置文件中，这些配置块将显示为空块，并添加注释说明"此配置块已被作者删除"。
					</p>
				</div>
			</div>

			<!-- 被删除的配置块列表 -->
			<div class="deleted-sections">
				<h4>已删除的配置块：</h4>
				<el-table :data="deletedSectionsData" border stripe max-height="300">
					<el-table-column type="index" label="序号" width="60" align="center" />
					<el-table-column prop="name" label="配置块名称" min-width="200">
						<template #default="{ row }">
							<div class="section-name-cell">
								<el-icon class="delete-icon"><Delete /></el-icon>
								<span>{{ row.name }}</span>
							</div>
						</template>
					</el-table-column>
					<el-table-column prop="itemCount" label="配置项数量" width="120" align="center">
						<template #default="{ row }">
							<el-tag type="info" size="small">{{ row.itemCount }} 项</el-tag>
						</template>
					</el-table-column>
				</el-table>
			</div>

			<!-- 说明文字 -->
			<div class="info-note">
				<el-icon><InfoFilled /></el-icon>
				<span>如果您需要这些配置块，请联系作者或选择其他人设卡。</span>
			</div>
		</div>

		<!-- 对话框底部按钮 -->
		<template #footer>
			<div class="dialog-footer">
				<el-button @click="handleCancel">取消下载</el-button>
				<el-button type="primary" @click="handleConfirm">
					<el-icon><Download /></el-icon>
					确认下载
				</el-button>
			</div>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, computed, watch } from 'vue';
import { WarningFilled, InfoFilled, Delete, Download } from '@element-plus/icons-vue';

/**
 * 被删除块提醒对话框组件
 * 
 * 功能：
 * - 实现被删除块提醒对话框（Element Plus Dialog）
 * - 以表格形式列出所有被删除的配置块名称
 * - 实现确认下载按钮
 * 
 * 验证需求：13.5, 13.6
 */

// Props
interface Props {
	visible: boolean;
	deletedSections: string[]; // 被删除的配置块名称列表
	sectionDetails?: Array<{ name: string; itemCount: number }>; // 配置块详细信息（可选）
}

const props = withDefaults(defineProps<Props>(), {
	visible: false,
	deletedSections: () => [],
	sectionDetails: () => [],
});

// Emits
const emit = defineEmits<{
	'update:visible': [value: boolean];
	confirm: [];
	cancel: [];
}>();

// 对话框可见性
const dialogVisible = ref(props.visible);

/**
 * 被删除的配置块数据（用于表格显示）
 */
const deletedSectionsData = computed(() => {
	// 如果提供了详细信息，使用详细信息
	if (props.sectionDetails && props.sectionDetails.length > 0) {
		return props.sectionDetails;
	}

	// 否则，从配置块名称列表生成基本数据
	return props.deletedSections.map((name) => ({
		name,
		itemCount: 0, // 未知配置项数量
	}));
});

/**
 * 处理确认下载
 */
const handleConfirm = () => {
	emit('confirm');
	dialogVisible.value = false;
};

/**
 * 处理取消下载
 */
const handleCancel = () => {
	emit('cancel');
	dialogVisible.value = false;
};

// 监听 props.visible 变化，同步到本地状态
watch(
	() => props.visible,
	(newValue) => {
		dialogVisible.value = newValue;
	}
);

// 监听本地状态变化，同步到父组件
watch(dialogVisible, (newValue) => {
	emit('update:visible', newValue);
});
</script>

<style scoped lang="scss">
.dialog-content {
	.warning-message {
		display: flex;
		gap: 12px;
		padding: 16px;
		margin-bottom: 20px;
		background: var(--el-color-warning-light-9);
		border: 1px solid var(--el-color-warning-light-7);
		border-radius: 4px;

		.warning-icon {
			font-size: 24px;
			color: var(--el-color-warning);
			flex-shrink: 0;
			margin-top: 2px;
		}

		.message-text {
			flex: 1;

			.message-title {
				font-size: 16px;
				font-weight: 600;
				color: var(--el-text-color-primary);
				margin: 0 0 8px 0;
			}

			.message-desc {
				font-size: 14px;
				color: var(--el-text-color-regular);
				margin: 0;
				line-height: 1.6;
			}
		}
	}

	.deleted-sections {
		margin-bottom: 20px;

		h4 {
			font-size: 14px;
			font-weight: 600;
			color: var(--el-text-color-primary);
			margin: 0 0 12px 0;
		}

		.section-name-cell {
			display: flex;
			align-items: center;
			gap: 8px;

			.delete-icon {
				color: var(--el-color-danger);
				flex-shrink: 0;
			}
		}
	}

	.info-note {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 12px;
		background: var(--el-fill-color-light);
		border-radius: 4px;
		font-size: 13px;
		color: var(--el-text-color-secondary);
		line-height: 1.6;

		.el-icon {
			margin-top: 2px;
			color: var(--el-color-info);
			flex-shrink: 0;
		}
	}
}

.dialog-footer {
	display: flex;
	justify-content: flex-end;
	gap: 10px;
}
</style>
