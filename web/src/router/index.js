import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '工作台', icon: 'HomeFilled' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/projects/index.vue'),
        meta: { title: '项目管理', icon: 'Folder' }
      },
      {
        path: 'projects/:id',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/detail.vue'),
        meta: { title: '项目详情', hidden: true }
      },
      {
        path: 'vouchers',
        name: 'Vouchers',
        component: () => import('@/views/vouchers/index.vue'),
        meta: { title: '凭证管理', icon: 'Document' }
      },
      {
        path: 'vouchers/:projectId/:id',
        name: 'VoucherDetail',
        component: () => import('@/views/vouchers/detail.vue'),
        meta: { title: '凭证详情', hidden: true }
      },
      {
        path: 'sampling',
        name: 'Sampling',
        redirect: '/sampling/risk-profile',
        meta: { title: '智能抽样', icon: 'DataAnalysis' },
        children: [
          {
            path: 'wizard',
            name: 'SamplingWizard',
            component: () => import('@/views/sampling/wizard.vue'),
            meta: { title: '抽样向导' }
          },
          {
            path: 'risk-profile',
            name: 'RiskProfile',
            component: () => import('@/views/sampling/risk-profile.vue'),
            meta: { title: '风险画像' }
          },
          {
            path: 'strategy',
            name: 'SamplingStrategy',
            component: () => import('@/views/sampling/strategy.vue'),
            meta: { title: '抽样策略' }
          },
          {
            path: 'execute',
            name: 'SamplingExecute',
            component: () => import('@/views/sampling/execute.vue'),
            meta: { title: '执行抽样' }
          },
          {
            path: 'results',
            name: 'SamplingResults',
            component: () => import('@/views/sampling/results.vue'),
            meta: { title: '抽样结果' }
          },
          {
            path: 'test',
            name: 'SampleTest',
            component: () => import('@/views/sampling/test.vue'),
            meta: { title: '样本测试' }
          },
          {
            path: 'inference',
            name: 'Inference',
            component: () => import('@/views/sampling/inference.vue'),
            meta: { title: '总体推断' }
          },
          {
            path: 'detail',
            name: 'SamplingDetail',
            component: () => import('@/views/sampling/detail.vue'),
            meta: { title: '抽样详情', hidden: true }
          }
        ]
      },
      {
        path: 'matching',
        name: 'Matching',
        component: () => import('@/views/matching/index.vue'),
        meta: { title: '三单匹配', icon: 'Connection' }
      },
      {
        path: 'compliance',
        name: 'Compliance',
        component: () => import('@/views/compliance/index.vue'),
        meta: { title: '合规检查', icon: 'Warning' }
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/tasks/index.vue'),
        meta: { title: '任务管理', icon: 'List' }
      },
      {
        path: 'papers',
        name: 'Papers',
        component: () => import('@/views/papers/index.vue'),
        meta: { title: '工作底稿', icon: 'Notebook' }
      },
      {
        path: 'audit-trail',
        name: 'AuditTrail',
        component: () => import('@/views/audit-trail/index.vue'),
        meta: { title: '审计轨迹', icon: 'Clock' }
      },
      {
        path: 'ai',
        name: 'AI',
        component: () => import('@/views/ai/index.vue'),
        meta: { title: 'AI服务', icon: 'MagicStick' }
      },
      {
        path: 'crawler',
        name: 'Crawler',
        component: () => import('@/views/crawler/index.vue'),
        meta: { title: '数据爬取', icon: 'Download' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - AI审计抽凭助手` : 'AI审计抽凭助手'

  // 检查登录状态
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router