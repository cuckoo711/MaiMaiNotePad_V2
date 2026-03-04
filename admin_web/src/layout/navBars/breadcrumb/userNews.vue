<template>
	<div class="layout-navbars-breadcrumb-user-news">
		<div class="head-box">
			<el-tabs v-model="activeTab" class="news-tabs">
				<el-tab-pane label="通知" name="notification"></el-tab-pane>
				<el-tab-pane label="评论" name="comment"></el-tab-pane>
				<el-tab-pane label="回复" name="reply"></el-tab-pane>
			</el-tabs>
		</div>
		<div class="content-box">
			<template v-if="state.newsList.length > 0">
				<div class="content-box-item" v-for="(v, k) in state.newsList" :key="k" @click="onMessageClick(v)">
					<!-- 未读红点 -->
					<div v-if="!v.is_read" class="unread-dot"></div>
					
					<div class="content-box-title">
						<el-tag :type="getMessageTypeTag(v.message_type)" size="small">
							{{ getMessageTypeLabel(v.message_type) }}
						</el-tag>
						{{ v.title }}
					</div>
					<div class="content-box-msg">
						<div v-html="v.content"></div>
					</div>
					<div class="content-box-time">{{ v.create_datetime }}</div>
				</div>
			</template>
			<el-empty :description="$t('message.user.newDesc')" v-else></el-empty>
		</div>
		<div class="foot-box" @click="onGoToGiteeClick">{{ $t('message.user.newGo') }}</div>
		
		<!-- 消息详情弹窗 -->
		<MessageDetailDialog
			v-model="dialogVisible"
			:message="currentMessage"
			@read="handleMessageRead"
		/>
	</div>
</template>

<script setup lang="ts" name="layoutBreadcrumbUserNews">
import { reactive, onMounted, ref, watch } from 'vue';
import MessageDetailDialog from '/@/components/MessageDetailDialog.vue';

// 定义变量内容
const state = reactive({
	newsList: [] as any,
});

const activeTab = ref('notification');
const dialogVisible = ref(false);
const currentMessage = ref<any>(null);

// 消息类型标签映射
const getMessageTypeLabel = (type: number) => {
	const labels: Record<number, string> = {
		0: '系统',
		1: '评论',
		2: '回复',
		3: '点赞',
		4: '审核',
	};
	return labels[type] || '未知';
};

// 获取消息类型标签颜色（与消息页面保持一致）
const getMessageTypeTag = (type: number) => {
	const tagMap: Record<number, string> = {
		0: '',
		1: 'success',
		2: 'primary',
		3: 'warning',
		4: 'info'
	};
	return tagMap[type] || '';
};

// 监听标签切换
watch(activeTab, () => {
	state.newsList = [];
	getLastMsg();
});

// 前往通知中心点击
import { useRouter } from 'vue-router';
const route = useRouter();
const onGoToGiteeClick = () => {
	route.push('/user/messages');
};

// 点击消息项，打开详情弹窗
const onMessageClick = (message: any) => {
	currentMessage.value = message;
	dialogVisible.value = true;
};

// 消息已读回调
const handleMessageRead = (message: any) => {
	// 更新本地状态
	const index = state.newsList.findIndex((m: any) => m.id === message.id);
	if (index !== -1) {
		state.newsList[index].is_read = true;
	}
};

//获取最新消息
import { request } from '/@/utils/service';
const getLastMsg = () => {
	const params: any = {
		limit: 5, // 获取最新5条
	};
	
	// 根据标签页添加消息类型筛选
	if (activeTab.value === 'notification') {
		// 通知：系统通知(0) 和 审核(4)
		params.message_type = '0,4';
	} else if (activeTab.value === 'comment') {
		// 评论：评论(1)
		params.message_type = '1';
	} else if (activeTab.value === 'reply') {
		// 回复：回复(2) 和 点赞(3)
		params.message_type = '2,3';
	}
	
	console.log('获取消息，参数:', params);
	
	request({
		url: '/api/system/message_center/get_self_receive/',
		method: 'get',
		params: params,
	}).then((res: any) => {
		console.log('消息弹窗 API 响应:', res);
		
		// 后端返回格式：{ code: 2000, data: [...], total: 10 }
		if (res && res.data) {
			state.newsList = Array.isArray(res.data) ? res.data : [];
		} else {
			state.newsList = [];
		}
		
		console.log('解析后的消息列表:', state.newsList);
	}).catch((error) => {
		console.error('获取消息失败:', error);
		state.newsList = [];
	});
};

onMounted(() => {
	getLastMsg();
});
</script>

<style scoped lang="scss">
.layout-navbars-breadcrumb-user-news {
	.head-box {
		border-bottom: 1px solid var(--el-border-color-lighter);
		
		.news-tabs {
			:deep(.el-tabs__header) {
				margin: 0;
				padding: 0 10px;
			}
			
			:deep(.el-tabs__nav-wrap::after) {
				display: none;
			}
			
			:deep(.el-tabs__item) {
				padding: 0 15px;
				height: 35px;
				line-height: 35px;
				font-size: 13px;
			}
		}
	}
	
	.content-box {
		font-size: 13px;
		max-height: 400px;
		overflow-y: auto;
		
		.content-box-item {
			position: relative;
			padding: 12px;
			padding-left: 20px;
			border-bottom: 1px solid var(--el-border-color-lighter);
			cursor: pointer;
			transition: background-color 0.2s;
			
			&:hover {
				background-color: var(--el-fill-color-light);
			}
			
			&:last-of-type {
				border-bottom: none;
			}
			
			.unread-dot {
				position: absolute;
				left: 6px;
				top: 18px;
				width: 6px;
				height: 6px;
				background: var(--el-color-danger);
				border-radius: 50%;
			}
			
			.content-box-title {
				display: flex;
				align-items: center;
				gap: 8px;
				font-weight: 500;
				color: var(--el-text-color-primary);
				margin-bottom: 4px;
			}
			
			.content-box-msg {
				color: var(--el-text-color-secondary);
				margin-top: 5px;
				margin-bottom: 5px;
				line-height: 1.5;
				
				:deep(p) {
					margin: 0;
				}
			}
			
			.content-box-time {
				color: var(--el-text-color-placeholder);
				font-size: 12px;
			}
		}
	}
	
	.foot-box {
		height: 35px;
		color: var(--el-color-primary);
		font-size: 13px;
		cursor: pointer;
		opacity: 0.8;
		display: flex;
		align-items: center;
		justify-content: center;
		border-top: 1px solid var(--el-border-color-lighter);
		&:hover {
			opacity: 1;
		}
	}
	
	:deep(.el-empty__description p) {
		font-size: 13px;
	}
}
</style>
