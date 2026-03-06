<template>
	<el-dialog
		v-model="dialogVisible"
		title="敏感信息确认"
		width="600px"
		:close-on-click-modal="false"
	>
		<div class="simple-sensitive-dialog">
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

			<!-- 确认提示 -->
			<div class="confirmation-tip">
				<el-icon color="var(--el-color-warning)" :size="16"><Warning /></el-icon>
				<span>请确认以上内容不涉及个人隐私信息后再保存</span>
			</div>
		</div>

		<template #footer>
			<span class="dialog-footer">
				<el-button @click="handleCancel">取消</el-button>
				<el-button type="primary" @click="handleConfirm">
					确认并保存
				</el-button>
			</span>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import { Warning } from '@element-plus/icons-vue';
import type { SensitiveItem } from '/@/stores/personaUpload';

/**
 * 简化版敏感信息确认对话框（用于编辑页面）
 * 
 * 不需要验证码，只需要用户确认即可
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
	confirm: [];
}>();

// 对话框可见性
const dialogVisible = computed({
	get: () => props.visible,
	set: (value: boolean) => emit('update:visible', value),
});

/**
 * 处理确认
 */
const handleConfirm = () => {
	emit('confirm');
};

/**
 * 处理取消
 */
const handleCancel = () => {
	dialogVisible.value = false;
};
</script>

<style scoped lang="scss">
.simple-sensitive-dialog {
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

	.confirmation-tip {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px;
		background-color: var(--el-color-warning-light-9);
		border-radius: 4px;
		font-size: 14px;
		color: var(--el-text-color-primary);
	}
}

.dialog-footer {
	display: flex;
	justify-content: flex-end;
	gap: 10px;
}
</style>
