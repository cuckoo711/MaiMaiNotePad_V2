<template>
	<div class="review-pie-chart">
		<!-- 加载失败状态 -->
		<div v-if="error" class="review-pie-chart__error">
			<el-result icon="error" title="加载失败" sub-title="获取审核状态分布数据失败">
				<template #extra>
					<el-button type="primary" @click="$emit('retry')">重试</el-button>
				</template>
			</el-result>
		</div>

		<!-- 正常/加载状态 -->
		<el-row v-else :gutter="16">
			<el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
				<el-card shadow="hover">
					<template #header>
						<span class="review-pie-chart__title">知识库审核状态分布</span>
					</template>
					<div v-if="loading" class="review-pie-chart__loading">
						<el-skeleton :rows="6" animated />
					</div>
					<div v-else-if="isKnowledgeBaseEmpty" class="review-pie-chart__empty">
						<el-empty description="暂无数据" :image-size="100" />
					</div>
					<div v-else ref="knowledgeBaseChartRef" class="review-pie-chart__canvas" />
				</el-card>
			</el-col>
			<el-col :xs="24" :sm="24" :md="12" :lg="12" :xl="12">
				<el-card shadow="hover">
					<template #header>
						<span class="review-pie-chart__title">人设卡审核状态分布</span>
					</template>
					<div v-if="loading" class="review-pie-chart__loading">
						<el-skeleton :rows="6" animated />
					</div>
					<div v-else-if="isPersonaCardEmpty" class="review-pie-chart__empty">
						<el-empty description="暂无数据" :image-size="100" />
					</div>
					<div v-else ref="personaCardChartRef" class="review-pie-chart__canvas" />
				</el-card>
			</el-col>
		</el-row>
	</div>
</template>

<script setup lang="ts" name="ReviewPieChart">
/**
 * 审核状态分布饼图组件
 *
 * 使用 ECharts 饼图分别展示知识库和人设卡的审核状态分布
 * 颜色方案：待审核 #E6A23C、已通过 #67C23A、已拒绝 #F56C6C
 * 支持加载中、加载失败、数据为空等状态
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts/core';
import { PieChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { ReviewDistribution } from '../api';

// 注册 ECharts 组件
echarts.use([PieChart, TitleComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

/** 审核状态颜色方案 */
const STATUS_COLORS = {
	pending: '#E6A23C',
	approved: '#67C23A',
	rejected: '#F56C6C',
};

/** 审核状态中文名称 */
const STATUS_LABELS: Record<string, string> = {
	pending: '待审核',
	approved: '已通过',
	rejected: '已拒绝',
};

const props = defineProps<{
	/** 审核状态分布数据，为 null 时显示暂无数据 */
	data: ReviewDistribution | null;
	/** 是否正在加载 */
	loading: boolean;
	/** 是否加载失败 */
	error: boolean;
}>();

defineEmits<{
	/** 重试加载数据 */
	(e: 'retry'): void;
}>();

// 图表 DOM 引用
const knowledgeBaseChartRef = ref<HTMLElement | null>(null);
const personaCardChartRef = ref<HTMLElement | null>(null);

// ECharts 实例
let knowledgeBaseChart: echarts.ECharts | null = null;
let personaCardChart: echarts.ECharts | null = null;

/** 判断知识库数据是否为空 */
const isKnowledgeBaseEmpty = computed(() => {
	if (!props.data) return true;
	const { pending, approved, rejected } = props.data.knowledge_base;
	return pending + approved + rejected === 0;
});

/** 判断人设卡数据是否为空 */
const isPersonaCardEmpty = computed(() => {
	if (!props.data) return true;
	const { pending, approved, rejected } = props.data.persona_card;
	return pending + approved + rejected === 0;
});

/**
 * 构建饼图配置项
 * @param statusData 审核状态数据
 */
function buildChartOption(statusData: { pending: number; approved: number; rejected: number }): echarts.EChartsOption {
	const seriesData = [
		{ value: statusData.pending, name: STATUS_LABELS.pending },
		{ value: statusData.approved, name: STATUS_LABELS.approved },
		{ value: statusData.rejected, name: STATUS_LABELS.rejected },
	];

	return {
		tooltip: {
			trigger: 'item',
			formatter: (params: any) => {
				const { name, value, percent } = params;
				return `${name}：${value} 条（${percent}%）`;
			},
		},
		legend: {
			bottom: '0',
			left: 'center',
			data: [STATUS_LABELS.pending, STATUS_LABELS.approved, STATUS_LABELS.rejected],
		},
		color: [STATUS_COLORS.pending, STATUS_COLORS.approved, STATUS_COLORS.rejected],
		series: [
			{
				type: 'pie',
				radius: ['40%', '70%'],
				center: ['50%', '45%'],
				avoidLabelOverlap: true,
				itemStyle: {
					borderRadius: 6,
					borderColor: '#fff',
					borderWidth: 2,
				},
				label: {
					show: true,
					formatter: '{b}: {d}%',
				},
				emphasis: {
					label: {
						show: true,
						fontSize: 14,
						fontWeight: 'bold',
					},
				},
				data: seriesData,
			},
		],
	};
}

/** 初始化或更新图表 */
function updateCharts(): void {
	if (!props.data) return;

	// 知识库饼图
	if (!isKnowledgeBaseEmpty.value && knowledgeBaseChartRef.value) {
		if (!knowledgeBaseChart) {
			knowledgeBaseChart = echarts.init(knowledgeBaseChartRef.value);
		}
		knowledgeBaseChart.setOption(buildChartOption(props.data.knowledge_base));
	}

	// 人设卡饼图
	if (!isPersonaCardEmpty.value && personaCardChartRef.value) {
		if (!personaCardChart) {
			personaCardChart = echarts.init(personaCardChartRef.value);
		}
		personaCardChart.setOption(buildChartOption(props.data.persona_card));
	}
}

/** 处理窗口大小变化 */
function handleResize(): void {
	knowledgeBaseChart?.resize();
	personaCardChart?.resize();
}

/** 销毁图表实例 */
function disposeCharts(): void {
	if (knowledgeBaseChart) {
		knowledgeBaseChart.dispose();
		knowledgeBaseChart = null;
	}
	if (personaCardChart) {
		personaCardChart.dispose();
		personaCardChart = null;
	}
}

// 监听数据变化，更新图表
watch(
	() => props.data,
	() => {
		// 数据变化时先销毁旧图表，等 DOM 更新后重新初始化
		disposeCharts();
		nextTick(() => {
			updateCharts();
		});
	},
	{ deep: true }
);

// 监听 loading 状态变化，加载完成后初始化图表
watch(
	() => props.loading,
	(newVal, oldVal) => {
		if (oldVal && !newVal) {
			nextTick(() => {
				updateCharts();
			});
		}
	}
);

onMounted(() => {
	window.addEventListener('resize', handleResize);
	nextTick(() => {
		updateCharts();
	});
});

onUnmounted(() => {
	window.removeEventListener('resize', handleResize);
	disposeCharts();
});
</script>

<style lang="scss" scoped>
.review-pie-chart {
	margin-bottom: 16px;

	&__error {
		padding: 20px;
		text-align: center;
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

	&__empty {
		min-height: 300px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	&__canvas {
		width: 100%;
		height: 300px;
	}

	// 小屏幕下第二个卡片增加上边距
	@media (max-width: 991px) {
		.el-col:last-child .el-card {
			margin-top: 16px;
		}
	}
}
</style>
