<template>
	<div class="persona-card-list">
		<!-- 页面头部 -->
		<div class="page-header">
			<div class="header-left">
				<h2>我的人设卡</h2>
				<p class="subtitle">管理您上传的所有人设卡</p>
			</div>
			<div class="header-right">
				<el-button type="primary" @click="handleUpload">
					<el-icon><Upload /></el-icon>
					上传新人设卡
				</el-button>
			</div>
		</div>

		<!-- 工具栏 -->
		<div class="toolbar">
			<!-- 排序选择 -->
			<el-select 
				v-model="sortOption" 
				placeholder="排序方式"
				style="width: 150px;"
				@change="handleSortChange"
			>
				<el-option label="最近编辑" value="-update_datetime" />
				<el-option label="最早编辑" value="update_datetime" />
				<el-option label="最新创建" value="-create_datetime" />
				<el-option label="最早创建" value="create_datetime" />
				<el-option label="下载最多" value="-downloads" />
				<el-option label="下载最少" value="downloads" />
			</el-select>

			<!-- 搜索栏 -->
			<el-input
				v-model="filterForm.keyword"
				placeholder="搜索人设卡名称"
				class="search-input"
				clearable
				@keyup.enter="handleSearch"
				@clear="handleSearch"
			>
				<template #prefix>
					<el-icon><Search /></el-icon>
				</template>
			</el-input>

			<!-- 公开状态筛选 -->
			<el-select 
				v-model="filterForm.is_public" 
				placeholder="公开状态" 
				clearable 
				style="width: 120px" 
				@change="handleSearch"
			>
				<el-option label="公开" :value="true" />
				<el-option label="私有" :value="false" />
			</el-select>

			<!-- 审核状态筛选 -->
			<el-select 
				v-model="filterForm.is_pending" 
				placeholder="审核状态" 
				clearable 
				style="width: 120px" 
				@change="handleSearch"
			>
				<el-option label="待审核" :value="true" />
				<el-option label="已审核" :value="false" />
			</el-select>

			<!-- 搜索按钮 -->
			<el-button type="primary" @click="handleSearch">
				<el-icon><Search /></el-icon>
				搜索
			</el-button>
		</div>

		<!-- 卡片列表 -->
		<div class="card-list" v-loading="loading">
			<div 
				v-for="card in tableData" 
				:key="card.id" 
				class="data-card"
			>
				<div class="card-header">
					<div class="card-title-area">
						<h4 class="card-title">{{ card.name }}</h4>
						<div class="card-meta">
							<span class="upload-time" v-if="card.update_datetime">
								<el-icon><Clock /></el-icon>
								编辑于 {{ formatRelativeTime(card.update_datetime) }}
							</span>
						</div>
					</div>
					<div class="card-actions-top" @click.stop>
						<el-dropdown trigger="click" @command="(cmd) => handleCardAction(cmd, card)">
							<el-button size="small" circle>
								<el-icon><MoreFilled /></el-icon>
							</el-button>
							<template #dropdown>
								<el-dropdown-menu>
									<el-dropdown-item v-if="canEdit(card)" command="edit">
										<el-icon><Edit /></el-icon>
										编辑
									</el-dropdown-item>
									<el-dropdown-item command="download">
										<el-icon><Download /></el-icon>
										下载
									</el-dropdown-item>
									<el-dropdown-item v-if="canTogglePublic(card)" command="toggle" divided>
										<el-icon><Switch /></el-icon>
										{{ card.is_public ? '转为私有' : '转为公开' }}
									</el-dropdown-item>
									<el-dropdown-item command="delete" divided>
										<el-icon><Delete /></el-icon>
										删除
									</el-dropdown-item>
								</el-dropdown-menu>
							</template>
						</el-dropdown>
					</div>
				</div>

				<div class="card-status-row">
					<el-tag v-if="card.is_public" type="success" size="small" effect="light">
						<span class="tag-content">
							<el-icon><View /></el-icon>
							<span>公开</span>
						</span>
					</el-tag>
					<el-tag v-else type="info" size="small" effect="light">
						<span class="tag-content">
							<el-icon><Lock /></el-icon>
							<span>私有</span>
						</span>
					</el-tag>
					<el-tag v-if="card.is_pending" type="warning" size="small" effect="light">
						<span class="tag-content">
							<el-icon><Clock /></el-icon>
							<span>待审核</span>
						</span>
					</el-tag>
					<el-tag v-else-if="card.is_public" type="success" size="small" effect="plain">
						<span class="tag-content">
							<el-icon><CircleCheck /></el-icon>
							<span>已通过</span>
						</span>
					</el-tag>
				</div>

				<div class="card-description" v-if="card.description">
					{{ card.description }}
				</div>

				<div class="card-meta-row" v-if="card.tags && parseCardTags(card.tags).length > 0">
					<div class="card-tags">
						<span v-for="tag in parseCardTags(card.tags).slice(0, 3)" :key="tag" class="tag">
							{{ tag }}
						</span>
						<span v-if="parseCardTags(card.tags).length > 3" class="tag-more">
							+{{ parseCardTags(card.tags).length - 3 }}
						</span>
					</div>
				</div>

				<div class="card-footer">
					<div class="card-stats">
						<span class="stat-item">
							<el-icon><Download /></el-icon>
							{{ card.downloads || 0 }}
						</span>
						<span class="stat-item" v-if="card.create_datetime">
							<el-icon><Calendar /></el-icon>
							创建于 {{ formatDate(card.create_datetime) }}
						</span>
					</div>
				</div>
			</div>

			<!-- 空状态 -->
			<div v-if="!loading && tableData.length === 0" class="empty-state">
				<el-empty description="暂无人设卡">
					<el-button type="primary" @click="handleUpload">上传第一个人设卡</el-button>
				</el-empty>
			</div>
		</div>

		<!-- 分页 -->
		<div class="pagination-container" v-if="pagination.total > pagination.pageSize">
			<el-pagination
				v-model:current-page="pagination.page"
				v-model:page-size="pagination.pageSize"
				:total="pagination.total"
				:page-sizes="[12, 24, 48, 96]"
				layout="total, sizes, prev, pager, next, jumper"
				@size-change="handleSizeChange"
				@current-change="handlePageChange"
			/>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import {
	Upload,
	Search,
	Edit,
	Delete,
	Download,
	Switch,
	Clock,
	CircleCheck,
	MoreFilled,
	View,
	Lock,
	Calendar,
} from '@element-plus/icons-vue';
import { getPersonaCardList, deletePersonaCard, togglePersonaCardPublic, downloadPersonaCard } from '../api';

