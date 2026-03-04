<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding">
			<template #header-middle>
				<el-tabs v-model="tabActivted" @tab-click="onTabClick">
					<el-tab-pane label="我的发布" name="send"></el-tab-pane>
					<el-tab-pane label="我的接收" name="receive">
						<template #label>
							<el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
								我的接收
							</el-badge>
						</template>
					</el-tab-pane>
				</el-tabs>
				<!-- 接收消息的二级标签 -->
				<el-tabs v-if="tabActivted === 'receive'" v-model="receiveTabActivted" @tab-click="onReceiveTabClick" class="receive-tabs">
					<el-tab-pane label="全部" name="all"></el-tab-pane>
					<el-tab-pane label="通知" name="notification"></el-tab-pane>
					<el-tab-pane label="评论" name="comment"></el-tab-pane>
					<el-tab-pane label="回复" name="reply"></el-tab-pane>
				</el-tabs>
			</template>
		</fs-crud>
	</fs-page>
</template>

<script lang="ts" setup name="messageCenter">
import { ref, onMounted, computed } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import createCrudOptions from './crud';
import { messageCenterStore } from '/@/stores/messageCenter';

const messageStore = messageCenterStore();

//tab选择
const tabActivted = ref('send');
const receiveTabActivted = ref('all');

const onTabClick = (tab: any) => {
	const { paneName } = tab;
	tabActivted.value = paneName;
	if (paneName === 'receive') {
		receiveTabActivted.value = 'all';
	}
	crudExpose.doRefresh();
};

const onReceiveTabClick = (tab: any) => {
	const { paneName } = tab;
	receiveTabActivted.value = paneName;
	crudExpose.doRefresh();
};

const unreadCount = computed(() => messageStore.unread);

const context: any = { tabActivted, receiveTabActivted }; //将 tabActivted 和 receiveTabActivted 通过context传递给crud.tsx
// 初始化crud配置
const { crudRef, crudBinding, crudExpose } = useFs({ createCrudOptions, context });

// 页面打开后获取列表数据
onMounted(() => {
	crudExpose.doRefresh();
});
</script>

<style scoped lang="scss">
.receive-tabs {
	margin-top: -10px;
	margin-left: 20px;
	
	:deep(.el-tabs__header) {
		margin-bottom: 10px;
	}
	
	:deep(.el-tabs__nav-wrap::after) {
		display: none;
	}
}
</style>
