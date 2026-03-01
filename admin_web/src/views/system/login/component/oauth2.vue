<template>
	<div class="other-fast-way" v-if="backends.length">
		<div class="fast-title"><span>其他快速方式登录</span></div>
		<div class="login-agreement">
			<el-checkbox v-model="agreement" style="margin-right: 5px;">
				我已阅读并同意
			</el-checkbox>
			<a :href="getSystemConfig['login.privacy_url'] || '/api/system/clause/privacy.html'" target="_blank">《隐私政策》</a>
			和
			<a :href="getSystemConfig['login.clause_url'] || '/api/system/clause/terms_service.html'" target="_blank">《服务条款》</a>
		</div>
		<ul class="fast-list">
			<li v-for="(v, k) in backends" :key="v.app_name">
				<a @click.once="handleOAuth2LoginClick(v)" style="width: 50px;color: #18bc9c">
					<img :src="v.icon" :alt="v.app_name" />
										<p>{{ v.app_name }}</p>

				</a>
			</li>
		</ul>
	</div>
</template>

<script lang="ts">
import { defineComponent, onMounted, reactive, toRefs, computed } from 'vue';
import { ElMessage } from 'element-plus';
import * as loginApi from '../api';
import { OAuth2Backend } from '/@/views/system/login/types';
import { storeToRefs } from 'pinia';
import { SystemConfigStore } from '/@/stores/systemConfig';

export default defineComponent({
	name: 'loginOAuth2',
	setup() {
		const systemConfigStore = SystemConfigStore();
		const { systemConfig } = storeToRefs(systemConfigStore);
		const getSystemConfig = computed(() => {
			return systemConfig.value;
		});

		const state = reactive({
			agreement: false,
			backends: [] as OAuth2Backend[],
		});

		const handleOAuth2LoginClick = (backend: OAuth2Backend) => {
			if (!state.agreement) {
				ElMessage.warning('请先阅读并同意隐私政策和服务条款');
				return;
			}
			history.replaceState(null, '', location.pathname + location.search);
			window.location.href = backend.authentication_url + '?next=' + window.location.href;
		};

		const getBackends = async () => {
			loginApi.getBackends().then((ret: any) => {				
				state.backends = ret.data;
			});
		};
		// const handleTreeClick = (record: MenuTreeItemType) => {
		//   menuButtonRef.value?.handleRefreshTable(record);
		//   menuFieldRef.value?.handleRefreshTable(record)
		// };

		onMounted(() => {
			// getBackends();
		});
		return {
			handleOAuth2LoginClick,
			getSystemConfig,
			...toRefs(state),
		};
	},
});
</script>

<style scoped lang="scss">
.login-agreement {
	width: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 12px;
	color: #606266;
	margin-bottom: 10px;

	a {
		color: var(--el-color-primary);
		text-decoration: none;
		margin: 0 2px;

		&:hover {
			text-decoration: underline;
		}
	}
}

.login-content-form {
	margin-top: 20px;
	@for $i from 1 through 4 {
		.login-animation#{$i} {
			opacity: 0;
			animation-name: error-num;
			animation-duration: 0.5s;
			animation-fill-mode: forwards;
			animation-delay: #{calc($i / 10)}s;
		}
	}

	.login-content-code {
		width: 100%;
		padding: 0;
	}

	.login-content-submit {
		width: 100%;
		letter-spacing: 2px;
		font-weight: 300;
		margin-top: 15px;
	}

	.login-msg {
		color: var(--el-text-color-placeholder);
	}
}
.other-fast-way {
	//height: 240px;
	position: relative;

	z-index: 1;
	//display: flex;
	//align-items: center;
	//justify-content: center;
	.fast-title {
		display: flex;
		align-items: center;
		justify-content: center;

		span {
			color: #999;
			font-size: 14px;
			padding: 0 20px;
		}
		&:before,
		&:after {
			content: '';
			flex: 1;
			height: 1px;
			background: #ddd;
		}
	}
}
.fast-list {
	display: flex;
	justify-content: center;
	margin-top: 10px;
	li {
		margin-left: 20px;
		opacity: 0;
		animation-name: error-num;
		animation-duration: 0.5s;
		animation-fill-mode: forwards;
		animation-delay: 0.1s;
		a {
			display: block;
			text-align: center;
			cursor: pointer;
			img {
				width: 35px;
				margin: 0 auto;
				max-width: 100%;
				margin-bottom: 6px;
			}
			p {
				font-size: 14px;
				color: #333;
			}
		}
		&:first-child {
			margin-left: 0;
		}
	}
}
</style>
