<template>
	<div class="config-section" :class="{ 'is-deleted': section.is_deleted }">
		<!-- 配置块头部 -->
		<div class="section-header">
			<div class="section-info">
				<span class="section-name">{{ section.name }}</span>
				<el-tag v-if="section.is_deleted" type="danger" size="small">已删除</el-tag>
				<el-tag v-else type="success" size="small">{{ section.items.length }} 项</el-tag>
			</div>
			<div class="section-actions">
				<el-button
					v-if="!section.is_deleted"
					type="danger"
					size="small"
					plain
					@click="handleDelete"
				>
					<el-icon><Delete /></el-icon>
					删除配置块
				</el-button>
				<el-button
					v-else
					type="success"
					size="small"
					plain
					@click="handleRestore"
				>
					<el-icon><RefreshLeft /></el-icon>
					恢复配置块
				</el-button>
			</div>
		</div>

		<!-- 配置块注释 -->
		<div v-if="section.comment" class="section-comment">
			<el-icon><InfoFilled /></el-icon>
			<span>{{ section.comment }}</span>
		</div>

		<!-- 配置项列表 -->
		<div class="section-items">
			<slot name="items" :items="section.items"></slot>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { Delete, RefreshLeft, InfoFilled } from '@element-plus/icons-vue';
import { ElMessageBox } from 'element-plus';
import type { ConfigSection } from '/@/stores/personaUpload';

/**
 * 配置块组件
 * 
 * 功能：
 * - 实现配置块组件（Element Plus Collapse Item）
 * - 显示配置块名称和注释
 * - 包含删除配置块按钮
 * - 渲染配置项列表
 * 
 * 验证需求：7.1, 7.4
 */

// Props
interface Props {
	section: ConfigSection;
}

const props = defineProps<Props>();

// Emits
const emit = defineEmits<{
	delete: [];
	restore: [];
}>();

/**
 * 处理删除配置块
 */
const handleDelete = async () => {
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

		emit('delete');
	} catch {
		// 用户取消
	}
};

/**
 * 处理恢复配置块
 */
const handleRestore = () => {
	emit('restore');
};
</script>

<style scoped lang="scss">
.config-section {
	padding: 15px;
	margin-bottom: 15px;
	background: var(--el-fill-color-blank);
	border: 1px solid var(--el-border-color-lighter);
	border-radius: 4px;
	transition: all 0.3s;

	&.is-deleted {
		opacity: 0.6;
		background: var(--el-fill-color-light);
		border-color: var(--el-color-danger-light-5);
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 15px;
		padding-bottom: 10px;
		border-bottom: 1px solid var(--el-border-color-lighter);

		.section-info {
			display: flex;
			align-items: center;
			gap: 10px;

			.section-name {
				font-size: 16px;
				font-weight: 600;
				color: var(--el-text-color-primary);
			}
		}

		.section-actions {
			display: flex;
			gap: 8px;
		}
	}

	.section-comment {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		padding: 10px;
		margin-bottom: 15px;
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

		span {
			flex: 1;
		}
	}

	.section-items {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
}
</style>
