<template>
  <div class="register-container">
    <div class="register-form-wrapper">
      <h2>麦麦笔记本</h2>
      <h3>注册</h3>
      <el-form
        :model="registerForm"
        :rules="registerRules"
        ref="registerFormRef"
        label-position="left"
        label-width="90px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="registerForm.username"
            placeholder="请输入用户名"
            :prefix-icon="User"
          ></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="registerForm.confirm_password"
            type="password"
            placeholder="请再次输入密码"
            :prefix-icon="Lock"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱"
            :prefix-icon="Message"
          ></el-input>
        </el-form-item>
        <el-form-item>
          <div class="login-agreement">
            <el-checkbox v-model="registerForm.agreement" style="margin-right: 5px;">
              我已阅读并同意
            </el-checkbox>
            <a :href="systemConfig['login.privacy_url'] || '/api/system/clause/privacy.html'" target="_blank">《隐私政策》</a>
            和
            <a :href="systemConfig['login.clause_url'] || '/api/system/clause/terms_service.html'" target="_blank">《服务条款》</a>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleRegister" class="register-btn">注册</el-button>
          <el-link type="primary" @click="$router.push('/login')" class="login-link">去登录</el-link>
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { register, getSystemConfig } from '@/api/user'
import { showApiErrorNotification, showErrorNotification, showSuccessNotification } from '@/utils/api'

const router = useRouter()
const registerFormRef = ref()

const registerForm = reactive({
  username: '',
  password: '',
  email: '',
  confirm_password: '',
  agreement: false
})
const systemConfig = ref({})

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

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度在 6 到 30 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请再次输入密码'))
        } else if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: ['blur', 'change']
    }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请输入邮箱'))
        } else {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(value)) {
            callback(new Error('请输入有效的邮箱地址'))
          } else {
            callback()
          }
        }
      },
      trigger: ['blur', 'change']
    }
  ]
}

const handleRegister = async () => {
  if (!registerFormRef.value) return
  if (!registerForm.agreement) {
    showErrorNotification('请先阅读并同意隐私政策和服务条款')
    return
  }
  await registerFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const response = await register(
          registerForm.username,
          registerForm.password,
          registerForm.email
        )

        // 注意：后端返回结构可能不同，这里假设 response.data 包含 message
        // 根据 api/index.js 的 interceptor，如果 code=2000，则 success=true
        // 如果后端返回标准 DetailResponse，通常 code=2000
        
        // 由于后端 RegisterView 返回 DetailResponse(data={"message": ...})
        // 响应体结构: { code: 2000, msg: "success", data: { message: "..." } }
        // api interceptor 会把 success=true 加进去

        // 检查是否成功
        // 如果 interceptor 正常工作，response 应该是 data 部分 + success=true
        // 但如果 interceptor 返回 response.data，那么 response 就是 { code: 2000, msg: "...", data: {...}, success: true }
        
        if (response.success || response.code === 2000) {
            const msg = response.data?.message || response.msg || '注册邮件已发送，请查收邮箱完成验证'
            showSuccessNotification(msg)
            router.push('/login')
        } else {
            showErrorNotification(response.msg || '注册失败')
        }
      } catch (error) {
        console.error('注册错误:', error)
        showApiErrorNotification(error, '注册失败，请稍后重试')
      }
    } else {
      return false
    }
  })
}

onMounted(() => {
  fetchSystemConfig()
})
</script>

<style scoped>
.register-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--primary-color);
}

.register-form-wrapper {
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

.register-btn {
  width: 100%;
  margin-bottom: 10px;
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
}

.login-link {
  display: block;
  text-align: center;
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
