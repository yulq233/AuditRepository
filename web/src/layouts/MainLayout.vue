<template>
  <div class="layout-container">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><DocumentChecked /></el-icon>
        <span>AI审计抽凭</span>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/dashboard" :class="['nav-item', { 'is-active': activeMenu === '/dashboard' }]">
          <el-icon><HomeFilled /></el-icon>
          <span>工作台</span>
        </router-link>

        <router-link to="/projects" :class="['nav-item', { 'is-active': activeMenu === '/projects' }]">
          <el-icon><Folder /></el-icon>
          <span>项目管理</span>
        </router-link>

        <router-link to="/vouchers" :class="['nav-item', { 'is-active': activeMenu === '/vouchers' }]">
          <el-icon><Document /></el-icon>
          <span>凭证管理</span>
        </router-link>

        <div
          class="nav-group"
          @mouseenter="openFlyout"
          @mouseleave="closeFlyout"
        >
          <div :class="['nav-item', { 'is-active': isSamplingActive }]">
            <el-icon><DataAnalysis /></el-icon>
            <span>智能抽样</span>
            <el-icon class="nav-arrow"><ArrowRight /></el-icon>
          </div>
        </div>

        <router-link to="/matching" :class="['nav-item', { 'is-active': activeMenu === '/matching' }]">
          <el-icon><Connection /></el-icon>
          <span>三单匹配</span>
        </router-link>

        <router-link to="/compliance" :class="['nav-item', { 'is-active': activeMenu === '/compliance' }]">
          <el-icon><Warning /></el-icon>
          <span>合规检查</span>
        </router-link>

        <router-link to="/tasks" :class="['nav-item', { 'is-active': activeMenu === '/tasks' }]">
          <el-icon><List /></el-icon>
          <span>任务管理</span>
        </router-link>

        <router-link to="/papers" :class="['nav-item', { 'is-active': activeMenu === '/papers' }]">
          <el-icon><Notebook /></el-icon>
          <span>工作底稿</span>
        </router-link>

        <router-link to="/audit-trail" :class="['nav-item', { 'is-active': activeMenu === '/audit-trail' }]">
          <el-icon><Clock /></el-icon>
          <span>审计轨迹</span>
        </router-link>

        <router-link to="/ai" :class="['nav-item', { 'is-active': activeMenu === '/ai' }]">
          <el-icon><MagicStick /></el-icon>
          <span>AI服务</span>
        </router-link>

        <router-link to="/crawler" :class="['nav-item', { 'is-active': activeMenu === '/crawler' }]">
          <el-icon><Download /></el-icon>
          <span>数据爬取</span>
        </router-link>
      </nav>
    </div>

    <!-- 弹出子菜单 - 放在 sidebar 外部避免被 overflow 裁剪 -->
    <transition name="flyout">
      <div
        v-show="samplingOpen"
        class="flyout-panel"
        :style="{ top: flyoutTop + 'px' }"
        @mouseenter="samplingOpen = true"
        @mouseleave="samplingOpen = false"
      >
        <div class="flyout-title">智能抽样</div>
        <router-link to="/sampling/wizard" :class="['flyout-item', { 'is-active': activeMenu === '/sampling/wizard' }]">抽样向导</router-link>
        <router-link to="/sampling/risk-profile" :class="['flyout-item', { 'is-active': activeMenu === '/sampling/risk-profile' }]">风险画像</router-link>
        <router-link to="/sampling/strategy" :class="['flyout-item', { 'is-active': activeMenu === '/sampling/strategy' }]">抽样策略</router-link>
        <router-link to="/sampling/execute" :class="['flyout-item', { 'is-active': activeMenu === '/sampling/execute' }]">执行抽样</router-link>
        <router-link to="/sampling/results" :class="['flyout-item', { 'is-active': activeMenu === '/sampling/results' }]">抽样结果</router-link>
      </div>
    </transition>

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
const flyoutTop = ref(0)

const isSamplingActive = computed(() =>
  route.path.startsWith('/sampling')
)

const openFlyout = (e) => {
  const rect = e.currentTarget.getBoundingClientRect()
  flyoutTop.value = rect.top
  samplingOpen.value = true
}

const closeFlyout = () => {
  samplingOpen.value = false
}

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
  position: relative;
}

.sidebar {
  width: $sidebar-width;
  background: $background-white;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $border-light;
  flex-shrink: 0;

  .logo {
    height: $header-height;
    display: flex;
    align-items: center;
    justify-content: center;
    color: $text-primary;
    font-size: 16px;
    font-weight: 700;
    flex-shrink: 0;
    letter-spacing: 0.5px;

    .logo-icon {
      margin-right: 10px;
      font-size: 22px;
      color: $primary-color;
    }
  }
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.nav-item {
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
  text-decoration: none;

  .el-icon {
    margin-right: 10px;
    font-size: 18px;
    flex-shrink: 0;
  }

  span {
    flex: 1;
    font-size: 14px;
  }

  .nav-arrow {
    margin-right: 0;
    margin-left: auto;
    font-size: 12px;
    transition: transform $transition-fast;
  }

  &:hover {
    background: $sidebar-hover-bg;
    color: $sidebar-text-hover;

    .nav-arrow {
      transform: translateX(2px);
    }
  }

  &.is-active {
    color: $sidebar-text-active;
    background: $sidebar-active-bg;
    border-left: 3px solid $sidebar-active-border;
    border-radius: 0 $border-radius-md $border-radius-md 0;
    padding-left: 17px;
  }
}

.nav-group {
  position: relative;
}

// 弹出面板 - fixed定位，不受sidebar overflow影响
.flyout-panel {
  position: fixed;
  left: #{$sidebar-width + 4px};
  width: 160px;
  background: $background-white;
  border: 1px solid $border-light;
  border-radius: $border-radius-lg;
  box-shadow: $shadow-lg;
  padding: 6px;
  z-index: 2000;
}

.flyout-title {
  padding: 8px 14px 6px;
  font-size: 11px;
  font-weight: $font-weight-semibold;
  color: $text-placeholder;
  letter-spacing: 0.5px;
}

.flyout-item {
  display: block;
  height: 36px;
  line-height: 36px;
  padding: 0 14px;
  border-radius: $border-radius-sm;
  font-size: 13px;
  color: $sidebar-text;
  text-decoration: none;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: $sidebar-hover-bg;
    color: $sidebar-text-hover;
  }

  &.is-active {
    color: $sidebar-text-active;
    background: $sidebar-active-bg;
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
</style>