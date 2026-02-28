<template>
	<!-- 注册表单 -->
	<template v-if="!state.isSuccess">
		<el-form ref="formRef" size="large" class="login-content-form" :model="state.form" :rules="rules" @keyup.enter="handleRegister">
			<el-form-item class="login-animation1" prop="email">
				<el-input v-model="state.form.email" placeholder="请输入邮箱地址" clearable autocomplete="off">
					<template #prefix>
						<el-icon class="el-input__icon"><ele-Message /></el-icon>
					</template>
				</el-input>
			</el-form-item>
			<el-form-item class="login-animation2" prop="username">
				<el-input v-model="state.form.username" placeholder="请输入用户名" clearable autocomplete="off">
					<template #prefix>
						<el-icon class="el-input__icon"><ele-User /></el-icon>
					</template>
				</el-input>
			</el-form-item>
			<el-form-item class="login-animation3" prop="password">
				<el-input type="password" v-model="state.form.password" placeholder="请输入密码" show-password>
					<template #prefix>
						<el-icon class="el-input__icon"><ele-Lock /></el-icon>
					</template>
				</el-input>
			</el-form-item>
			<el-form-item class="login-animation4">
				<el-button type="primary" class="login-content-submit" round :loading="state.loading" @click="handleRegister">
					注册
				</el-button>
			</el-form-item>
		</el-form>
	</template>

	<!-- 注册成功提示 -->
	<template v-else>
		<div class="register-success">
			<el-result icon="success" title="验证邮件已发送" sub-title="请查收邮箱并点击验证链接完成注册">
				<template #extra>
					<el-button type="primary" round @click="resetForm">返回登录</el-button>
				</template>
			</el-result>
		</div>
	</template>
</template>

<script setup lang="ts" name="loginRegister">
import { reactive, ref } from 'vue';
import type { FormInstance, FormRules } from 'element-plus';
import { ElMessage } from 'element-plus';
import { register } from '/@/views/system/login/api';

const emit = defineEmits(['switchToLogin']);

const formRef = ref<FormInstance>();

const state = reactive({
	form: {
		email: '',
		username: '',
		password: '',
	},
	loading: false,
	isSuccess: false,
});

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
	const valid = await formRef.value.validate().catch(() => false);
	if (!valid) return;
	state.loading = true;
	try {
		await register({
			email: state.form.email,
			username: state.form.username,
			password: state.form.password,
		});
		state.isSuccess = true;
	} catch (err: any) {
		if (err && err.msg && err.code !== 400) {
			ElMessage.error(err.msg);
		}
	} finally {
		state.loading = false;
	}
};

// 重置表单并切回登录 tab
const resetForm = () => {
	state.isSuccess = false;
	state.form = { email: '', username: '', password: '' };
	emit('switchToLogin');
};
</script>

<style scoped lang="scss">
@keyframes error-num {
	from {
		opacity: 0;
		transform: translateY(20px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

.login-content-form {
	margin-top: 20px;

	:deep(.el-input__wrapper) {
		border-radius: 8px !important;
	}
	:deep(.el-input__inner) {
		font-size: 12px !important;
	}

	@for $i from 1 through 4 {
		.login-animation#{$i} {
			opacity: 0;
			animation-name: error-num;
			animation-duration: 0.5s;
			animation-fill-mode: forwards;
			animation-delay: #{calc($i / 10)}s;
		}
	}

	.login-content-submit {
		width: 100%;
		letter-spacing: 2px;
		font-weight: 800;
		margin-top: 15px;
		border-radius: 8px;
	}
}

.register-success {
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 20px 0;
	animation: error-num 0.5s ease;
}
</style>
