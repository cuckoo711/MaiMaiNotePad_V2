<template>
	<div class="top-content-table">
		<!-- 加载失败状态 -->
		<div v-if="error" class="top-content-table__error">
			<el-result icon="error" title="加载失败" sub-title="获取热门内容排行数据失败">
				<template #extra>
					<el-button type="primary" @click="$emit('retry')">重试</el-button>
				</template>
			</el-result>
		</div>

		<!-- 正常/加载状态 -->
		<template v-else>
			<!-- 排序方式切换 -->
			<div class="top-content-table__sort">
				<el-radio-group v-model="currentOrderBy" size="small" @change="handleSortChange">
					<el-radio-button value="star_count">按收藏数排序</el-radio-button>
					<el-radio-button value="downloads">按下载次数排序</el-radio-button>
				</el-radio-group>
			</div>

			<!-- 两个排行榜并排展示 -->
			<el-row :gutter="16">
				<!-- 知识库热门排行 -->
				<el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<el-card shadow="hover">
						<template #header>
							<span class="top-content-table__title">知识库热门排行</span>
						</template>
						<div v-if="loading" class="top-content-table__loading">
							<el-skeleton :rows="6" animated />
						</div>
						<el-table
							v-else
							:data="knowledgeBaseList"
							stripe
							empty-text="暂无数据"
							style="width: 100%"
						>
							<el-table-column type="index" label="排名" width="60" align="center" />
							<el-table-column prop="name" label="内容名称" min-width="120" show-overflow-tooltip />
							<el-table-column prop="uploader_name" label="上传者" width="100" show-overflow-tooltip />
							<el-table-column prop="star_count" label="收藏数" width="80" align="center" />
							<el-table-column prop="downloads" label="下载次数" width="90" align="center" />
						</el-table>
					</el-card>
				</el-col>

				<!-- 人设卡热门排行 -->
				<el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
					<el-card shadow="hover">
						<template #header>
							<span class="top-content-table__title">人设卡热门排行</span>
						</template>
						<div v-if="loading" class="top-content-table__loading">
							<el-skeleton :rows="6" animated />
						</div>
						<el-table
							v-else
							:data="personaCardList"
							stripe
							empty-text="暂无数据"
							style="width: 100%"
						>
							<el-table-column type="index" label="排名" width="60" align="center" />
							<el-table-column prop="name" label="内容名称" min-width="120" show-overflow-tooltip />
							<el-table-column prop="uploader_name" label="上传者" width="100" show-overflow-tooltip />
							<el-table-column prop="star_count" label="收藏数" width="80" align="center" />
							<el-table-column prop="downloads" label="下载次数" width="90" align="center" />
						</el-table>
					</el-card>
				</el-col>
			</el-row>
		</template>
	</div>
</template>

<script setup lang="ts" name="TopContentTable">
/**
 * 热门内容排行榜组件
 *
 * 使用 el-table 分别展示知识库和人设卡的前10条热门记录
 * 支持"按收藏数排序"和"按下载次数排序"切换
 * 切换时通过 sort-change 事件通知父组件重新请求数据
 */
import { ref, computed } from 'vue';
import type { TopContentResponse } from '../api';

const props = defineProps<{
	/** 热门内容数据，为 null 时显示暂无数据 */
	data: TopContentResponse | null;
	/** 是否正在加载 */
	loading: boolean;
	/** 是否加载失败 */
	error: boolean;
}>();

const emit = defineEmits<{
	/** 重试加载数据 */
	(e: 'retry'): void;
	/** 排序方式切换 */
	(e: 'sort-change', orderBy: string): void;
}>();

/** 当前排序方式，默认按收藏数排序 */
const currentOrderBy = ref<string>('star_count');

/** 知识库排行数据，最多取前10条 */
const knowledgeBaseList = computed(() => {
	if (!props.data?.knowledge_base) return [];
	return props.data.knowledge_base.slice(0, 10);
});

/** 人设卡排行数据，最多取前10条 */
const personaCardList = computed(() => {
	if (!props.data?.persona_card) return [];
	return props.data.persona_card.slice(0, 10);
});

/**
 * 处理排序方式切换
 * @param orderBy 新的排序方式
 */
function handleSortChange(orderBy: string | number | boolean): void {
	emit('sort-change', String(orderBy));
}
</script>

<style lang="scss" scoped>
.top-content-table {
	margin-bottom: 16px;

	&__error {
		padding: 20px;
		text-align: center;
	}

	&__sort {
		margin-bottom: 16px;
	}

	&__title {
		font-size: 16px;
		font-weight: 600;
		color: #303133;
	}

	&__loading {
		min-height: 300px;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 20px;
	}

	// 小屏幕下第二个卡片增加上边距
	@media (max-width: 991px) {
		.el-col:last-child .el-card {
			margin-top: 16px;
		}
	}
}
</style>
