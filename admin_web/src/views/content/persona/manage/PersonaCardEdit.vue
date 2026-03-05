<template>
	<div class="persona-card-edit">
		<!-- 页面头部 -->
		<div class="page-header">
			<div class="header-left">
				<el-button text @click="handleBack">
					<el-icon><ArrowLeft /></el-icon>
					返回列表
				</el-button>
			</div>
			<div class="header-center">
				<h2>编辑人设卡</h2>
				<p class="subtitle">{{ personaCard?.name || '加载中...' }}</p>
			</div>
			<div class="header-right">
				<el-button type="primary" :loading="saving" @click="handleSave">
					<el-icon><Check /></el-icon>
					保存修改
				</el-button>
			</div>
		</div>

		<!-- 权限提示 -->
		<el-alert
			v-if="!canEdit"
			type="warning"
			:closable="false"
			show-icon
			style="margin-bottom: 20px"
		>
			<template #title>
				<span>此人设卡当前状态不允许编辑</span>
			</template>
			<template #default>
				<p style="margin: 0">
					只有私有状态的人设卡可以编辑。正在审核或已通过审核的公开人设卡无法编辑。
					如需修改，请先将人设卡转为私有状态。
				</p>
			</template>
		</el-alert>

		<!-- 加载状态 -->
		<div v-if="loading" v-loading="loading" class="loading-container">
			<p>加载中...</p>
		</div>

		<!-- 编辑内容 -->
		<div v-else-if="personaCard" class="edit-content">
			<!-- 基本信息 -->
			<el-card class="info-card" shadow="never">
				<template #header>
					<div class="card-header">
						<span>基本信息</span>
						<el-tag v-if="personaCard.is_public" type="success" size="small">公开</el-tag>
						<el-tag v-else type="info" size="small">私有</el-tag>
					</div>
				</template>
				<el-form :model="basicInfo" label-width="120px" :disabled="!canEdit">
					<el-form-item label="人设卡名称">
						<el-input v-model="basicInfo.name" placeholder="请输入人设卡名称（1-200 字符）" />
					</el-form-item>
					<el-form-item label="描述">
						<el-input
							v-model="basicInfo.description"
							type="textarea"
							:rows="4"
							placeholder="请输入人设卡描述（至少 10 字符）"
						/>
					</el-form-item>
					<el-form-item label="版权所有者">
						<el-input v-model="basicInfo.copyright_owner" placeholder="默认为上传者用户名" />
					</el-form-item>
					<el-form-item label="标签">
						<TagInput v-model="basicInfo.tags" :disabled="!canEdit" />
					</el-form-item>
				</el-form>
			</el-card>

			<!-- 配置编辑器 -->
			<el-card class="config-card" shadow="never">
				<template #header>
					<div class="card-header">
						<span>配置编辑</span>
						<el-tag type="info" size="small">{{ configSections.length }} 个配置块</el-tag>
					</div>
				</template>
				<div class="config-editor-wrapper">
					<ConfigEditor
						v-model:sections="configSections"
						:sensitive-info="sensitiveInfo"
						:readonly="!canEdit"
						@update:sections="handleConfigChange"
					/>
				</div>
			</el-card>
		</div>

		<!-- 错误状态 -->
		<el-empty v-else description="加载失败或人设卡不存在">
			<el-button type="primary" @click="handleBack">返回列表</el-button>
		</el-empty>
	</div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { ArrowLeft, Check } from '@element-plus/icons-vue';
import ConfigEditor from '../upload/ConfigEditor.vue';
import TagInput from '/@/components/TagInput.vue';
import { getPersonaCardDetail, getPersonaCardConfig, updatePersonaCardBasicInfo, updatePersonaCardConfig } from '../api';
import type { ConfigSection } from '/@/stores/personaUpload';

/**
 * 人设卡编辑页面
 * 
 * 功能：
 * - 实现人设卡编辑页面
 * - 复用 ConfigEditor 组件
 * - 实现权限检查（只能编辑私有状态的人设卡）
 * - 实现保存修改功能
 * 
 * 验证需求：12.3, 12.4, 7.3
 */

const route = useRoute();
const router = useRouter();

// 人设卡 ID
const personaCardId = ref<string>(route.params.id as string);

// 加载状态
const loading = ref(false);
const saving = ref(false);

// 人设卡数据
const personaCard = ref<any>(null);

// 基本信息
const basicInfo = reactive({
	name: '',
	description: '',
	copyright_owner: '',
	tags: [] as string[] | string,
});

// 配置块数据
const configSections = ref<ConfigSection[]>([]);

// 敏感信息数据
const sensitiveInfo = ref<any[]>([]);

/**
 * 是否可以编辑
 * 只有私有状态且未在审核中的人设卡可以编辑
 */
const canEdit = computed(() => {
	if (!personaCard.value) return false;
	return !personaCard.value.is_public && !personaCard.value.is_pending;
});

/**
 * 加载人设卡详情
 */