/**
 * 我的人设卡列表页面（卡片式布局）
 * 
 * 功能：
 * - 实现我的人设卡列表页面（卡片式布局，类似 GitHub repositories）
 * - 显示信息：名称、描述、标签、状态、创建时间、下载次数
 * - 实现筛选功能（公开/私有、审核状态、关键词搜索）
 * - 实现排序功能（创建时间、下载次数）
 * - 实现操作按钮：编辑、切换公开/私有、删除、下载
 * - 显示审核状态标签（待审核、已通过）
 * 
 * 验证需求：12.1, 12.2, 11.5
 */

const router = useRouter();

// 加载状态
const loading = ref(false);

// 筛选表单
const filterForm = reactive({
	is_public: null as boolean | null,
	is_pending: null as boolean | null,
	keyword: '',
});

// 排序选项
const sortOption = ref('-update_datetime');

// 表格数据
const tableData = ref<any[]>([]);

// 分页
const pagination = reactive({
	page: 1,
	pageSize: 12,
	total: 0,
});

/**
 * 格式化相对时间
 */
const formatRelativeTime = (datetime: string) => {
	if (!datetime) return '-';
	const date = new Date(datetime);
	const now = new Date();
	const diff = now.getTime() - date.getTime();
	
	const seconds = Math.floor(diff / 1000);
	const minutes = Math.floor(seconds / 60);
	const hours = Math.floor(minutes / 60);
	const days = Math.floor(hours / 24);
	const months = Math.floor(days / 30);
	const years = Math.floor(days / 365);
	
	if (years > 0) return `${years} 年前`;
	if (months > 0) return `${months} 个月前`;
	if (days > 0) return `${days} 天前`;
	if (hours > 0) return `${hours} 小时前`;
	if (minutes > 0) return `${minutes} 分钟前`;
	return '刚刚';
};

/**
 * 格式化日期
 */
const formatDate = (dateString: string): string => {
	if (!dateString) return '';
	const date = new Date(dateString);
	const now = new Date();
	const diff = now.getTime() - date.getTime();
	const days = Math.floor(diff / (1000 * 60 * 60 * 24));
	
	if (days === 0) return '今天';
	if (days === 1) return '昨天';
	if (days < 7) return `${days}天前`;
	if (days < 30) return `${Math.floor(days / 7)}周前`;
	if (days < 365) return `${Math.floor(days / 30)}个月前`;
	return `${Math.floor(days / 365)}年前`;
};

/**
 * 解析标签数据
 * 支持数组格式和字符串格式（向后兼容）
 */
const parseCardTags = (tagsData: string | string[]) => {
	if (!tagsData) return [];
	// 如果已经是数组，直接返回
	if (Array.isArray(tagsData)) {
		return tagsData.filter((tag: string) => tag && tag.trim());
	}
	// 如果是字符串，按逗号分割（向后兼容）
	return tagsData.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
};

