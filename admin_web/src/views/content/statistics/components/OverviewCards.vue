<template>
	<div class="overview-cards">
		<!-- 加载失败状态 -->
		<div v-if="error" class="overview-cards__error">
			<el-result icon="error" title="加载失败" sub-title="获取概览指标数据失败">
				<template #extra>
					<el-button type="primary" @click="$emit('retry')">重试</el-button>
				</template>
			</el-result>
		</div>

		<!-- 正常/加载状态 -->
		<el-row v-else :gutter="16">
			<el-col
				v-for="card in cardDefinitions"
				:key="card.field"
				:xl="4"
				:lg="4"
				:md="8"
				:sm="12"
				:xs="24"
			>
				<el-card class="overview-card" shadow="hover" :body-style="{ padding: '20px' }">
					<div v-if="loading" class="overview-card__loading">
						<el-skeleton :rows="1" animated />
					</div>
					<div v-else class="overview-card__content">
						<div class="overview-card__icon" :style="{ backgroundColor: card.bgColor }">
							<el-icon :size="28" :color="card.color">
								<component :is="card.icon" />
							</el-icon>
						</div>
						<div class="overview-card__info">
							<div class="overview-card__value">{{ getCardValue(card.field) }}</div>
							<div class="overview-card__title">{{ card.title }}</div>
						</div>
					</div>
				</el-card>
			</el-col>
		</el-row>
	</div>
</template>

<script setup lang="ts" name="OverviewCards">
/**
 * 概览指标卡片组件
 *
 * 展示6个指标卡片：知识库总数、人设卡总数、评论总数、收藏总数、上传总数、下载总数
 * 支持加载中、加载失败、数据为空等状态
 */
import { Document, User, ChatDotRound, Star, Upload, Download } from '@element-plus/icons-vue';
import type { StatisticsOverview } from '../api';
import type { Component } from 'vue';

/** 卡片定义接口 */
interface CardDefinition {
	field: keyof StatisticsOverview;
	title: string;
	icon: Component;
	color: string;
	bgColor: string;
}

const props = defineProps<{
	/** 概览指标数据，为 null 时显示 0 */
	data: StatisticsOverview | null;
	/** 是否正在加载 */
	loading: boolean;
	/** 是否加载失败 */
	error: boolean;
}>();

defineEmits<{
	/** 重试加载数据 */
	(e: 'retry'): void;
}>();

/** 6个指标卡片定义 */
const cardDefinitions: CardDefinition[] = [
	{
		field: 'knowledge_base_count',
		title: '知识库总数',
		icon: Document,
		color: '#409EFF',
		bgColor: 'rgba(64, 158, 255, 0.1)',
	},
	{
		field: 'persona_card_count',
		title: '人设卡总数',
		icon: User,
		color: '#67C23A',
		bgColor: 'rgba(103, 194, 58, 0.1)',
	},
	{
		field: 'comment_count',
		title: '评论总数',
		icon: ChatDotRound,
		color: '#E6A23C',
		bgColor: 'rgba(230, 162, 60, 0.1)',
	},
	{
		field: 'star_count',
		title: '收藏总数',
		icon: Star,
		color: '#F2C037',
		bgColor: 'rgba(242, 192, 55, 0.1)',
	},
	{
		field: 'upload_count',
		title: '上传总数',
		icon: Upload,
		color: '#9B59B6',
		bgColor: 'rgba(155, 89, 182, 0.1)',
	},
	{
		field: 'download_count',
		title: '下载总数',
		icon: Download,
		color: '#00BCD4',
		bgColor: 'rgba(0, 188, 212, 0.1)',
	},
];

/**
 * 获取卡片数值，数据为空时返回 0
 */
const getCardValue = (field: keyof StatisticsOverview): number => {
	if (!props.data) return 0;
	return props.data[field] ?? 0;
};
</script>

<style lang="scss" scoped>
.overview-cards {
	margin-bottom: 16px;

	&__error {
		padding: 20px;
		text-align: center;
	}
}

.overview-card {
	margin-bottom: 16px;

	&__loading {
		min-height: 60px;
		display: flex;
		align-items: center;
	}

	&__content {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	&__icon {
		width: 56px;
		height: 56px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	&__info {
		flex: 1;
		min-width: 0;
	}

	&__value {
		font-size: 28px;
		font-weight: 600;
		line-height: 1.2;
		color: #303133;
	}

	&__title {
		font-size: 14px;
		color: #909399;
		margin-top: 4px;
	}
}
</style>
