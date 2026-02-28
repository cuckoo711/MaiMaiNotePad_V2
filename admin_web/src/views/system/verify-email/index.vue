<template>
	<div class="verify-container flex z-10">
		<div class="verify-left">
			<div class="verify-left-logo">
				<img :src="logoMini" />
				<div class="verify-left-logo-text">
					<span>{{ getThemeConfig.globalViceTitle }}</span>
				</div>
			</div>
		</div>
		<div class="verify-right flex z-10">
			<div class="verify-right-warp flex-margin">
				<div class="verify-right-warp-main">
					<!-- 加载中状态 -->
					<div v-if="state.status === 'loading'" class="verify-status">
						<el-result icon="info" title="正在验证...">
							<template #extra>
								<el-icon class="is-loading" :size="32"><ele-Loading /></el-icon>
							</template>
						</el-result>
					</div>

					<!-- 验证成功状态 -->
					<div v-else-if="state.status === 'success'" class="verify-status">
						<el-result icon="success" title="验证成功" sub-title="正在跳转至首页..." />
					</div>

					<!-- 验证失败状态 -->
					<div v-else-if="state.status === 'error'" class="verify-status">
						<el-result icon="error" :title="state.errorTitle" :sub-title="state.errorSubTitle">
							<template #extra>
								<el-button type="primary" round @click="router.push(state.errorAction)">
									{{ state.errorBtnText }}
								</el-button>
							</template>
						</el-result>
					</div>
				</div>
			</div>
		</div>

		<div class="verify-footer z-10">
			<p>MaiMaiNotePad</p>
		</div>
	</div>
	<div>
		<img :src="loginBg" class="verify-bg fixed inset-0 z-1 w-full h-full" />
	</div>
</template>

<script setup lang="ts" name="verifyEmailIndex">
import { reactive, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Cookies from 'js-cookie';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { Session } from '/@/utils/storage';
import { initBackEndControlRoutes } from '/@/router/backEnd';
import { NextLoading } from '/@/utils/loading';
import { verifyEmail } from '/@/views/system/login/api';
import logoMini from '/@/assets/logo-mini.svg';
import loginBg from '/@/assets/login-bg.png';

const route = useRoute();
const router = useRouter();
const storesThemeConfig = useThemeConfig();
const { themeConfig } = storeToRefs(storesThemeConfig);

// 获取布局配置信息
const getThemeConfig = computed(() => {
	return themeConfig.value;
});

// 页面状态
const state = reactive({
	status: 'loading' as 'loading' | 'success' | 'error',
	errorTitle: '',
	errorSubTitle: '',
	errorBtnText: '',
	errorAction: '',
});

/**
 * 处理验证成功：存储 JWT 并跳转首页
 *
 * @param data 验证 API 返回的用户数据
 */
const handleSuccess = async (data: any) => {
	state.status = 'success';
	// 存储用户信息和令牌，与登录页保持一致
	Cookies.set('username', data.username);
	Session.set('token', data.access);
	// 初始化后端路由
	await initBackEndControlRoutes();
	// 添加 loading 并跳转首页
	NextLoading.start();
	router.push('/');
};

/**
 * 处理验证失败：根据原因展示不同的错误信息
 *
 * @param reason 失败原因（expired 或 conflict）
 */
const handleError = (reason: string) => {
	state.status = 'error';
	if (reason === 'conflict') {
		// 邮箱或用户名已被注册（并发场景）
		state.errorTitle = '该邮箱或用户名已被注册';
		state.errorSubTitle = '其他用户可能已抢先注册了相同的邮箱或用户名';
		state.errorBtnText = '返回登录';
		state.errorAction = '/login';
	} else {
		// 默认按过期处理（expired 或其他未知原因）
		state.errorTitle = '验证链接已过期或无效';
		state.errorSubTitle = '验证链接有效期为 24 小时，请重新注册';
		state.errorBtnText = '重新注册';
		state.errorAction = '/register';
	}
};

// 页面加载时自动调用验证 API
onMounted(async () => {
	const token = route.query.token as string;

	// 缺少 token 参数，直接显示过期错误
	if (!token) {
		handleError('expired');
		return;
	}

	try {
		const res: any = await verifyEmail(token);
		if (res.code === 2000) {
			await handleSuccess(res.data);
		} else {
			// API 返回非成功状态码
			const reason = res.data?.reason || 'expired';
			handleError(reason);
		}
	} catch (err: any) {
		// 请求异常，从错误响应中提取原因
		const reason = err?.data?.reason || 'expired';
		handleError(reason);
	}
});
</script>

<style scoped lang="scss">
// 入场动画关键帧
@keyframes fadeInUp {
	from {
		opacity: 0;
		transform: translateY(20px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

@keyframes logoAnimation {
	from {
		opacity: 0;
		transform: translateX(-20px);
	}
	to {
		opacity: 1;
		transform: translateX(0);
	}
}

.verify-container {
	height: 100%;
	background: var(--el-color-white);

	.verify-left {
		flex: 1;
		position: relative;
		background-color: rgba(211, 239, 255, 1);
		margin-right: 100px;

		.verify-left-logo {
			display: flex;
			align-items: center;
			position: absolute;
			top: 50px;
			left: 80px;
			z-index: 1;
			animation: logoAnimation 0.3s ease;

			img {
				width: 52px;
				height: 52px;
			}

			.verify-left-logo-text {
				display: flex;
				flex-direction: column;

				span {
					margin-left: 10px;
					font-size: 24px;
					color: var(--el-color-primary);
				}
			}
		}
	}

	.verify-right {
		width: 700px;

		.verify-right-warp {
			border-radius: 3px;
			width: 500px;
			height: 500px;
			position: relative;
			overflow: hidden;

			.verify-right-warp-main {
				display: flex;
				flex-direction: column;
				align-items: center;
				justify-content: center;
				height: 100%;

				.verify-status {
					animation: fadeInUp 0.5s ease;
					text-align: center;
				}
			}
		}
	}

	.verify-footer {
		position: absolute;
		bottom: 30px;
		left: 0;
		right: 0;
		text-align: center;

		p {
			font-size: 12px;
			color: rgba(0, 0, 0, 0.5);
		}
	}
}

.verify-bg {
	object-fit: cover;
}
</style>
