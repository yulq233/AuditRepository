<template>
  <div class="layout-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><DocumentChecked /></el-icon>
        <span>AI审计抽凭</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>工作台</span>
        </el-menu-item>

        <el-menu-item index="/projects">
          <el-icon><Folder /></el-icon>
          <span>项目管理</span>
        </el-menu-item>

        <el-menu-item index="/vouchers">
          <el-icon><Document /></el-icon>
          <span>凭证管理</span>
        </el-menu-item>

        <el-sub-menu index="/sampling">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>智能抽样</span>
          </template>
          <el-menu-item index="/sampling/wizard">抽样向导</el-menu-item>
          <el-menu-item index="/sampling/risk-profile">风险画像</el-menu-item>
          <el-menu-item index="/sampling/strategy">抽样策略</el-menu-item>
          <el-menu-item index="/sampling/execute">执行抽样</el-menu-item>
          <el-menu-item index="/sampling/results">抽样结果</el-menu-item>
        </el-sub-menu>

        <el-menu-item index="/matching">
          <el-icon><Connection /></el-icon>
          <span>三单匹配</span>
        </el-menu-item>

        <el-menu-item index="/compliance">
          <el-icon><Warning /></el-icon>
          <span>合规检查</span>
        </el-menu-item>

        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>任务管理</span>
        </el-menu-item>

        <el-menu-item index="/papers">
          <el-icon><Notebook /></el-icon>
          <span>工作底稿</span>
        </el-menu-item>

        <el-menu-item index="/audit-trail">
          <el-icon><Clock /></el-icon>
          <span>审计轨迹</span>
        </el-menu-item>

        <el-menu-item index="/ai">
          <el-icon><MagicStick /></el-icon>
          <span>AI服务</span>
        </el-menu-item>

        <el-menu-item index="/crawler">
          <el-icon><Download /></el-icon>
          <span>数据爬取</span>
        </el-menu-item>
      </el-menu>
    </div>

    <!-- 主内容区 -->
    <div class="main-container">
      <!-- 顶部导航 -->
      <div class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.meta?.title">
              {{ currentRoute.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <div class="user-info">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ username }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="settings">设置</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- 内容区 -->
      <div class="content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)
const username = computed(() => localStorage.getItem('username') || '用户')

const handleCommand = (command) => {
  switch (command) {
    case 'logout':
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      router.push('/login')
      break
    case 'profile':
      // TODO: 跳转个人中心
      break
    case 'settings':
      // TODO: 跳转设置
      break
  }
}
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.layout-container {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 220px;
  background: #304156;
  height: 100%;
  overflow-y: auto;

  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    background: #263445;

    .logo-icon {
      margin-right: 10px;
      font-size: 20px;
    }
  }

  :deep(.el-menu) {
    border-right: none;
    background: transparent;
  }
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;

  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;

    .username {
      margin-left: 8px;
      color: #606266;
    }
  }
}

.content {
  flex: 1;
  overflow-y: auto;
  background: #f5f7fa;
}
</style>