<template>
  <div class="reset-container">
    <div class="reset-form-wrapper">
      <h2>麦麦笔记本</h2>
      <h3>重置密码</h3>
      <el-form
        :model="resetForm"
        :rules="resetRules"
        ref="resetFormRef"
        label-position="left"
        label-width="90px"
      >
        <el-form-item label="邮箱" prop="email">
          <div class="email-input-wrapper">
            <el-input
              v-model="resetForm.emailLocal"
              placeholder="请输入邮箱"
              :prefix-icon="Message"
              style="flex: 1"
            ></el-input>
            <span class="email-suffix">.com</span>
          </div>
        </el-form-item>
        <el-form-item label="验证码" prop="verification_code">
          <div class="code-input-wrapper">
            <el-input
              v-model="resetForm.verification_code"
              placeholder="请输入验证码"
              :prefix-icon="CircleCheck"
              style="width: 65%"
            ></el-input>
            <el-button
              type="primary"
              @click="handleSendCode"
              :disabled="countdown > 0"
              style="width: 30%; margin-left: 5%"
            >
              {{ countdown > 0 ? `${countdown}s后重试` : '发送验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="resetForm.new_password"
            type="password"
            placeholder="请输入新密码"
            :prefix-icon="Lock"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="resetForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            :prefix-icon="Lock"
            show-password
          ></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleReset" class="reset-btn">重置密码</el-button>
          <el-link type="primary" @click="$router.push('/login')" class="login-link">返回登录</el-link>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { Message, CircleCheck, Lock } from '@element-plus/icons-vue'
import { sendResetPasswordCode, resetPassword } from '@/api/user'
import { handleApiError, showApiErrorNotification, showErrorNotification, showSuccessNotification, showWarningNotification } from '@/utils/api'

const router = useRouter()
const resetFormRef = ref()
const countdown = ref(0)
let countdownTimer = null

const resetForm = reactive({
  email: '',
  emailLocal: '',
  verification_code: '',
  new_password: '',
  confirm_password: ''
})

const resetRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        const fullEmail = resetForm.emailLocal + '.com'
        if (!fullEmail) {
          callback(new Error('请输入邮箱'))
        } else {
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(fullEmail)) {
            callback(new Error('请输入有效的邮箱地址'))
          } else {
            callback()
          }
        }
      },
      trigger: ['blur', 'change']
    }
  ],
  verification_code: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 30, message: '密码长度在 6 到 30 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('请再次输入新密码'))
        } else if (value !== resetForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: ['blur', 'change']
    }
  ]
}

const handleSendCode = async () => {
  if (!resetForm.emailLocal) {
    showWarningNotification('请先输入邮箱')
    return
  }

  const fullEmail = resetForm.emailLocal + '.com'
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(fullEmail)) {
    showWarningNotification('请输入有效的邮箱地址')
    return
  }

  try {
    const response = await sendResetPasswordCode(fullEmail)
    if (response.success) {
      showSuccessNotification('验证码发送成功')
      countdown.value = 60
      countdownTimer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) {
          clearInterval(countdownTimer)
        }
      }, 1000)
    } else {
      showErrorNotification(response.message || '验证码发送失败')
    }
  } catch (error) {
    showApiErrorNotification(error, '验证码发送失败，请检查网络连接')
  }
}

const handleReset = async () => {
  if (!resetFormRef.value) return
  await resetFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const fullEmail = resetForm.emailLocal + '.com'
        const response = await resetPassword(
          fullEmail,
          resetForm.verification_code,
          resetForm.new_password
        )
        if (response.success) {
          showSuccessNotification('密码重置成功，请使用新密码登录')
          router.push('/login')
        } else {
          showErrorNotification(response.message || '密码重置失败')
        }
      } catch (error) {
        showApiErrorNotification(error, '密码重置失败，请检查网络连接')
      }
    } else {
      return false
    }
  })
}
</script>

<style scoped>
.reset-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--primary-color);
}

.reset-form-wrapper {
  width: 450px;
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

.code-input-wrapper {
  display: flex;
  align-items: center;
}

.email-input-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
}

.email-suffix {
  margin-left: 10px;
  padding: 0 12px;
  height: 32px;
  line-height: 32px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--card-background);
  color: var(--text-color);
  font-size: 14px;
  box-sizing: border-box;
}

.reset-btn {
  width: 100%;
  margin-bottom: 10px;
  background-color: var(--secondary-color);
  border-color: var(--secondary-color);
}

.login-link {
  display: block;
  text-align: center;
}
</style>
