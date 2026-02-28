<template>
	<div class="trend-line-chart">
		<!-- 加载失败状态 -->
		<div v-if="error" class="trend-line-chart__error">
			<el-result icon="error" title="加载失败" sub-title="获取趋势数据失败">
				<template #extra>
					<el-button type="primary" @click="$emit('retry')">重试</el-button>
				</template>
			</el-result>
		</div>

		<!-- 正常/加载状态 -->
		<el-card v-else shadow="hover">
			<template #header>
				<div class="trend-line-chart__header">
					<span class="trend-line-chart__title">每日新增趋势</span>
					<el-radio-group v-model="selectedDays" size="small" @change="handleRangeChange">
						<el-radio-button :value="7">最近7天</el-radio-button>
						<el-radio-button :value="30">最近30天</el-radio-button>
						<el-radio-button :value="90">最近90天</el-radio-button>
					</el-radio-group>
				</div>
			</template>
			<div v-if="loading" class="trend-line-chart__loading">
				<el-skeleton :rows="6" animated />
			</div>
			<div v-else ref="chartRef" class="trend-line-chart__canvas" />
		</el-card>
	</div>
</template>

<script setup lang="ts" name="TrendLineChart">
/**
 * 趋势折线图组件
 *
 * 使用 ECharts 折线图展示每日新增数据趋势
 * 三条折线分别代表知识库、人设卡、评论，使用不同颜色区分
 * 支持时间范围切换（7天/30天/90天）
 */
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { TrendDataPoint } from '../api';

// 注册 ECharts 组件
echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

/** 折线颜色方案 */
const LINE_COLORS = {
	knowledge_base: '#409EFF',
	persona_card: '#67C23A',
	comment: '#E6A23C',
};

/** 折线中文名称 */
const LINE_LABELS: Record<string, string> = {
	knowledge_base: '知识库',
	persona_card: '人设卡',
	comment: '评论',
};

const props = defineProps<{
	/** 趋势数据点数组，为 null 时显示空图表 */
	data: TrendDataPoint[] | null;
	/** 是否正在加载 */
	loading: boolean;
	/** 是否加载失败 */
	error: boolean;
}>();

const emit = defineEmits<{
	/** 重试加载数据 */
	(e: 'retry'): void;
	/** 时间范围切换 */
	(e: 'range-change', days: number): void;
}>();

// 当前选中的时间范围（天数），默认30天
const selectedDays = ref<number>(30);

// 图表 DOM 引用
const chartRef = ref<HTMLElement | null>(null);

// ECharts 实例
let chartInstance: echarts.ECharts | null = null;

/**
 * 构建折线图配置项
 * @param trendData 趋势数据点数组
 */
function buildChartOption(trendData: TrendDataPoint[]): echarts.EChartsOption {
	const dates = trendData.map((item) => item.date);
	const knowledgeBaseData = trendData.map((item) => item.knowledge_base_count);
	const personaCardData = trendData.map((item) => item.persona_card_count);
	const commentData = trendData.map((item) => item.comment_count);

	return {
		tooltip: {
			trigger: 'axis',
			axisPointer: {
				type: 'cross',
			},
		},
		legend: {
			bottom: '0',
			left: 'center',
			data: [LINE_LABELS.knowledge_base, LINE_LABELS.persona_card, LINE_LABELS.comment],
		},
		grid: {
			left: '3%',
			right: '4%',
			bottom: '40px',
			top: '10px',
			containLabel: true,
		},
		xAxis: {
			type: 'category',
			boundaryGap: false,
			data: dates,
		},
		yAxis: {
			type: 'value',
			minInterval: 1,
		},
		series: [
			{
				name: LINE_LABELS.knowledge_base,
				type: 'line',
				smooth: true,
				data: knowledgeBaseData,
				itemStyle: { color: LINE_COLORS.knowledge_base },
				lineStyle: { color: LINE_COLORS.knowledge_base },
			},
			{
				name: LINE_LABELS.persona_card,
				type: 'line',
				smooth: true,
				data: personaCardData,
				itemStyle: { color: LINE_COLORS.persona_card },
				lineStyle: { color: LINE_COLORS.persona_card },
			},
			{
				name: LINE_LABELS.comment,
				type: 'line',
				smooth: true,
				data: commentData,
				itemStyle: { color: LINE_COLORS.comment },
				lineStyle: { color: LINE_COLORS.comment },
			},
		],
	};
}

/** 初始化或更新图表 */
function updateChart(): void {
	if (!chartRef.value) return;

	if (!chartInstance) {
		chartInstance = echarts.init(chartRef.value);
	}

	// 数据为空或 null 时显示空图表（仅坐标轴）
	const trendData = props.data ?? [];
	chartInstance.setOption(buildChartOption(trendData), true);
}

/** 处理时间范围切换 */
function handleRangeChange(days: number): void {
	emit('range-change', days);
}

/** 处理窗口大小变化 */
function handleResize(): void {
	chartInstance?.resize();
}

/** 销毁图表实例 */
function disposeChart(): void {
	if (chartInstance) {
		chartInstance.dispose();
		chartInstance = null;
	}
}

// 监听数据变化，更新图表
watch(
	() => props.data,
	() => {
		nextTick(() => {
			updateChart();
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
				updateChart();
			});
		}
	}
);

onMounted(() => {
	window.addEventListener('resize', handleResize);
	nextTick(() => {
		updateChart();
	});
});

onUnmounted(() => {
	window.removeEventListener('resize', handleResize);
	disposeChart();
});
</script>

<style lang="scss" scoped>
.trend-line-chart {
	margin-bottom: 16px;

	&__error {
		padding: 20px;
		text-align: center;
	}

	&__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 8px;
	}

	&__title {
		font-size: 16px;
		font-weight: 600;
		color: #303133;
	}

	&__loading {
		min-height: 350px;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 20px;
	}

	&__canvas {
		width: 100%;
		height: 350px;
	}
}
</style>
