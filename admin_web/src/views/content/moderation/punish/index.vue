<template>
	<fs-page>
		<el-card>
			<fs-crud ref="crudRef" v-bind="crudBinding" @selection-change="handleSelectionChange">
				<!-- 自定义操作按钮 -->
				<template #actionbar-right>
					<!-- 已选中数量显示 -->
					<span v-if="hasSelection" style="margin-right: 12px; color: #409eff; font-size: 14px;">
						已选中 {{ selectedCount }} 条
					</span>
					<!-- 批量禁言 -->
					<el-button
						v-if="auth('punish:BatchMute')"
						type="warning"
						:disabled="!hasSelection"
						@click="handleBatchMute"
					>
						批量禁言
					</el-button>
					<!-- 批量封禁 -->
					<el-button
						v-if="auth('punish:BatchBan')"
						type="danger"
						:disabled="!hasSelection"
						@click="handleBatchBan"
					>
						批量封禁
					</el-button>
				</template>

				<!-- 自定义列显示 -->
				<template #cell_is_muted="scope">
					<el-tag v-if="scope.row.is_muted" type="warning" size="small">
						已禁言
					</el-tag>
					<el-tag v-else type="success" size="small">
						正常
					</el-tag>
				</template>

				<template #cell_is_active="scope">
					<el-tag v-if="!scope.row.is_active" type="danger" size="small">
						已封禁
					</el-tag>
					<el-tag v-else type="success" size="small">
						正常
					</el-tag>
				</template>

				<!-- 自定义行操作按钮 -->
				<template #row-handle="{ row }">
					<!-- 系统账号不显示任何操作按钮 -->
					<template v-if="row.user_type !== 2">
						<el-button
							v-if="auth('punish:Mute') && !row.is_muted"
							link
							size="small"
							type="warning"
							@click="handleMute(row)"
						>
							禁言
						</el-button>
						<el-button
							v-if="auth('punish:Ban') && row.is_active"
							link
							size="small"
							type="danger"
							@click="handleBan(row)"
						>
							封禁
						</el-button>
						<el-button
							v-if="auth('punish:Detail')"
							link
							size="small"
							@click="handleViewDetail(row)"
						>
							查看详情
						</el-button>
					</template>
					<template v-else>
						<el-tag type="info" size="small">系统账号</el-tag>
					</template>
				</template>
			</fs-crud>
		</el-card>

		<!-- 禁言对话框 -->
		<ModerationDialog
			v-model:visible="muteDialogVisible"
			:type="'mute'"
			:mode="'create'"
			:pre-selected-user="selectedUser"
			@success="handleDialogSuccess"
		/>

		<!-- 封禁对话框 -->
		<ModerationDialog
			v-model:visible="banDialogVisible"
			:type="'ban'"
			:mode="'create'"
			:pre-selected-user="selectedUser"
			@success="handleDialogSuccess"
		/>

		<!-- 批量禁言对话框 -->
		<BatchOperationDialog
			v-model:visible="batchMuteDialogVisible"
			:type="'mute'"
			:pre-selected-users="selectedRows"
			@success="handleDialogSuccess"
		/>

		<!-- 批量封禁对话框 -->
		<BatchOperationDialog
			v-model:visible="batchBanDialogVisible"
			:type="'ban'"
			:pre-selected-users="selectedRows"
			@success="handleDialogSuccess"
		/>

		<!-- 操作日志抽屉 -->
		<ModerationLogDrawer
			v-model:visible="logDrawerVisible"
			:user-id="currentUserId"
		/>
	</fs-page>
</template>

<script lang="ts" setup name="contentModerationPunish">
import { ref, onMounted } from 'vue';
import { useExpose, useCrud } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { auth } from '/@/utils/authFunction';
import { errorMessage } from '/@/utils/message';
import ModerationDialog from '../components/ModerationDialog.vue';
import BatchOperationDialog from '../components/BatchOperationDialog.vue';
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

// 选中的行
const selectedRows = ref<any[]>([]);
const selectedCount = ref(0);
const hasSelection = ref(false);

// 对话框状态
const muteDialogVisible = ref(false);
const banDialogVisible = ref(false);
const batchMuteDialogVisible = ref(false);
const batchBanDialogVisible = ref(false);
const logDrawerVisible = ref(false);

// 当前操作的用户
const selectedUser = ref<any>(null);
const currentUserId = ref(0);

/**
 * 处理选择变化
 */
const handleSelectionChange = (selection: any[]) => {
	selectedRows.value = selection;
	selectedCount.value = selection.length;
	hasSelection.value = selection.length > 0;
};

/**
 * 禁言单个用户
 */
const handleMute = (row: any) => {
	selectedUser.value = row;
	muteDialogVisible.value = true;
};

/**
 * 封禁单个用户
 */
const handleBan = (row: any) => {
	selectedUser.value = row;
	banDialogVisible.value = true;
};

/**
 * 批量禁言
 */
const handleBatchMute = () => {
	if (!hasSelection.value) {
		errorMessage('请先选择要禁言的用户');
		return;
	}
	if (selectedCount.value > 20) {
		errorMessage('批量操作最多支持20个用户');
		return;
	}
	batchMuteDialogVisible.value = true;
};

/**
 * 批量封禁
 */
const handleBatchBan = () => {
	if (!hasSelection.value) {
		errorMessage('请先选择要封禁的用户');
		return;
	}
	if (selectedCount.value > 20) {
		errorMessage('批量操作最多支持20个用户');
		return;
	}
	batchBanDialogVisible.value = true;
};

/**
 * 查看详情
 */
const handleViewDetail = (row: any) => {
	currentUserId.value = row.id;
	logDrawerVisible.value = true;
};

/**
 * 对话框成功回调
 */
const handleDialogSuccess = () => {
	crudExpose.doRefresh();
};

// 页面打开后获取列表数据
onMounted(() => {
	crudExpose.doRefresh();
});
</script>

<style lang="scss" scoped>
.el-card {
	height: 100%;
}
</style>