/**
 * 检查是否可以编辑
 * 只有私有状态的人设卡可以编辑
 */
const canEdit = (row: any) => {
	return !row.is_public && !row.is_pending;
};

/**
 * 检查是否可以切换公开/私有状态
 */
const canTogglePublic = (row: any) => {
	// 私有人设卡可以转为公开
	// 已通过审核的公开人设卡可以转为私有
	return !row.is_pending;
};

/**
 * 加载人设卡列表
 */
const loadPersonaCards = async () => {
	loading.value = true;
	try {
		const params: any = {
			page: pagination.page,
			page_size: pagination.pageSize,
		};

		// 添加筛选条件
		if (filterForm.is_public !== null) {
			params.is_public = filterForm.is_public;
		}
		if (filterForm.is_pending !== null) {
			params.is_pending = filterForm.is_pending;
		}
		if (filterForm.keyword) {
			params.keyword = filterForm.keyword;
		}

		// 添加排序条件
		if (sortOption.value) {
			params.ordering = sortOption.value;
		}

		const response = await getPersonaCardList(params);
		if (response.code === 2000) {
			// 后端返回的数据格式：{ code, msg, data: [...], total, page, limit }
			tableData.value = response.data || [];
			pagination.total = response.total || 0;
		} else {
			ElMessage.error(response.msg || '加载失败');
		}
	} catch (error) {
		console.error('加载人设卡列表失败:', error);
		ElMessage.error('加载失败，请稍后重试');
	} finally {
		loading.value = false;
	}
};

/**
 * 处理搜索
 */
const handleSearch = () => {
	pagination.page = 1;
	loadPersonaCards();
};

/**
 * 处理排序变化
 */
const handleSortChange = () => {
	pagination.page = 1;
	loadPersonaCards();
};

/**
 * 处理页码变化
 */
const handlePageChange = (page: number) => {
	pagination.page = page;
	loadPersonaCards();
};

/**
 * 处理每页数量变化
 */
const handleSizeChange = (size: number) => {
	pagination.pageSize = size;
	pagination.page = 1;
	loadPersonaCards();
};

/**
 * 处理上传
 */
const handleUpload = () => {
	router.push('/content/persona/upload');
};

/**
 * 处理卡片操作
 */
const handleCardAction = (command: string, card: any) => {
	switch (command) {
		case 'edit':
			handleEdit(card);
			break;
		case 'download':
			handleDownload(card);
			break;
		case 'toggle':
			handleTogglePublic(card);
			break;
		case 'delete':
			handleDelete(card);
			break;
	}
};

/**
 * 处理编辑
 */
const handleEdit = (row: any) => {
	router.push(`/content/persona/edit/${row.id}`);
};

/**
 * 处理切换公开/私有状态
 */
const handleTogglePublic = async (row: any) => {
	const action = row.is_public ? '转为私有' : '转为公开';
	const message = row.is_public
		? '转为私有后，其他用户将无法下载此人设卡。确定要继续吗？'
		: '转为公开后，人设卡将进入审核流程。审核通过后，其他用户可以下载使用。确定要继续吗？';

	try {
		await ElMessageBox.confirm(message, `确认${action}`, {
			confirmButtonText: '确定',
			cancelButtonText: '取消',
			type: 'warning',
		});

		loading.value = true;
		const response = await togglePersonaCardPublic(row.id);
		if (response.code === 2000) {
			ElMessage.success(`${action}成功`);
			loadPersonaCards();
		} else {
			ElMessage.error(response.msg || `${action}失败`);
		}
	} catch (error: any) {
		if (error !== 'cancel') {
			console.error('切换公开状态失败:', error);
			ElMessage.error('操作失败，请稍后重试');
		}
	} finally {
		loading.value = false;
	}
};

/**
 * 处理下载
 */
const handleDownload = async (row: any) => {
	try {
		loading.value = true;
		await downloadPersonaCard(row.id, row.name);
		ElMessage.success('下载成功');
	} catch (error) {
		console.error('下载失败:', error);
		ElMessage.error('下载失败，请稍后重试');
	} finally {
		loading.value = false;
	}
};

/**
 * 处理删除
 */
const handleDelete = async (row: any) => {
	try {
		await ElMessageBox.confirm(
			'删除后，人设卡将无法恢复。确定要删除吗？',
			'确认删除',
			{
				confirmButtonText: '确定',
				cancelButtonText: '取消',
				type: 'warning',
			}
		);

		loading.value = true;
		const response = await deletePersonaCard(row.id);
		if (response.code === 2000) {
			ElMessage.success('删除成功');
			loadPersonaCards();
		} else {
			ElMessage.error(response.msg || '删除失败');
		}
	} catch (error: any) {
		if (error !== 'cancel') {
			console.error('删除失败:', error);
			ElMessage.error('删除失败，请稍后重试');
		}
	} finally {
		loading.value = false;
	}
};

