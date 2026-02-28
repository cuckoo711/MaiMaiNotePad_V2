<template>
	<div class="register-container flex z-10">
		<div class="register-left">
			<div class="register-left-logo">
				<img :src="logoMini" />
				<div class="register-left-logo-text">
					<span>{{ getThemeConfig.globalViceTitle }}</span>
				</div>
			</div>
		</div>
		<div class="register-right flex z-10">
			<div class="register-right-warp flex-margin">
				<div class="register-right-warp-main">
					<!-- 注册表单状态 -->
					<template v-if="!state.isSuccess">
						<div class="register-right-warp-main-title">
							<span>注册账号</span>
						</div>
						<div class="register-right-warp-main-form">
							<el-form
								ref="formRef"
								size="large"
								class="register-form"
								:model="state.form"
								:rules="rules"
								@keyup.enter="handleRegister"
							>
								<el-form-item class="register-animation1" prop="email">
									<el-input
										v-model="state.form.email"
										placeholder="请输入邮箱地址"
										clearable
										autocomplete="off"
									>
										<template #prefix>
											<el-icon class="el-input__icon"><ele-Message /></el-icon>
										</template>
									</el-input>
								</el-form-item>
								<el-form-item class="register-animation2" prop="username">
									<el-input
										v-model="state.form.username"
										placeholder="请输入用户名"
										clearable
										autocomplete="off"
									>
										<template #prefix>
											<el-icon class="el-input__icon"><ele-User /></el-icon>
										</template>
									</el-input>
								</el-form-item>
								<el-form-item class="register-animation3" prop="password">
									<el-input
										type="password"
										v-model="state.form.password"
										placeholder="请输入密码"
										show-password
									>
										<template #prefix>
											<el-icon class="el-input__icon"><ele-Lock /></el-icon>
										</template>
									</el-input>
								</el-form-item>
								<el-form-item class="register-animation4">
									<el-button
										type="primary"
										class="register-submit"
										round
										:loading="state.loading"
										@click="handleRegister"
									>
										注册
									</el-button>
								</el-form-item>
							</el-form>
							<div class="register-login-link register-animation4">
								<router-link to="/login">已有账号？去登录</router-link>
							</div>
						</div>
					</template>

					<!-- 注册成功提示状态 -->
					<template v-else>
						<div class="register-success">
							<el-result icon="success" title="验证邮件已发送" sub-title="请查收邮箱并点击验证链接完成注册">
								<template #extra>
									<el-button type="primary" round @click="goLogin">返回登录</el-button>
								</template>
							</el-result>
						</div>
					</template>
				</div>
			</div>
		</div>

		<div class="register-footer z-10">
			<p>MaiMaiNotePad</p>
		</div>
	</div>
	<div>
		<img :src="loginBg" class="register-bg fixed inset-0 z-1 w-full h-full" />
	</div>
</template>

<script setup lang="ts" name="registerIndex">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { register } from '/@/views/system/login/api';
import logoMini from '/@/assets/logo-mini.svg';
import loginBg from '/@/assets/login-bg.png';

const router = useRouter();
const storesThemeConfig = useThemeConfig();
const { themeConfig } = storeToRefs(storesThemeConfig);

// 获取布局配置信息
const getThemeConfig = computed(() => {
	return themeConfig.value;
});

// 表单引用
const formRef = ref<FormInstance>();

// 组件状态
const state = reactive({
	form: {
		email: '',
		username: '',
		password: '',
	},
	loading: false,
	isSuccess: false,
});

// 表单校验规则
const rules = reactive<FormRules>({
	email: [
		{ required: true, message: '请输入邮箱地址', trigger: 'blur' },
		{ type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
	],
	username: [
		{ required: true, message: '请输入用户名', trigger: 'blur' },
		{ min: 3, max: 30, message: '用户名长度需在 3-30 个字符之间', trigger: 'blur' },
	],
	password: [
		{ required: true, message: '请输入密码', trigger: 'blur' },
		{ min: 6, message: '密码长度至少为 6 个字符', trigger: 'blur' },
	],
});

// 提交注册
const handleRegister = async () => {
	if (!formRef.value) return;
	// 使用 promise 方式校验表单，避免 callback 模式下 await 无效的问题
	const valid = await formRef.value.validate().catch(() => false);
	if (!valid) return;
	state.loading = true;
	try {
		await register({
			email: state.form.email,
			username: state.form.username,
			password: state.form.password,
		});
		// 注册成功，切换到邮件已发送提示页
		state.isSuccess = true;
	} catch (err: any) {
		// 后端返回的错误信息已由 service.ts 拦截器通过 errorCreate 显示
		// 如果有额外的 msg 信息且拦截器未处理，手动显示
		if (err && err.msg && err.code !== 400) {
			ElMessage.error(err.msg);
		}
	} finally {
		state.loading = false;
	}
};

// 跳转登录页
const goLogin = () => {
	router.push('/login');
};
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

.register-container {
	height: 100%;
	background: var(--el-color-white);

	.register-left {
		flex: 1;
		position: relative;
		background-color: rgba(211, 239, 255, 1);
		margin-right: 100px;

		.register-left-logo {
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

			.register-left-logo-text {
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

	.register-right {
		width: 700px;

		.register-right-warp {
			border-radius: 3px;
			width: 500px;
			height: 500px;
			position: relative;
			overflow: hidden;

			.register-right-warp-main {
				display: flex;
				flex-direction: column;
				height: 100%;

				.register-right-warp-main-title {
					height: 100px;
					display: flex;
					align-items: center;
					justify-content: center;
					font-size: 24px;
					font-weight: 600;
					letter-spacing: 3px;
					animation: logoAnimation 0.3s ease;
					animation-delay: 0.1s;
					color: var(--el-text-color-primary);
				}

				.register-right-warp-main-form {
					flex: 1;
					padding: 0 50px 50px;

					.register-form {
						margin-top: 10px;

						:deep(.el-input__wrapper) {
							border-radius: 8px !important;
						}

						:deep(.el-input__inner) {
							font-size: 12px !important;
						}

						@for $i from 1 through 4 {
							.register-animation#{$i} {
								opacity: 0;
								animation-name: fadeInUp;
								animation-duration: 0.5s;
								animation-fill-mode: forwards;
								animation-delay: #{calc($i / 10)}s;
							}
						}

						.register-submit {
							width: 100%;
							letter-spacing: 2px;
							font-weight: 800;
							margin-top: 15px;
							border-radius: 8px;
						}
					}

					.register-login-link {
						text-align: center;
						margin-top: 15px;
						opacity: 0;
						animation-name: fadeInUp;
						animation-duration: 0.5s;
						animation-fill-mode: forwards;
						animation-delay: 0.4s;

						a {
							color: var(--el-color-primary);
							text-decoration: none;
							font-size: 14px;

							&:hover {
								text-decoration: underline;
							}
						}
					}
				}

				.register-success {
					display: flex;
					align-items: center;
					justify-content: center;
					height: 100%;
					animation: fadeInUp 0.5s ease;
				}
			}
		}
	}

	.register-footer {
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

.register-bg {
	object-fit: cover;
}
</style>
