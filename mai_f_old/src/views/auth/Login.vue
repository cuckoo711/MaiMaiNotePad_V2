<template>
  <div class="login-container">
    <div class="login-form-wrapper">
      <h2>麦麦笔记本</h2>
      <h3>登录</h3>
      <el-form
        :model="loginForm"
        :rules="loginRules"
        ref="loginFormRef"
        label-position="left"
        label-width="90px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          ></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          ></el-input>
        </el-form-item>
        <el-form-item label="验证码" prop="captcha">
          <div class="captcha-row">
            <el-input
              v-model="loginForm.captcha"
              placeholder="请输入验证码"
              :prefix-icon="Key"
              @keyup.enter="handleLogin"
              style="flex: 1"
            ></el-input>
            <img 
              v-if="captchaImage" 
              :src="captchaImage" 
              class="captcha-img" 
              @click="fetchCaptcha" 
              title="点击刷新验证码"
            />
          </div>
        </el-form-item>
        <el-form-item>
          <div class="login-agreement">
            <el-checkbox v-model="loginForm.agreement" style="margin-right: 5px;">
              我已阅读并同意
            </el-checkbox>
            <a :href="systemConfig['login.privacy_url'] || '/api/system/clause/privacy.html'" target="_blank">《隐私政策》</a>
            和
            <a :href="systemConfig['login.clause_url'] || '/api/system/clause/terms_service.html'" target="_blank">《服务条款》</a>
          </div>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="loginForm.remember">记住用户名和密码</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" class="login-btn">登录</el-button>
          <div class="link-row">
            <el-link type="primary" @click="$router.push('/register')" class="link-item">去注册</el-link>
            <el-link type="primary" @click="$router.push('/reset-password')" class="link-item">忘记密码</el-link>
          </div>
        </el-form-item>
      </el-form>
      <div v-if="systemConfig['login.copyright']" class="copyright">
        {{ systemConfig['login.copyright'] }}
        <span v-if="systemConfig['login.keep_record']"> | {{ systemConfig['login.keep_record'] }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Key } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { login, getCaptcha, getSystemConfig } from '@/api/user'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification } from '@/utils/api'
import websocket from '@/utils/websocket'

const router = useRouter()
const loginFormRef = ref()
const loginForm = ref({
  username: '',
  password: '',
  captcha: '',
  captchaKey: '',
  remember: false,
  agreement: false
})
const systemConfig = ref({})

const captchaImage = ref('')

const fetchCaptcha = async () => {
  try {
    const response = await getCaptcha()
    if (response.code === 2000 && response.data) {
      captchaImage.value = response.data.image_base
      loginForm.value.captchaKey = response.data.key
      loginForm.value.captcha = ''
    }
  } catch (error) {
    console.error('Failed to fetch captcha:', error)
  }
}

const fetchSystemConfig = async () => {
  try {
    const response = await getSystemConfig()
    if (response.code === 2000 && response.data) {
      systemConfig.value = response.data
    }
  } catch (error) {
    console.error('Failed to fetch system config:', error)
  }
}

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ],
  captcha: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ]
}

const getRegisterInfo = () => {
  const query = router.currentRoute.value.query
  if (query.username && query.password) {
    loginForm.value.username = query.username
    loginForm.value.password = query.password
  }
}

const getRememberedInfo = () => {
  const remembered = localStorage.getItem('rememberedLogin')
  if (remembered) {
    const { username, password, remember } = JSON.parse(remembered)
    loginForm.value.username = username
    loginForm.value.password = password
    loginForm.value.remember = remember
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  if (!loginForm.value.agreement) {
    showErrorNotification('请先阅读并同意隐私政策和服务条款')
    return
  }
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const response = await login(
          loginForm.value.username,
          loginForm.value.password,
          loginForm.value.captcha,
          loginForm.value.captchaKey
        )

        if (response.success) {
          localStorage.setItem('access_token', response.data.access)
          localStorage.setItem('refresh_token', response.data.refresh)

          if (loginForm.value.remember) {
            localStorage.setItem('rememberedLogin', JSON.stringify({
              username: loginForm.value.username,
              password: loginForm.value.password,
              remember: true
            }))
          } else {
            localStorage.removeItem('rememberedLogin')
          }

          websocket.init()
          showSuccessNotification('登录成功')
          // 如果有 redirect 参数，跳转回用户原本想访问的页面
          const redirect = router.currentRoute.value.query.redirect || '/home'
          router.push(redirect)
        } else {
          showErrorNotification(response.msg || '登录失败')
          // 刷新验证码
          fetchCaptcha()
        }
      } catch (error) {
        showApiErrorNotification(error, '登录失败')
        // 刷新验证码
        fetchCaptcha()
      }
    }
  })
}

onMounted(() => {
  getRegisterInfo()
  getRememberedInfo()
  fetchCaptcha()
  fetchSystemConfig()
})
</script>

<style scoped>
.login-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--primary-color);
}

.login-form-wrapper {
  width: 520px;
  padding: 40px;
  background-color: var(--card-background);
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
}

h2 {
  color: var(--secondary-color);
  text-align: center;
  margin-bottom: 10px;
  font-size: 28px;
}

h3 {
  text-align: center;
  margin-bottom: 30px;
  font-size: 18px;
  color: var(--text-color);
}

.login-btn {
  width: 100%;
  margin-bottom: 10px;
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
}

.link-row {
  width: 100%;
  display: flex;
  justify-content: space-between;
}

.link-item {
  font-size: 14px;
}
  .captcha-row {
    display: flex;
    align-items: center;
    width: 100%;
    gap: 10px;
  }
  
  .captcha-img {
    height: 32px;
    cursor: pointer;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
  }

.login-agreement {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #606266;
  flex-wrap: wrap;
}

.login-agreement a {
  color: var(--el-color-primary);
  text-decoration: none;
  margin: 0 2px;
}

.login-agreement a:hover {
  text-decoration: underline;
}

.copyright {
  margin-top: 20px;
  text-align: center;
  font-size: 12px;
  color: #909399;
}
</style>
