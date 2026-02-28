import { DEFAULT_API_PORT } from '@/api'

const getWsBaseUrl = () => {
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (envBase && typeof envBase === 'string' && envBase.startsWith('http')) {
    const url = new URL(envBase)
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${url.host}/`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://'
  const host = window.location.hostname
  const port = DEFAULT_API_PORT
  return `${protocol}${host}:${port}/`
}

let statusListeners = []

const notifyStatus = (status) => {
  if (!statusListeners.length) {
    return
  }
  statusListeners.forEach((listener) => {
    if (typeof listener === 'function') {
      try {
        listener(status)
      } catch (e) {}
    }
  })
}

const websocket = {
  websocket: null,
  connectUrl: '',
  socketOpen: false,
  heartbeatTimer: null,
  heartbeatInterval: 20000,
  isReconnect: true,
  reconnectCount: 0,
  reconnectMaxCount: 10,
  reconnectTimer: null,
  reconnectBaseInterval: 3000,
  reconnectMaxInterval: 60000,
  messageHandler: null,
  init(receiveMessage) {
    if (typeof receiveMessage === 'function') {
      this.messageHandler = receiveMessage
    }
    if (typeof window === 'undefined' || !('WebSocket' in window)) {
      this.socketOpen = false
      notifyStatus('closed')
      return
    }
    const token = localStorage.getItem('access_token')
    if (!token) {
      this.socketOpen = false
      notifyStatus('closed')
      return
    }
    if (this.websocket && this.socketOpen) {
      notifyStatus('open')
      return
    }
    // 添加末尾斜杠以匹配后端路由 path('ws/<str:service_uid>/', ...)
    const wsUrl = `${getWsBaseUrl()}ws/${token}/`
    this.connectUrl = wsUrl
    const ws = new WebSocket(wsUrl)
    this.websocket = ws

    ws.onopen = () => {
      this.socketOpen = true
      this.isReconnect = true
      // 连接成功，重置重连计数
      this.reconnectCount = 0
      this.heartbeat()
      notifyStatus('open')
    }

    ws.onmessage = (event) => {
      notifyStatus('message')
      if (this.messageHandler) {
        this.messageHandler(event)
      }
    }

    ws.onclose = (event) => {
      this.socketOpen = false
      this.stopHeartbeat()
      notifyStatus('closed')

      // token 已被清除（登出），不再重连
      const token = localStorage.getItem('access_token')
      if (!token) {
        this.isReconnect = false
        return
      }

      this.scheduleReconnect()
    }

    ws.onerror = () => {
      this.socketOpen = false
      notifyStatus('error')
    }

    // 页面切回前台时检查连接状态
    if (!this._visibilityHandler) {
      this._visibilityHandler = () => {
        if (document.visibilityState === 'visible' && !this.socketOpen) {
          const token = localStorage.getItem('access_token')
          if (token) {
            // 重置重连计数，立即尝试重连
            this.reconnectCount = 0
            this.isReconnect = true
            this.scheduleReconnect(500)
          }
        }
      }
      document.addEventListener('visibilitychange', this._visibilityHandler)
    }
  },
  scheduleReconnect(delayOverride) {
    if (!this.isReconnect) {
      return
    }
    if (this.reconnectCount >= this.reconnectMaxCount) {
      // 达到最大重连次数，暂停重连，等待页面切回前台时重试
      return
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    // 指数退避：3s, 6s, 12s, 24s... 最大 60s
    const delay = delayOverride != null
      ? delayOverride
      : Math.min(
          this.reconnectBaseInterval * Math.pow(2, this.reconnectCount),
          this.reconnectMaxInterval
        )
    this.reconnectTimer = setTimeout(() => {
      this.reconnectCount += 1
      this.reconnect()
    }, delay)
  },
  heartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      const token = localStorage.getItem('access_token')
      if (!token) {
        return
      }
      const data = { token }
      this.send(data)
    }, this.heartbeatInterval)
  },
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  },
  send(data) {
    if (!this.websocket) {
      this.socketOpen = false
      notifyStatus('closed')
      return
    }
    if (this.websocket.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data)
      this.websocket.send(payload)
    } else {
      this.stopHeartbeat()
      this.socketOpen = false
      notifyStatus('closed')
    }
  },
  close() {
    this.isReconnect = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.stopHeartbeat()
    if (this.websocket) {
      try {
        this.websocket.close()
      } catch (e) {}
      this.websocket = null
    }
    this.socketOpen = false
    notifyStatus('closed')
  },
  reconnect() {
    // 清理旧连接但不改变 isReconnect 状态
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.stopHeartbeat()
    if (this.websocket) {
      try {
        this.websocket.close()
      } catch (e) {}
      this.websocket = null
    }
    this.socketOpen = false
    this.init(this.messageHandler)
  },
  subscribeStatus(listener) {
    if (typeof listener !== 'function') {
      return
    }
    statusListeners.push(listener)
  },
  unsubscribeStatus(listener) {
    if (!statusListeners.length) {
      return
    }
    if (!listener) {
      statusListeners = []
      return
    }
    const index = statusListeners.indexOf(listener)
    if (index !== -1) {
      statusListeners.splice(index, 1)
    }
  }
}

export default websocket
