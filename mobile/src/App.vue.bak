<script>
export default {
  onLaunch: function() {
    console.log('App Launch')
  },
  onShow: function() {
    console.log('App Show')
  },
  onHide: function() {
    console.log('App Hide')
  }
}
</script>

<style>
/* =============================================
   AI审计抽凭系统 - 移动端全局样式
   ============================================= */

/* 基础重置 */
page {
  background-color: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Helvetica, Segoe UI, Arial, Roboto, 'PingFang SC', 'miui', 'Hiragino Sans GB', 'Microsoft Yahei', sans-serif;
  font-size: 28rpx;
  color: #303133;
  line-height: 1.5;
}

/* 容器 */
.container {
  padding: 20rpx;
  min-height: 100vh;
}

/* =============================================
   颜色变量（使用CSS变量便于主题切换）
   ============================================= */
page {
  --primary-color: #409eff;
  --primary-light: #66b1ff;
  --primary-lighter: #c6e2ff;

  --success-color: #67c23a;
  --success-lighter: #e1f3d8;

  --warning-color: #e6a23c;
  --warning-lighter: #fdf6ec;

  --danger-color: #f56c6c;
  --danger-lighter: #fde2e2;

  --info-color: #909399;
  --info-lighter: #e9e9eb;

  --text-primary: #303133;
  --text-regular: #606266;
  --text-secondary: #909399;
  --text-placeholder: #c0c4cc;

  --border-color: #dcdfe6;
  --background-color: #f5f5f5;
  --white: #ffffff;
}

/* =============================================
   卡片组件
   ============================================= */
.card {
  background: var(--white);
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.card-title {
  font-size: 32rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.card-more {
  font-size: 26rpx;
  color: var(--primary-color);
}

/* =============================================
   状态标签
   ============================================= */
.status-tag {
  display: inline-flex;
  align-items: center;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
  font-weight: 500;
}

.status-tag.active {
  background: var(--success-lighter);
  color: var(--success-color);
}

.status-tag.completed {
  background: var(--primary-lighter);
  color: var(--primary-color);
}

.status-tag.archived {
  background: var(--info-lighter);
  color: var(--info-color);
}

.status-tag.pending {
  background: var(--warning-lighter);
  color: var(--warning-color);
}

/* =============================================
   风险标签
   ============================================= */
.risk-tag {
  display: inline-flex;
  align-items: center;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
  font-weight: 500;
}

.risk-tag.high {
  background: var(--danger-lighter);
  color: var(--danger-color);
}

.risk-tag.medium {
  background: var(--warning-lighter);
  color: var(--warning-color);
}

.risk-tag.low {
  background: var(--success-lighter);
  color: var(--success-color);
}

/* =============================================
   统计卡片
   ============================================= */
.stats-card {
  display: flex;
  justify-content: space-around;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
  padding: 32rpx 0;
  border-radius: 16rpx;
  margin-bottom: 20rpx;
}

.stat-item {
  text-align: center;
  color: var(--white);
}

.stat-value {
  font-size: 44rpx;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 24rpx;
  margin-top: 8rpx;
  opacity: 0.9;
}

/* =============================================
   快捷入口
   ============================================= */
.quick-actions {
  display: flex;
  justify-content: space-around;
  padding: 20rpx 0;
}

.action-item {
  text-align: center;
  flex: 1;
}

.action-icon {
  width: 100rpx;
  height: 100rpx;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12rpx;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.1);
}

.action-name {
  font-size: 24rpx;
  color: var(--text-regular);
}

/* =============================================
   列表项
   ============================================= */
.list-item {
  display: flex;
  align-items: center;
  background: var(--white);
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.list-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
  flex-shrink: 0;
}

.list-info {
  flex: 1;
  min-width: 0;
}

.list-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-desc {
  font-size: 24rpx;
  color: var(--text-secondary);
}

.list-action {
  flex-shrink: 0;
  margin-left: 16rpx;
}

/* =============================================
   空状态
   ============================================= */
.empty-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80rpx 0;
  color: var(--text-placeholder);
}

.empty-icon {
  font-size: 96rpx;
  margin-bottom: 16rpx;
}

.empty-text {
  font-size: 28rpx;
}

/* =============================================
   按钮
   ============================================= */
.action-area {
  padding: 20rpx 0;
}

.btn-primary {
  background: var(--primary-color);
  color: var(--white);
  border: none;
  border-radius: 12rpx;
  padding: 24rpx;
  font-size: 28rpx;
  font-weight: 500;
  text-align: center;
}

.btn-secondary {
  background: var(--primary-lighter);
  color: var(--primary-color);
  border: none;
  border-radius: 12rpx;
  padding: 24rpx;
  font-size: 28rpx;
  font-weight: 500;
  text-align: center;
}

/* =============================================
   表单
   ============================================= */
.form-group {
  margin-bottom: 24rpx;
}

.form-label {
  font-size: 28rpx;
  color: var(--text-regular);
  margin-bottom: 12rpx;
  display: block;
}

.form-input {
  width: 100%;
  background: var(--background-color);
  border: 1px solid var(--border-color);
  border-radius: 12rpx;
  padding: 24rpx;
  font-size: 28rpx;
}

/* =============================================
   金额显示
   ============================================= */
.amount {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
}

.amount-positive {
  color: var(--success-color);
}

.amount-negative {
  color: var(--danger-color);
}

/* =============================================
   工具类
   ============================================= */
.text-primary { color: var(--primary-color); }
.text-success { color: var(--success-color); }
.text-warning { color: var(--warning-color); }
.text-danger { color: var(--danger-color); }
.text-muted { color: var(--text-secondary); }

.text-center { text-align: center; }
.text-right { text-align: right; }

.font-bold { font-weight: 700; }
.font-medium { font-weight: 500; }

.mt-sm { margin-top: 16rpx; }
.mt-md { margin-top: 24rpx; }
.mb-sm { margin-bottom: 16rpx; }
.mb-md { margin-bottom: 24rpx; }

.flex { display: flex; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
</style>