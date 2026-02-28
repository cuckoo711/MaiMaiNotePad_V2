import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import VerifyEmail from '@/views/auth/VerifyEmail.vue'
import ResetPassword from '@/views/auth/ResetPassword.vue'
import Home from '@/views/layout/Home.vue'
import PersonaCard from '@/views/persona/PersonaCard.vue'
import MyPersona from '@/views/persona/MyPersona.vue'
import PersonaUpload from '@/views/persona/PersonaUpload.vue'
import PersonaReview from '@/views/admin/PersonaReview.vue'
import KnowledgeBase from '@/views/knowledge/KnowledgeBase.vue'
import MyKnowledge from '@/views/knowledge/MyKnowledge.vue'
import UserCenter from '@/views/user/UserCenter.vue'
import KnowledgeUpload from '@/views/knowledge/KnowledgeUpload.vue'
import KnowledgeReview from '@/views/admin/KnowledgeReview.vue'
import AdminUserManagement from '@/views/admin/AdminUserManagement.vue'
import AdminDashboard from '@/views/admin/AdminDashboard.vue'
import AdminMuteManagement from '@/views/admin/AdminMuteManagement.vue'
import AdminAnnouncement from '@/views/admin/AdminAnnouncement.vue'
import FavoritePersona from '@/views/favorites/FavoritePersona.vue'
import FavoriteKnowledge from '@/views/favorites/FavoriteKnowledge.vue'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      pageTitle: '登录'
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: {
      pageTitle: '注册'
    }
  },
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: VerifyEmail,
    meta: {
      pageTitle: '验证邮箱'
    }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: ResetPassword,
    meta: {
      pageTitle: '重置密码'
    }
  },
  {
    path: '/home',
    name: 'Home',
    component: Home,
    meta: {
      pageTitle: '麦麦笔记本'
    },
    redirect: '/persona-card',
    children: [
      {
        path: '/persona-card',
        name: 'PersonaCard',
        component: PersonaCard,
        meta: {
          pageTitle: '人设卡广场'
        }
      },
      {
        path: '/my-persona',
        name: 'MyPersona',
        component: MyPersona,
        meta: {
          pageTitle: '我的人设卡'
        }
      },
      {
        path: '/persona-upload',
        name: 'PersonaUpload',
        component: PersonaUpload,
        meta: {
          pageTitle: '创建人设卡'
        }
      },
      {
        path: '/knowledge-base',
        name: 'KnowledgeBase',
        component: KnowledgeBase,
        meta: {
          pageTitle: '知识库广场'
        }
      },
      {
        path: '/my-knowledge',
        name: 'MyKnowledge',
        component: MyKnowledge,
        meta: {
          pageTitle: '我的知识库'
        }
      },
      {
        path: '/favorite-persona',
        name: 'FavoritePersona',
        component: FavoritePersona,
        meta: {
          pageTitle: '收藏人设卡'
        }
      },
      {
        path: '/favorite-knowledge',
        name: 'FavoriteKnowledge',
        component: FavoriteKnowledge,
        meta: {
          pageTitle: '收藏知识库'
        }
      },
      {
        path: '/knowledge-upload',
        name: 'KnowledgeUpload',
        component: KnowledgeUpload,
        meta: {
          pageTitle: '上传知识库'
        }
      },
      {
        path: '/knowledge-review',
        name: 'KnowledgeReview',
        component: KnowledgeReview,
        meta: {
          pageTitle: '知识库审核'
        }
      },
      {
        path: '/persona-review',
        name: 'PersonaReview',
        component: PersonaReview,
        meta: {
          pageTitle: '人设卡审核'
        }
      },
      {
        path: '/admin-dashboard',
        name: 'AdminDashboard',
        component: AdminDashboard,
        meta: {
          pageTitle: '运营看板'
        }
      },
      {
        path: '/admin-announcement',
        name: 'AdminAnnouncement',
        component: AdminAnnouncement,
        meta: {
          pageTitle: '发布公告'
        }
      },
      {
        path: '/admin-users',
        name: 'AdminUserManagement',
        component: AdminUserManagement,
        meta: {
          pageTitle: '用户管理'
        }
      },
      {
        path: '/admin-mute',
        name: 'AdminMuteManagement',
        component: AdminMuteManagement,
        meta: {
          pageTitle: '禁言管理'
        }
      },
      {
        path: '/user-center',
        name: 'UserCenter',
        component: UserCenter,
        meta: {
          pageTitle: '个人中心'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 不需要认证的页面白名单
const publicPages = ['/login', '/register', '/verify-email', '/reset-password']

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const isPublic = publicPages.includes(to.path)

  if (!isPublic && !token) {
    // 未登录访问需要认证的页面，重定向到登录页
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (isPublic && token && to.path === '/login') {
    // 已登录用户访问登录页，重定向到首页
    return next('/home')
  }

  next()
})

const baseTitle = '麦麦笔记本'

router.afterEach((to) => {
  const pageTitle = to.meta && to.meta.pageTitle ? to.meta.pageTitle : ''
  if (pageTitle) {
    document.title = `${baseTitle} - ${pageTitle}`
  } else {
    document.title = baseTitle
  }
})

export default router
