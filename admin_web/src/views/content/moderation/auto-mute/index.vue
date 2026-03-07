<template>
	<fs-page>
		<el-card>
			<fs-crud ref="crudRef" v-bind="crudBinding">
				<!-- 自定义操作按钮 -->
				<template #actionbar-right>
					<!-- 导出 -->
					<el-button
						v-if="auth('autoMute:Export')"
						type="primary"
						@click="handleExport"
					>
						导出
					</el-button>
				</template>

				<!-- 自定义列显示 -->
				<template #cell_auto_unmute_status="scope">
					<el-tag
						:type="getStatusTagType(scope.row)"
						size="small"
					>
						{{ getAutoUnmuteStatusText(scope.row) }}
					</el-tag>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #row-handle="{ row }">
					<el-button
						v-if="auth('autoMute:Unmute') && row.is_active"
						link
						size="small"
						type="success"
						@click="handleUnmute(row)"
					>
						解除禁言
					</el-button>
					<el-button
						v-if="auth('autoMute:ModifyDuration') && row.is_active"
						link
						size="small"
						type="primary"
						@click="handleModifyDuration(row)"
					>
						修改时长
					</el-button>
					<el-button
						v-if="auth('autoMute:Detail')"
						link
						size="small"
						@click="handleViewDetail(row)"
					>
						查看详情
					</el-button>
				</template>
			</fs-crud>
		</el-card>

		<!-- 修改时长对话框 -->
		<DurationModifyDialog
			v-model:visible="durationDialogVisible"
			:user-id="currentUserId"
			:current-duration="currentDuration"
			:operation-type="'mute'"
			@success="handleDialogSuccess"
		/>

		<!-- 操作日志抽屉 -->
		<ModerationLogDrawer
			v-model:visible="logDrawerVisible"
			:user-id="currentUserId"
		/>

		<!-- 导出对话框 -->
		<el-dialog
			v-model="exportDialogVisible"
			title="导出数据"
			width="500px"
			:close-on-click-modal="false"
		>
			<el-form label-width="100px">
				<el-form-item label="导出格式">
					<el-radio-group v-model="exportForm.format">
						<el-radio label="excel">Excel (.xlsx)</el-radio>
						<el-radio label="csv">CSV (.csv)</el-radio>
					</el-radio-group>
				</el-form-item>
				<el-form-item label="导出范围">
					<el-tag type="info">导出全部记录</el-tag>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="exportDialogVisible = false">取消</el-button>
				<el-button type="primary" @click="executeExport">导出</el-button>
			</template>
		</el-dialog>
	</fs-page>
</template>

<script lang="ts" setup name="contentModerationAutoMute">
import { ref, onMounted, onUnmounted } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions, getAutoUnmuteStatus } from './crud';
import * as api from '/@/api/moderation';
import { auth } from '/@/utils/authFunction';
import { successMessage, errorMessage } from '/@/utils/message';
import { ElMessageBox } from 'element-plus';
import DurationModifyDialog from '../components/DurationModifyDialog.vue';
import ModerationLogDrawer from '../components/ModerationLogDrawer.vue';

// crud 组件的 ref
const crudRef = ref();
// crud 配置的 ref
const crudBinding = ref();
// 暴露的方法
const { crudExpose } = useExpose({ crudRef, crudBinding });
// crud 配置
const { crudOptions } = createCrudOptions({ crudExpose });
// 初始化 crud 配置
const { resetCrudOptions } = useCrud({ crudExpose, crudOptions });

// 对话框状态
const durationDialogVisible = ref(false);
const logDrawerVisible = ref(false);
const exportDialogVisible = ref(false);

// 当前操作的用户
const currentUserId = ref(0);
const currentDuration = ref<string | undefined>(undefined);

// 导出表单
const exportForm = ref({
	format: 'excel',
});

// 定时刷新倒计时
let refreshTimer: number | null = null;

/**
 * 获取自动解封状态文本
 */
const getAutoUnmuteStatusText = (row: any): string => {
	return getAutoUnmuteStatus(row);
};

/**
 * 获取状态标签类型
 */
const getStatusTagType = (row: any): string => {
	const status = getAutoUnmuteStatus(row);
	if (status === '等待中') return 'warning';
	if (status === '已解封') return 'success';
	if (status === '已被人工修改') return 'info';
	return 'info';
};

/**
 * 解除禁言
 */
const handleUnmute = (row: any) => {
	ElMessageBox.prompt('请输入解除原因（可选）', '解除禁言', {
		confirmButtonText: '确定',
		cancelButtonText: '取消',
		inputType: 'textarea',
	})
		.then(async ({ value }) => {
			try {
				const res = await api.unmuteUser({
					user_id: row.user,
					reason: value || undefined,
				});
				successMessage(res.msg || '解除禁言成功');
				crudExpose.doRefresh();
			} catch (error: any) {
				errorMessage('解除禁言失败：' + (error.message || '未知错误'));
			}
		})
		.catch(() => {});
};

/**
 * 修改时长
 */
const handleModifyDuration = (row: any) => {
	currentUserId.value = row.user;
	currentDuration.value = row.muted_until;
	durationDialogVisible.value = true;
};

/**
 * 查看详情
 */
const handleViewDetail = (row: any) => {
	currentUserId.value = row.user;
	logDrawerVisible.value = true;
};

/**
 * 导出
 */
const handleExport = () => {
	exportDialogVisible.value = true;
};

/**
 * 执行导出
 */
const executeExport = async () => {
	try {
		const params: any = {
			type: 'auto_mute',
			format: exportForm.value.format,
		};
		
		await api.exportData(params);
		successMessage('导出成功');
		exportDialogVisible.value = false;
	} catch (error: any) {
		errorMessage('导出失败：' + (error.message || '未知错误'));
	}
};

/**
 * 对话框成功回调
 */
const handleDialogSuccess = () => {
	crudExpose.doRefresh();
};

/**
 * 启动定时刷新（每分钟刷新一次倒计时）
 */
const startRefreshTimer = () => {
	refreshTimer = window.setInterval(() => {
		// 只刷新表格数据，不重新请求
		crudExpose.doRefresh();
	}, 60000); // 每60秒刷新一次
};

/**
 * 停止定时刷新
 */
const stopRefreshTimer = () => {
	if (refreshTimer) {
		clearInterval(refreshTimer);
		refreshTimer = null;
	}
};

// 页面打开后获取列表数据并启动定时刷新
onMounted(() => {
	crudExpose.doRefresh();
	startRefreshTimer();
});

// 页面关闭时停止定时刷新
onUnmounted(() => {
	stopRefreshTimer();
});
</script>

<style lang="scss" scoped>
.el-card {
	height: 100%;
}
</style>
