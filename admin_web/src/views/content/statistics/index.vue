<template>
	<div class="statistics-container">
		<!-- 概览指标卡片 -->
		<section class="statistics-section">
			<OverviewCards
				:data="overviewData"
				:loading="overviewLoading"
				:error="overviewError"
				@retry="fetchOverview"
			/>
		</section>

		<!-- 审核状态分布饼图 -->
		<section class="statistics-section">
			<ReviewPieChart
				:data="reviewData"
				:loading="reviewLoading"
				:error="reviewError"
				@retry="fetchReviewDistribution"
			/>
		</section>

		<!-- 趋势折线图 -->
		<section class="statistics-section">
			<TrendLineChart
				:data="trendData"
				:loading="trendLoading"
				:error="trendError"
				@retry="fetchTrends"
				@range-change="handleRangeChange"
			/>
		</section>

		<!-- 热门内容排行榜 -->
		<section class="statistics-section">
			<TopContentTable
				:data="topContentData"
				:loading="topContentLoading"
				:error="topContentError"
				@retry="fetchTopContent"
				@sort-change="handleSortChange"
			/>
		</section>
	</div>
</template>

<script setup lang="ts" name="contentStatistics">
/**
 * 数据统计仪表盘主页面
 *
 * 组合 OverviewCards、ReviewPieChart、TrendLineChart、TopContentTable 四个子组件
 * 各组件独立加载，一个组件失败不影响其他组件
 * 页面加载时并行调用所有统计 API 获取数据
 */
import { ref, onMounted } from 'vue';
import { OverviewCards, ReviewPieChart, TrendLineChart, TopContentTable } from './components';
import { getOverview, getReviewDistribution, getTrends, getTopContent } from './api';
import type { StatisticsOverview, ReviewDistribution, TrendDataPoint, TopContentResponse } from './api';

// ==================== 概览指标状态 ====================
const overviewData = ref<StatisticsOverview | null>(null);
const overviewLoading = ref(true);
const overviewError = ref(false);

// ==================== 审核分布状态 ====================
const reviewData = ref<ReviewDistribution | null>(null);
const reviewLoading = ref(true);
const reviewError = ref(false);

// ==================== 趋势数据状态 ====================
const trendData = ref<TrendDataPoint[] | null>(null);
const trendLoading = ref(true);
const trendError = ref(false);

// ==================== 热门排行状态 ====================
const topContentData = ref<TopContentResponse | null>(null);
const topContentLoading = ref(true);
const topContentError = ref(false);

// ==================== 数据获取函数 ====================

/**
 * 获取概览指标数据
 */
async function fetchOverview(): Promise<void> {
	overviewLoading.value = true;
	overviewError.value = false;
	try {
		overviewData.value = await getOverview();
	} catch {
		overviewError.value = true;
	} finally {
		overviewLoading.value = false;
	}
}

/**
 * 获取审核状态分布数据
 */
async function fetchReviewDistribution(): Promise<void> {
	reviewLoading.value = true;
	reviewError.value = false;
	try {
		reviewData.value = await getReviewDistribution();
	} catch {
		reviewError.value = true;
	} finally {
		reviewLoading.value = false;
	}
}

/**
 * 获取趋势数据
 * @param days 时间范围（天数）
 */
async function fetchTrends(days?: number): Promise<void> {
	trendLoading.value = true;
	trendError.value = false;
	try {
		const response = await getTrends(days);
		trendData.value = response.data;
	} catch {
		trendError.value = true;
	} finally {
		trendLoading.value = false;
	}
}

/**
 * 获取热门内容排行数据
 * @param orderBy 排序方式
 */
async function fetchTopContent(orderBy?: string): Promise<void> {
	topContentLoading.value = true;
	topContentError.value = false;
	try {
		topContentData.value = await getTopContent(orderBy);
	} catch {
		topContentError.value = true;
	} finally {
		topContentLoading.value = false;
	}
}

// ==================== 事件处理 ====================

/**
 * 处理趋势图时间范围切换
 * @param days 新的时间范围（天数）
 */
function handleRangeChange(days: number): void {
	fetchTrends(days);
}

/**
 * 处理排行榜排序方式切换
 * @param orderBy 新的排序方式
 */
function handleSortChange(orderBy: string): void {
	fetchTopContent(orderBy);
}

// ==================== 页面初始化 ====================

onMounted(() => {
	// 并行调用所有统计 API，各组件独立加载
	fetchOverview();
	fetchReviewDistribution();
	fetchTrends();
	fetchTopContent();
});
</script>

<style lang="scss" scoped>
.statistics-container {
	padding: 16px;
}

.statistics-section {
	margin-bottom: 0;
}
</style>
