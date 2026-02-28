<template>
  <div class="verify-container">
    <div class="verify-wrapper">
      <h2>麦麦笔记本</h2>
      <div v-if="loading" class="status-box">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>正在验证邮箱...</p>
      </div>
      <div v-else-if="success" class="status-box success">
        <el-icon><CircleCheckFilled /></el-icon>
        <p>邮箱验证成功！</p>
        <p class="sub-text">{{ countdown }}秒后跳转至登录页...</p>
        <el-button type="primary" @click="$router.push('/login')">立即登录</el-button>
      </div>
      <div v-else class="status-box error">
        <el-icon><CircleCloseFilled /></el-icon>
        <p>验证失败</p>
        <p class="error-msg">{{ errorMessage }}</p>
        <el-button type="primary" @click="$router.push('/login')">返回登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { verifyEmail } from '@/api/user'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const success = ref(false)
const errorMessage = ref('')
const countdown = ref(3)

onMounted(async () => {
  const token = route.query.token
  
  if (!token) {
    loading.value = false
    errorMessage.value = '无效的验证链接'
    return
  }

  try {
    const response = await verifyEmail(token)
    // 根据 api/index.js 的 interceptor，response.success 应该是 true
    if (response.success || response.code === 2000) {
      success.value = true
      loading.value = false
      startCountdown()
    } else {
      throw new Error(response.msg || '验证失败')
    }
  } catch (error) {
    loading.value = false
    errorMessage.value = error.message || '验证链接无效或已过期'
  }
})

const startCountdown = () => {
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      router.push('/login')
    }
  }, 1000)
}
</script>

<style scoped>
.verify-container {
  width: 100%;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--primary-color);
}

.verify-wrapper {
  width: 400px;
  padding: 40px;
  background-color: var(--card-background);
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
  text-align: center;
}

h2 {
  color: var(--secondary-color);
  margin-bottom: 30px;
  font-size: 28px;
}

.status-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.el-icon {
  font-size: 48px;
}

.is-loading {
  color: var(--text-color);
}

.success .el-icon {
  color: var(--success-color, #67c23a);
}

.error .el-icon {
  color: var(--error-color, #f56c6c);
}

p {
  font-size: 18px;
  color: var(--text-color);
}

.sub-text {
  font-size: 14px;
  color: var(--text-secondary-color, #909399);
  margin-bottom: 10px;
}

.error-msg {
  font-size: 14px;
  color: var(--error-color, #f56c6c);
  margin-bottom: 10px;
}
</style>
