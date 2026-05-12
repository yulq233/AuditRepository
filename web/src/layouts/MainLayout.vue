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
        background-color="#ffffff"
        text-color="#64748b"
        active-text-color="#2563eb"
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

        <div class="sub-menu-wrapper" @mouseenter="samplingOpen = true" @mouseleave="samplingOpen = false">
          <div :class="['sub-menu-trigger', { 'is-active': isSamplingActive }]">
            <el-icon><DataAnalysis /></el-icon>
            <span>智能抽样</span>
            <el-icon class="arrow-icon"><ArrowRight /></el-icon>
          </div>
          <transition name="flyout">
            <div v-show="samplingOpen" class="flyout-panel">
              <div class="flyout-header">智能抽样</div>
              <el-menu-item index="/sampling/wizard">抽样向导</el-menu-item>
              <el-menu-item index="/sampling/risk-profile">风险画像</el-menu-item>
              <el-menu-item index="/sampling/strategy">抽样策略</el-menu-item>
              <el-menu-item index="/sampling/execute">执行抽样</el-menu-item>
              <el-menu-item index="/sampling/results">抽样结果</el-menu-item>
            </div>
          </transition>
        </div>

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
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)
const username = computed(() => localStorage.getItem('username') || '用户')
const samplingOpen = ref(false)

const isSamplingActive = computed(() =>
  route.path.startsWith('/sampling')
)

const handleCommand = (command) => {
  switch (command) {
    case 'logout':
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      router.push('/login')
      break
    case 'profile':
      ElMessage.info('个人中心功能开发中')
      break
    case 'settings':
      ElMessage.info('设置功能开发中')
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
  width: $sidebar-width;
  background: linear-gradient(180deg, $sidebar-bg 0%, $sidebar-bg-end 100%);
  height: 100%;
  overflow-y: auto;
  border-right: 1px solid $border-light;

  .logo {
    height: $header-height;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-primary;
    font-size: 16px;
    font-weight: 700;
    background: $background-white;
    letter-spacing: 0.5px;

    .logo-icon {
      margin-right: 10px;
      font-size: 22px;
      color: $primary-color;
    }
  }

  :deep(.el-menu) {
    border-right: none;
    background: transparent;
    padding: 6px;
  }

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    color: $sidebar-text;
    border-radius: $border-radius-md;
    margin: 1px 0;
    height: 42px;
    line-height: 42px;

    &:hover {
      background: $sidebar-hover-bg;
      color: $sidebar-text-hover;
    }
  }

  :deep(.el-menu-item.is-active) {
    color: $sidebar-text-active;
    background: $sidebar-active-bg;
    border-left: 3px solid $sidebar-active-border;
    border-radius: 0 $border-radius-md $border-radius-md 0;
    padding-left: 17px;
  }
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: $header-height;
  background: #fff;
  border-bottom: 1px solid $border-color;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;

  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;
    padding: 5px 10px;
    border-radius: $border-radius-md;
    transition: all $transition-fast;

    &:hover {
      background: $background-color;
    }

    .username {
      margin-left: 8px;
      color: $text-primary;
      font-size: 13px;
      font-weight: 500;
    }
  }
}

.content {
  flex: 1;
  overflow-y: auto;
  background: $background-color;
}

// 侧边弹出子菜单
.sub-menu-wrapper {
  position: relative;
}

.sub-menu-trigger {
  display: flex;
  align-items: center;
  height: 42px;
  line-height: 42px;
  padding: 0 20px;
  margin: 1px 0;
  border-radius: $border-radius-md;
  color: $sidebar-text;
  cursor: pointer;
  transition: all $transition-fast;

  .el-icon:first-child {
    margin-right: 10px;
    font-size: 18px;
  }

  .arrow-icon {
    margin-left: auto;
    font-size: 12px;
    transition: transform $transition-fast;
  }

  &:hover {
    background: $sidebar-hover-bg;
    color: $sidebar-text-hover;

    .arrow-icon {
      transform: translateX(2px);
    }
  }

  &.is-active {
    color: $sidebar-text-active;
    background: $sidebar-active-bg;
    border-left: 3px solid $sidebar-active-border;
    border-radius: 0 $border-radius-md $border-radius-md 0;
    padding-left: 17px;

    .el-icon:first-child {
      color: $sidebar-text-active;
    }
  }
}

.flyout-panel {
  position: absolute;
  left: 100%;
  top: 0;
  width: 160px;
  background: $background-white;
  border: 1px solid $border-light;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-lg;
  padding: 6px;
  z-index: 100;

  .flyout-header {
    padding: 8px 14px 6px;
    font-size: 12px;
    font-weight: $font-weight-semibold;
    color: $text-placeholder;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }

  :deep(.el-menu-item) {
    height: 36px;
    line-height: 36px;
    font-size: 13px;
    border-radius: $border-radius-sm;
    color: $sidebar-text;
    background: transparent;
    border-left: none;
    padding-left: 14px !important;

    &:hover {
      background: $sidebar-hover-bg;
      color: $sidebar-text-hover;
    }

    &.is-active {
      color: $sidebar-text-active;
      background: $sidebar-active-bg;
      border-left: none;
      padding-left: 14px;
    }
  }
}

// 弹出动画
.flyout-enter-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.flyout-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.flyout-enter-from {
  opacity: 0;
  transform: translateX(-4px);
}
.flyout-leave-to {
  opacity: 0;
  transform: translateX(-4px);
}
</style>