// 组件挂载时加载数据
onMounted(() => {
	loadPersonaCards();
});
</script>

<style scoped lang="scss">
.persona-card-list {
	padding: 20px;
	min-height: calc(100vh - 84px);
	background: #f5f5f5;

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 20px;
		background: white;
		padding: 20px;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

		.header-left {
			h2 {
				font-size: 24px;
				font-weight: 600;
				color: #333;
				margin: 0 0 6px 0;
			}

			.subtitle {
				font-size: 14px;
				color: #999;
				margin: 0;
			}
		}

		.header-right {
			.el-button {
				height: 36px;
				padding: 0 20px;
				font-size: 14px;
			}
		}
	}

	.toolbar {
		display: flex;
		gap: 12px;
		margin-bottom: 20px;
		align-items: center;
		background: white;
		padding: 16px;
		border-radius: 8px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

		.search-input {
			flex: 1;
			min-width: 200px;
		}
	}

	.card-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 20px;
		min-height: 400px;

		.data-card {
			background: white;
			border-radius: 8px;
			padding: 16px;
			cursor: pointer;
			transition: all 0.3s;
			box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
			display: flex;
			flex-direction: column;
			height: 200px;

			&:hover {
				transform: translateY(-4px);
				box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
			}

			.card-header {
				display: flex;
				align-items: flex-start;
				gap: 12px;
				margin-bottom: 8px;
				position: relative;

				.card-title-area {
					flex: 1;
					min-width: 0;

					.card-title {
						margin: 0 0 4px 0;
						font-size: 15px;
						font-weight: 600;
						overflow: hidden;
						text-overflow: ellipsis;
						white-space: nowrap;
						color: #333;
					}

					.card-meta {
						font-size: 12px;
						color: #999;
						display: flex;
						gap: 12px;
						align-items: center;

						.upload-time {
							display: flex;
							align-items: center;
							gap: 4px;

							.el-icon {
								font-size: 11px;
							}
						}
					}
				}

				.card-actions-top {
					position: absolute;
					top: -4px;
					right: -4px;
					z-index: 2;

					.el-button {
						padding: 5px;
						border-radius: 50%;
						width: 28px;
						height: 28px;
						display: flex;
						align-items: center;
						justify-content: center;

						.el-icon {
							font-size: 16px;
						}
					}
				}
			}

			.card-status-row {
				display: flex;
				gap: 6px;
				margin-bottom: 8px;
				flex-wrap: wrap;

				.el-tag {
					border-radius: 12px;
					font-size: 11px;
					padding: 3px 8px;

					.tag-content {
						display: inline-flex;
						align-items: center;
						gap: 4px;

						.el-icon {
							font-size: 12px;
						}
					}
				}
			}

			.card-description {
				font-size: 13px;
				color: #666;
				line-height: 1.5;
				margin-bottom: 8px;
				overflow: hidden;
				text-overflow: ellipsis;
				display: -webkit-box;
				-webkit-line-clamp: 2;
				-webkit-box-orient: vertical;
				flex: 1;
				min-height: 0;
			}

			.card-meta-row {
				display: flex;
				align-items: center;
				gap: 8px;
				margin-bottom: 8px;
				min-height: 24px;
				flex-wrap: wrap;

				.card-tags {
					display: flex;
					flex-wrap: wrap;
					gap: 6px;
					flex: 1;

					.tag {
						padding: 4px 12px;
						background: #f0f0f0;
						border-radius: 12px;
						font-size: 11px;
						color: #666;
					}

					.tag-more {
						padding: 4px 12px;
						background: #e0e0e0;
						border-radius: 12px;
						font-size: 11px;
						color: #999;
					}
				}
			}

			.card-footer {
				display: flex;
				justify-content: space-between;
				align-items: center;
				padding-top: 8px;
				border-top: 1px solid #f0f0f0;
				margin-top: auto;

				.card-stats {
					display: flex;
					gap: 15px;

					.stat-item {
						font-size: 12px;
						color: #999;
						display: flex;
						align-items: center;
						gap: 4px;

						.el-icon {
							font-size: 13px;
						}
					}
				}
			}
		}

		.empty-state {
			grid-column: 1 / -1;
			text-align: center;
			padding: 60px 20px;
			background: white;
			border-radius: 8px;
		}
	}

	.pagination-container {
		margin-top: 30px;
		display: flex;
		justify-content: center;
	}
}
</style>