const loadPersonaCard = async () => {
	loading.value = true;
	try {
		// 加载基本信息
		const detailResponse = await getPersonaCardDetail(personaCardId.value);
		if (detailResponse.code === 2000) {
			personaCard.value = detailResponse.data;
			basicInfo.name = personaCard.value.name;
			basicInfo.description = personaCard.value.description;
			basicInfo.copyright_owner = personaCard.value.copyright_owner || '';
			// 支持数组和字符串格式
			basicInfo.tags = personaCard.value.tags || [];
		} else {
			ElMessage.error(detailResponse.msg || '加载人设卡详情失败');
			loading.value = false;
			return;
		}

		// 加载配置数据
		const configResponse = await getPersonaCardConfig(personaCardId.value);
		if (configResponse.code === 2000) {
			configSections.value = configResponse.data.sections || [];
			// 保存敏感信息数据
			sensitiveInfo.value = configResponse.data.sensitive_info || [];
			// 调试日志
			console.log('加载配置数据成功:', {
				sections: configSections.value.length,
				sensitiveInfo: sensitiveInfo.value.length,
				sensitiveInfoDetail: sensitiveInfo.value
			});
		} else {
			ElMessage.error(configResponse.msg || '加载配置数据失败');
		}
	} catch (error: any) {
		console.error('加载人设卡失败:', error);
		ElMessage.error(error?.message || '加载失败，请稍后重试');
	} finally {
		loading.value = false;
	}
};

/**
 * 处理配置变化
 */
const handleConfigChange = (sections: ConfigSection[]) => {
	configSections.value = sections;
};

/**
 * 验证基本信息
 */
const validateBasicInfo = (): boolean => {
	if (!basicInfo.name || basicInfo.name.length < 1 || basicInfo.name.length > 200) {
		ElMessage.error('人设卡名称长度必须在 1-200 字符之间');
		return false;
	}

	if (!basicInfo.description || basicInfo.description.length < 10) {
		ElMessage.error('人设卡描述至少需要 10 个字符');
		return false;
	}

	return true;
};

/**
 * 处理保存
 */
const handleSave = async () => {
	if (!canEdit.value) {
		ElMessage.warning('当前状态不允许编辑');
		return;
	}

	// 验证基本信息
	if (!validateBasicInfo()) {
		return;
	}

	try {
		await ElMessageBox.confirm(
			'确定要保存修改吗？',
			'确认保存',
			{
				confirmButtonText: '确定',
				cancelButtonText: '取消',
				type: 'info',
			}
		);

		saving.value = true;

		// 1. 更新基本信息
		const basicInfoData = {
			name: basicInfo.name,
			description: basicInfo.description,
			copyright_owner: basicInfo.copyright_owner || undefined,
			// 确保 tags 以数组格式发送，如果为空则发送空数组
			tags: Array.isArray(basicInfo.tags) 
				? (basicInfo.tags.length > 0 ? basicInfo.tags : undefined)
				: (basicInfo.tags ? basicInfo.tags : undefined),
		};

		const basicInfoResponse = await updatePersonaCardBasicInfo(personaCardId.value, basicInfoData);
		if (basicInfoResponse.code !== 2000) {
			ElMessage.error(basicInfoResponse.msg || '保存基本信息失败');
			saving.value = false;
			return;
		}

		// 2. 更新配置项（如果有配置项的话）
		if (configSections.value.length > 0) {
			const configData = {
				updates: configSections.value,
				deleted_sections: [],
			};

			const configResponse = await updatePersonaCardConfig(personaCardId.value, configData);
			if (configResponse.code !== 2000) {
				ElMessage.error(configResponse.msg || '保存配置失败');
				saving.value = false;
				return;
			}
		}

		ElMessage.success('保存成功');
		// 重新加载数据
		await loadPersonaCard();
	} catch (error: any) {
		if (error !== 'cancel') {
			console.error('保存失败:', error);
			ElMessage.error('保存失败，请稍后重试');
		}
	} finally {
		saving.value = false;
	}
};

/**
 * 处理返回
 */
const handleBack = () => {
	router.push('/content/persona/manage');
};

// 组件挂载时加载数据
onMounted(() => {
	if (!personaCardId.value) {
		ElMessage.error('缺少人设卡 ID');
		handleBack();
		return;
	}
	loadPersonaCard();
});
</script>

<style scoped lang="scss">
.persona-card-edit {
	padding: 20px;

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 20px;
		padding-bottom: 20px;
		border-bottom: 1px solid var(--el-border-color-lighter);

		.header-left {
			flex: 0 0 auto;
		}

		.header-center {
			flex: 1;
			text-align: center;

			h2 {
				font-size: 24px;
				font-weight: 600;
				color: var(--el-text-color-primary);
				margin: 0 0 8px 0;
			}

			.subtitle {
				font-size: 14px;
				color: var(--el-text-color-secondary);
				margin: 0;
			}
		}

		.header-right {
			flex: 0 0 auto;
		}
	}

	.loading-container {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 400px;
		font-size: 16px;
		color: var(--el-text-color-secondary);
	}

	.edit-content {
		.info-card,
		.config-card {
			margin-bottom: 20px;

			.card-header {
				display: flex;
				align-items: center;
				gap: 10px;
				font-size: 16px;
				font-weight: 600;
			}
		}

		.config-card {
			.config-editor-wrapper {
				:deep(.config-editor) {
					.editor-header {
						display: none; // 隐藏编辑器自带的头部
					}

					.editor-actions {
						display: none; // 隐藏编辑器自带的操作按钮
					}
				}
			}
		}
	}
}
</style>
