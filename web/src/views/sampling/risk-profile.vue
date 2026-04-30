<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h2 class="page-title">风险画像</h2>
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-select
          v-model="projectId"
          placeholder="选择项目"
          style="width: 200px"
          @change="onProjectChange"
        >
          <el-option
            v-for="project in projects"
            :key="project.id"
            :label="project.name"
            :value="project.id"
          />
        </el-select>
        <el-button type="primary" @click="generateAllProfiles" :disabled="!projectId" :loading="generating">
          <el-icon><Refresh /></el-icon>
          生成风险画像
        </el-button>
        <el-button @click="openRiskConfig" :disabled="!projectId">
          <el-icon><Setting /></el-icon>
          风险配置
        </el-button>
      </div>
    </div>

    <!-- 项目风险概览 -->
    <div class="overview-section" v-loading="loading">
      <!-- 整体风险评分 -->
      <div class="overview-card score-card">
        <div class="card-header">
          <el-icon class="header-icon"><Warning /></el-icon>
          <span class="header-title">整体风险评分</span>
        </div>
        <div class="card-body">
          <div class="score-gauge">
            <el-progress
              type="dashboard"
              :percentage="overview.overall_risk_score || 0"
              :color="getScoreColor(overview.overall_risk_score)"
              :width="130"
              :stroke-width="10"
            >
              <template #default="{ percentage }">
                <span class="score-number">{{ percentage }}</span>
                <span class="score-unit">分</span>
              </template>
            </el-progress>
          </div>
          <div class="score-footer">
            <el-tag :type="getRiskType(overview.overall_risk_level)" size="large" effect="dark">
              {{ getRiskLabel(overview.overall_risk_level) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 风险维度雷达图 -->
      <div class="overview-card radar-card">
        <div class="card-header">
          <el-icon class="header-icon"><Aim /></el-icon>
          <span class="header-title">风险维度雷达图</span>
        </div>
        <div class="card-body">
          <div ref="radarChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 高风险科目TOP5 -->
      <div class="overview-card top-card">
        <div class="card-header">
          <el-icon class="header-icon"><TrendCharts /></el-icon>
          <span class="header-title">高风险科目 TOP5</span>
        </div>
        <div class="card-body">
          <div class="top-list" v-if="highRiskSubjects.length">
            <div class="top-item" v-for="(item, index) in highRiskSubjects" :key="item.subject_code">
              <div class="top-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</div>
              <div class="top-info">
                <div class="top-name">{{ item.subject_name }}</div>
                <div class="top-meta">
                  <span class="top-score" :style="{ color: getRiskColor(item.risk_level) }">
                    {{ item.risk_score?.toFixed(0) }}分
                  </span>
                  <el-tag :type="getRiskType(item.risk_level)" size="small">{{ getRiskLabel(item.risk_level) }}</el-tag>
                </div>
              </div>
              <el-button class="top-action" type="primary" link size="small" @click="drillDownSubject(item)">
                详情
              </el-button>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="50" />
        </div>
      </div>

      <!-- 风险趋势 -->
      <div class="overview-card trend-card">
        <div class="card-header">
          <el-icon class="header-icon"><DataLine /></el-icon>
          <span class="header-title">风险趋势</span>
        </div>
        <div class="card-body">
          <div ref="trendChartRef" class="chart-container"></div>
        </div>
      </div>
    </div>

    <!-- 多维分析Tabs -->
    <el-tabs v-model="activeTab" style="margin-top: 20px" @tab-change="onTabChange">
      <!-- 科目维度 -->
      <el-tab-pane label="科目维度" name="subjects">
        <el-card class="card-container">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>科目风险画像</span>
              <el-input v-model="searchKeyword" placeholder="搜索科目" style="width: 200px" clearable />
            </div>
          </template>

          <!-- 风险分布图 -->
          <el-row :gutter="20" style="margin-bottom: 20px">
            <el-col :span="8">
              <div ref="riskPieChartRef" style="height: 200px"></div>
            </el-col>
            <el-col :span="16">
              <div ref="subjectBarChartRef" style="height: 200px"></div>
            </el-col>
          </el-row>

          <!-- 科目列表 -->
          <el-table :data="filteredProfiles" style="width: 100%">
            <el-table-column prop="subject_code" label="科目代码" width="120" />
            <el-table-column prop="subject_name" label="科目名称" min-width="150" />
            <el-table-column prop="risk_level" label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="risk_score" label="风险分数" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.risk_score"
                  :color="getRiskColor(row.risk_level)"
                  :stroke-width="10"
                />
              </template>
            </el-table-column>
            <el-table-column prop="material_amount" label="重要性水平" width="120">
              <template #default="{ row }">
                {{ formatAmount(row.material_amount) }}
              </template>
            </el-table-column>
            <el-table-column label="风险因素" min-width="200">
              <template #default="{ row }">
                <el-tag
                  v-for="(factor, index) in (row.risk_factors || []).slice(0, 3)"
                  :key="index"
                  size="small"
                  style="margin-right: 5px"
                >
                  {{ factor.name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewSubjectDetail(row)">详情</el-button>
                <el-button type="primary" link @click="goToSampling(row)">抽样</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 交易对手维度 -->
      <el-tab-pane label="交易对手维度" name="counterparty">
        <el-card class="card-container" v-loading="counterpartyLoading">
          <template #header>交易对手风险分析</template>
          <el-table :data="counterpartyRisks" style="width: 100%" class="counterparty-table">
            <el-table-column prop="counterparty_name" label="交易对手" min-width="150" show-overflow-tooltip />
            <el-table-column prop="total_amount" label="交易金额" min-width="120">
              <template #default="{ row }">{{ formatAmount(row.total_amount) }}</template>
            </el-table-column>
            <el-table-column prop="transaction_count" label="交易笔数" min-width="80" />
            <el-table-column prop="concentration_ratio" label="集中度" min-width="80">
              <template #default="{ row }">{{ (row.concentration_ratio * 100).toFixed(2) }}%</template>
            </el-table-column>
            <el-table-column label="关联方" min-width="70">
              <template #default="{ row }">
                <el-tag v-if="row.is_related_party" type="danger" size="small">是</el-tag>
                <el-tag v-else type="success" size="small">否</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="新客户" min-width="70">
              <template #default="{ row }">
                <el-tag v-if="row.is_new_customer" type="warning" size="small">是</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="risk_level" label="风险等级" min-width="90">
              <template #default="{ row }">
                <el-tag :type="getRiskType(row.risk_level)">{{ getRiskLabel(row.risk_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="risk_score" label="风险分数" min-width="100">
              <template #default="{ row }">
                <el-progress :percentage="row.risk_score" :color="getRiskColor(row.risk_level)" :stroke-width="8" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 时间维度 -->
      <el-tab-pane label="时间维度" name="time">
        <el-card class="card-container" v-loading="timeLoading">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>时间维度风险分析</span>
              <el-radio-group v-model="periodType" @change="loadTimeAnalysis">
                <el-radio-button label="monthly">按月</el-radio-button>
                <el-radio-button label="quarterly">按季度</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="14">
              <div ref="timeChartRef" style="height: 300px"></div>
            </el-col>
            <el-col :span="10">
              <h4>异常期间标记</h4>
              <el-table :data="timeAnomalies" size="small" max-height="260">
                <el-table-column prop="period" label="期间" width="100" />
                <el-table-column prop="total_amount" label="金额" width="120">
                  <template #default="{ row }">{{ formatAmount(row.total_amount) }}</template>
                </el-table-column>
                <el-table-column label="异常指标">
                  <template #default="{ row }">
                    <el-tag v-for="(ind, idx) in row.anomaly_indicators?.slice(0, 2)" :key="idx" type="warning" size="small" style="margin-right: 4px">
                      {{ ind }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>

      <!-- 交易风险清单 -->
      <el-tab-pane label="交易风险清单" name="transactions">
        <el-card class="card-container" v-loading="transactionLoading">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>交易风险清单</span>
              <div>
                <el-button type="primary" :disabled="selectedTransactions.length === 0" @click="batchAddToSampling">
                  批量加入抽样 ({{ selectedTransactions.length }})
                </el-button>
              </div>
            </div>
          </template>

          <!-- 筛选条件 -->
          <el-form inline style="margin-bottom: 16px">
            <el-form-item label="风险等级">
              <el-select v-model="transactionFilters.risk_level" clearable placeholder="全部" style="width: 100px">
                <el-option label="高风险" value="high" />
                <el-option label="中风险" value="medium" />
                <el-option label="低风险" value="low" />
              </el-select>
            </el-form-item>
            <el-form-item label="金额范围">
              <el-input-number v-model="transactionFilters.min_amount" :min="0" placeholder="最小" style="width: 120px" />
              <span style="margin: 0 8px">-</span>
              <el-input-number v-model="transactionFilters.max_amount" :min="0" placeholder="最大" style="width: 120px" />
            </el-form-item>
            <el-form-item label="交易对手">
              <el-input v-model="transactionFilters.counterparty" placeholder="搜索" clearable style="width: 150px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="searchTransactions">搜索</el-button>
              <el-button @click="resetTransactionFilters">重置</el-button>
            </el-form-item>
          </el-form>

          <!-- 交易列表 -->
          <div class="table-scroll-wrapper">
            <el-table
              :data="transactionList"
              @selection-change="handleTransactionSelection"
              style="min-width: 1200px"
            >
              <el-table-column type="selection" width="50" />
              <el-table-column prop="voucher_no" label="凭证号" width="150" />
              <el-table-column prop="voucher_date" label="日期" min-width="150" />
              <el-table-column prop="amount" label="金额" width="140">
                <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
              </el-table-column>
              <el-table-column prop="subject_name" label="科目" min-width="150" />
              <el-table-column prop="summary" label="摘要" min-width="200">
                <template #default="{ row }">
                  <span style="white-space: pre-wrap">{{ row.summary || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="risk_level" label="风险等级" width="100">
                <template #default="{ row }">
                  <el-tag :type="getRiskType(row.risk_level)" size="small">
                    {{ getRiskLabel(row.risk_level) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="risk_score" label="风险分数" width="120">
                <template #default="{ row }">
                  <el-progress :percentage="row.risk_score || 0" :color="getRiskColor(row.risk_level)" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column label="风险标签" min-width="325">
                <template #default="{ row }">
                  <div class="risk-tags-wrap">
                    <el-tag
                      v-for="tag in row.risk_tags"
                      :key="tag.code"
                      :type="getTagType(tag.severity)"
                      size="small"
                    >
                      {{ tag.name }}
                    </el-tag>
                    <span v-if="!row.risk_tags?.length" style="color: #909399">-</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="风险因素" min-width="390">
                <template #default="{ row }">
                  <div class="risk-factors-cell">
                    <!-- AI分析结果 -->
                    <template v-if="row.ai_analysis">
                      <div class="ai-analysis-section">
                        <div v-if="row.ai_analysis.explanation" class="ai-explanation">
                          <span class="ai-label">AI分析：</span>
                          <span class="ai-content">{{ row.ai_analysis.explanation }}</span>
                        </div>
                        <div v-if="row.ai_analysis.audit_attention?.length" class="ai-attention">
                          <span class="ai-label">AI建议：</span>
                          <ul class="attention-list">
                            <li v-for="(item, idx) in row.ai_analysis.audit_attention" :key="idx">{{ item }}</li>
                          </ul>
                        </div>
                      </div>
                    </template>
                    <!-- 无数据 -->
                    <span v-else class="no-data">暂无风险说明</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" link @click="viewTransactionDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 分页 -->
          <el-pagination
            style="margin-top: 16px; justify-content: flex-end"
            v-model:current-page="transactionPage"
            v-model:page-size="transactionPageSize"
            :total="transactionTotal"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadTransactions"
            @current-change="loadTransactions"
          />
        </el-card>
      </el-tab-pane>

      <!-- 分层抽样建议 -->
      <el-tab-pane label="抽样建议" name="sampling">
        <el-card class="card-container" v-loading="samplingLoading">
          <template #header>分层抽样建议</template>
          <el-row :gutter="20">
            <el-col :span="12">
              <el-table :data="layeredData.layers" style="width: 100%">
                <el-table-column prop="level" label="风险等级" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getRiskType(row.level)">{{ getRiskLabel(row.level) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="count" label="总体数量" width="100" />
                <el-table-column label="抽样比例" width="100">
                  <template #default="{ row }">{{ (row.ratio * 100).toFixed(0) }}%</template>
                </el-table-column>
                <el-table-column prop="sample_size" label="样本量" width="100" />
                <el-table-column label="抽样方法">
                  <template #default="{ row }">
                    {{ row.level === 'high' ? '100%检查' : (row.level === 'medium' ? '分层抽样' : '随机抽样') }}
                  </template>
                </el-table-column>
              </el-table>
              <div style="margin-top: 16px">
                <el-statistic title="总样本量" :value="layeredData.total_sample_size || 0">
                  <template #suffix>笔</template>
                </el-statistic>
              </div>
            </el-col>
            <el-col :span="12">
              <h4>抽样建议说明</h4>
              <p style="color: #606266; line-height: 1.8">{{ layeredData.recommendation || '暂无建议' }}</p>
              <el-divider />
              <el-button type="primary" @click="executeLayeredSampling" :disabled="!layeredData.total_sample_size">
                执行分层抽样
              </el-button>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 科目详情对话框 -->
    <el-dialog v-model="subjectDetailVisible" title="风险画像详情" width="900px">
      <el-descriptions :column="2" border v-if="currentSubject">
        <el-descriptions-item label="科目代码">{{ currentSubject.subject_code }}</el-descriptions-item>
        <el-descriptions-item label="科目名称">{{ currentSubject.subject_name }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="getRiskType(currentSubject.risk_level)">
            {{ getRiskLabel(currentSubject.risk_level) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险分数">{{ currentSubject.risk_score?.toFixed(1) }}</el-descriptions-item>
        <el-descriptions-item label="重要性水平">{{ formatAmount(currentSubject.material_amount) }}</el-descriptions-item>
        <el-descriptions-item label="异常分数">{{ currentSubject.anomaly_score?.toFixed(1) }}</el-descriptions-item>
      </el-descriptions>

      <h4 style="margin-top: 20px">风险因素分析</h4>
      <el-table :data="currentSubject?.risk_factors || []" style="width: 100%">
        <el-table-column prop="name" label="因素" width="150" />
        <el-table-column prop="score" label="分数" width="100">
          <template #default="{ row }">{{ row.score?.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column prop="weight" label="权重" width="100">
          <template #default="{ row }">{{ (row.weight * 100).toFixed(0) }}%</template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="300" show-overflow-tooltip />
      </el-table>

      <h4 style="margin-top: 20px">抽样建议</h4>
      <p>{{ currentSubject?.recommendation }}</p>
    </el-dialog>

    <!-- 交易详情对话框 -->
    <el-dialog v-model="transactionDetailVisible" title="交易风险详情" width="700px">
      <el-descriptions :column="2" border v-if="currentTransaction">
        <el-descriptions-item label="凭证号">{{ currentTransaction.voucher_no }}</el-descriptions-item>
        <el-descriptions-item label="日期">{{ currentTransaction.voucher_date }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ formatAmount(currentTransaction.amount) }}</el-descriptions-item>
        <el-descriptions-item label="科目">{{ currentTransaction.subject_name }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="getRiskType(currentTransaction.risk_level)">{{ getRiskLabel(currentTransaction.risk_level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险分数">{{ currentTransaction.risk_score?.toFixed(1) }}</el-descriptions-item>
        <el-descriptions-item label="交易对手" :span="2">{{ currentTransaction.counterparty || '-' }}</el-descriptions-item>
        <el-descriptions-item label="摘要" :span="2">{{ currentTransaction.description || '-' }}</el-descriptions-item>
      </el-descriptions>

      <h4 style="margin-top: 20px">风险标签</h4>
      <div>
        <el-tag
          v-for="tag in (currentTransaction?.risk_tags || [])"
          :key="tag.code"
          :type="getTagType(tag.severity)"
          style="margin-right: 8px; margin-bottom: 8px"
        >
          {{ tag.name }}
        </el-tag>
        <span v-if="!currentTransaction?.risk_tags?.length" style="color: #909399; font-size: 14px">暂无风险标签</span>
      </div>

      <!-- AI风险分析 -->
      <template v-if="currentTransaction?.ai_analysis?.explanation">
        <h4 style="margin-top: 20px">AI风险分析</h4>
        <div style="background: #fdf6ec; border: 1px solid #faecd8; border-radius: 4px; padding: 12px 15px;">
          <span style="color: #cf8b2e; font-weight: 600;">AI分析：</span>
          <span style="color: #b88230;">{{ currentTransaction.ai_analysis.explanation }}</span>
        </div>
      </template>

      <!-- AI审计关注点 -->
      <template v-if="currentTransaction?.ai_analysis?.audit_attention?.length">
        <h4 style="margin-top: 15px">AI审计建议</h4>
        <div style="background: #fdf6ec; border: 1px solid #faecd8; border-radius: 4px; padding: 12px 15px;">
          <span style="color: #cf8b2e; font-weight: 600;">AI建议：</span>
          <ul style="padding-left: 20px; margin-top: 8px; color: #b88230;">
            <li v-for="(item, index) in currentTransaction.ai_analysis.audit_attention" :key="index" style="margin-bottom: 4px;">
              {{ item }}
            </li>
          </ul>
        </div>
      </template>

      <!-- 风险因素汇总 -->
      <template v-if="currentTransaction?.risk_factors?.length">
        <h4 style="margin-top: 15px">风险因素说明</h4>
        <div style="background: #f5f7fa; padding: 15px; border-radius: 4px;">
          <div v-for="(factor, index) in currentTransaction.risk_factors" :key="index" style="margin-bottom: 8px; color: #606266;">
            {{ index + 1 }}. {{ factor }}
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 风险配置对话框 -->
    <el-dialog v-model="configVisible" title="风险配置" width="800px">
      <el-tabs v-model="configTab">
        <!-- 权重配置 -->
        <el-tab-pane label="权重调整" name="weights">
          <el-form label-width="150px">
            <el-form-item v-for="(value, key) in configWeights" :key="key" :label="getDimensionLabel(key)">
              <el-slider v-model="configWeights[key]" :min="0" :max="100" :format-tooltip="formatPercent" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="saveWeights">保存权重</el-button>
        </el-tab-pane>

        <!-- 阈值配置 -->
        <el-tab-pane label="阈值设置" name="thresholds">
          <el-form label-width="150px">
            <el-form-item label="高风险阈值">
              <el-input-number v-model="configThresholds.high" :min="50" :max="100" />
              <span style="margin-left: 10px">分以上为高风险</span>
            </el-form-item>
            <el-form-item label="中风险阈值">
              <el-input-number v-model="configThresholds.medium" :min="0" :max="70" />
              <span style="margin-left: 10px">分以上为中风险</span>
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="saveThresholds">保存阈值</el-button>
        </el-tab-pane>

        <!-- 规则开关 -->
        <el-tab-pane label="规则开关" name="rules">
          <el-table :data="configRules" style="width: 100%">
            <el-table-column prop="name" label="规则名称" width="150" />
            <el-table-column prop="description" label="说明" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" @change="toggleRule(row)" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 配置模板 -->
        <el-tab-pane label="配置模板" name="templates">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>保存当前配置</template>
                <el-input v-model="templateName" placeholder="模板名称" style="margin-bottom: 10px" />
                <el-button type="primary" @click="saveTemplate" :disabled="!templateName">保存为模板</el-button>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>加载模板</template>
                <el-select v-model="selectedTemplate" placeholder="选择模板" style="width: 100%; margin-bottom: 10px">
                  <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.name" />
                </el-select>
                <el-button type="primary" @click="loadTemplate" :disabled="!selectedTemplate">加载</el-button>
                <el-button @click="deleteTemplate" :disabled="!selectedTemplate" style="margin-left: 10px">删除</el-button>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Setting, Warning, Aim, TrendCharts, DataLine } from '@element-plus/icons-vue'
import { riskApi, projectApi } from '@/api'
import * as echarts from 'echarts'

const router = useRouter()
const loading = ref(false)
const generating = ref(false)
const configVisible = ref(false)
const configTab = ref('weights')
const subjectDetailVisible = ref(false)
const transactionDetailVisible = ref(false)
const activeTab = ref('subjects')
const periodType = ref('monthly')

// 项目相关
const projects = ref([])
const projectId = ref(localStorage.getItem('currentProjectId') || '')

// 概览数据
const overview = ref({})
const highRiskSubjects = ref([])
const profiles = ref([])
const searchKeyword = ref('')

// 多维分析数据
const counterpartyRisks = ref([])
const counterpartyLoading = ref(false)
const timeAnalysis = ref([])
const timeLoading = ref(false)
const timeAnomalies = computed(() =>
  timeAnalysis.value.filter(t => t.anomaly_indicators?.length > 0)
)

// 交易清单数据
const transactionList = ref([])
const transactionTotal = ref(0)
const transactionPage = ref(1)
const transactionPageSize = ref(50)
const transactionLoading = ref(false)
const transactionFilters = ref({
  risk_level: null,
  min_amount: null,
  max_amount: null,
  counterparty: ''
})
const selectedTransactions = ref([])
const currentTransaction = ref(null)

// 分层抽样数据
const layeredData = ref({})
const samplingLoading = ref(false)

// 配置数据
const configWeights = ref({})
const configThresholds = ref({ high: 70, medium: 50 })
const configRules = ref([])
const templates = ref([])
const templateName = ref('')
const selectedTemplate = ref('')

// 当前选中
const currentSubject = ref(null)

// 图表引用
const radarChartRef = ref()
const trendChartRef = ref()
const riskPieChartRef = ref()
const subjectBarChartRef = ref()
const timeChartRef = ref()

// 计算属性
const filteredProfiles = computed(() => {
  if (!searchKeyword.value) return profiles.value
  const keyword = searchKeyword.value.toLowerCase()
  return profiles.value.filter(p =>
    p.subject_code?.toLowerCase().includes(keyword) ||
    p.subject_name?.toLowerCase().includes(keyword)
  )
})

// 工具函数
const formatAmount = (amount) => {
  if (!amount) return '0.00'
  return Number(amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const getRiskType = (level) => {
  const types = { high: 'danger', medium: 'warning', low: 'success' }
  return types[level] || 'info'
}

const getRiskLabel = (level) => {
  const labels = { high: '高风险', medium: '中风险', low: '低风险' }
  return labels[level] || level
}

const getRiskColor = (level) => {
  const colors = { high: '#f56c6c', medium: '#e6a23c', low: '#67c23a' }
  return colors[level] || '#909399'
}

const getScoreColor = (score) => {
  if (score >= 70) return '#f56c6c'
  if (score >= 50) return '#e6a23c'
  return '#67c23a'
}

const getTagType = (severity) => {
  const types = { high: 'danger', medium: 'warning', low: 'info' }
  return types[severity] || 'info'
}

const getDimensionLabel = (key) => {
  const labels = {
    amount_significance: '金额重要性',
    business_complexity: '业务复杂性',
    historical_issues: '历史问题',
    industry_risk: '行业风险',
    anomaly_indicators: '异常指标',
    counterparty_risk: '交易对手风险',
    time_risk: '时间风险',
    document_completeness: '文档完整性'
  }
  return labels[key] || key
}

const formatPercent = (val) => `${val}%`

// 加载项目列表
const loadProjects = async () => {
  try {
    const res = await projectApi.getList({ page: 1, page_size: 100 })
    projects.value = res.items || []

    if (projectId.value) {
      const exists = projects.value.some(p => p.id === projectId.value)
      if (!exists) {
        projectId.value = ''
        localStorage.removeItem('currentProjectId')
      }
    }
  } catch (error) {
    console.error(error)
  }
}

// 项目切换
const onProjectChange = (val) => {
  localStorage.setItem('currentProjectId', val)
  overview.value = {}
  profiles.value = []
  highRiskSubjects.value = []
  counterpartyRisks.value = []
  timeAnalysis.value = []
  transactionList.value = []
  layeredData.value = {}
  loadAllData()
}

// 加载所有数据
const loadAllData = async () => {
  if (!projectId.value) return

  loading.value = true
  try {
    await Promise.all([
      loadOverview(),
      loadProfiles(),
      loadHighRiskSubjects()
    ])
    nextTick(() => {
      renderCharts()
    })
  } finally {
    loading.value = false
  }
}

// 加载概览
const loadOverview = async () => {
  try {
    const res = await riskApi.getOverview(projectId.value)
    overview.value = res || {}
  } catch (error) {
    console.error(error)
  }
}

// 加载科目画像
const loadProfiles = async () => {
  try {
    const res = await riskApi.getSubjects(projectId.value)
    profiles.value = res || []
  } catch (error) {
    console.error(error)
  }
}

// 加载高风险科目
const loadHighRiskSubjects = async () => {
  try {
    const res = await riskApi.getHighRiskSubjects(projectId.value, 5)
    highRiskSubjects.value = res || []
  } catch (error) {
    console.error(error)
  }
}

// 加载交易对手分析
const loadCounterpartyAnalysis = async () => {
  counterpartyLoading.value = true
  try {
    const res = await riskApi.getCounterpartyAnalysis(projectId.value)
    counterpartyRisks.value = res || []
  } catch (error) {
    console.error(error)
  } finally {
    counterpartyLoading.value = false
  }
}

// 加载时间分析
const loadTimeAnalysis = async () => {
  timeLoading.value = true
  try {
    const res = await riskApi.getTimeAnalysis(projectId.value, periodType.value)
    timeAnalysis.value = res || []
    nextTick(() => {
      renderTimeChart()
    })
  } catch (error) {
    console.error(error)
  } finally {
    timeLoading.value = false
  }
}

// 加载交易清单
const loadTransactions = async () => {
  transactionLoading.value = true
  try {
    const params = {
      page: transactionPage.value,
      page_size: transactionPageSize.value,
      ...transactionFilters.value
    }
    // 移除空值
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '' || params[key] === undefined) {
        delete params[key]
      }
    })

    const res = await riskApi.getTransactionList(projectId.value, params)
    transactionList.value = res.items || []
    transactionTotal.value = res.total || 0
  } catch (error) {
    console.error(error)
  } finally {
    transactionLoading.value = false
  }
}

// 加载分层抽样建议
const loadLayeredSampling = async () => {
  samplingLoading.value = true
  try {
    const res = await riskApi.getLayeredSampling(projectId.value)
    layeredData.value = res || {}
  } catch (error) {
    console.error(error)
  } finally {
    samplingLoading.value = false
  }
}

// 生成风险画像
const generateAllProfiles = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  // 弹出选择框
  const result = await ElMessageBox.confirm(
    '请选择风险画像生成模式：\n\n• AI增强模式：使用大模型智能分析，更准确但耗时较长（约2-3分钟）\n• 快速模式：仅使用规则引擎，速度快但分析深度有限',
    '生成风险画像',
    {
      distinguishCancelAndClose: true,
      confirmButtonText: 'AI增强模式',
      cancelButtonText: '快速模式',
      type: 'info'
    }
  ).then(() => true)  // 点击确认 = AI模式
    .catch((action) => {
      if (action === 'cancel') return false  // 点击取消 = 快速模式
      return null  // 点击关闭 = 取消操作
    })

  if (result === null) return  // 用户关闭了对话框

  const useAi = result

  generating.value = true
  const startTime = Date.now()
  try {
    // 先生成科目画像
    ElMessage.info(useAi ? '正在使用AI增强分析，请耐心等待...' : '正在生成风险画像...')
    await riskApi.generateSubjects(projectId.value, useAi)
    // 再生成概览
    await riskApi.generateOverview(projectId.value)

    const elapsed = Math.round((Date.now() - startTime) / 1000)
    ElMessage.success(`风险画像生成成功，耗时${elapsed}秒`)
    loadAllData()
  } catch (error) {
    console.error(error)
    ElMessage.error('生成失败')
  } finally {
    generating.value = false
  }
}

// Tab切换
const onTabChange = (tab) => {
  if (tab === 'counterparty' && counterpartyRisks.value.length === 0) {
    loadCounterpartyAnalysis()
  } else if (tab === 'time' && timeAnalysis.value.length === 0) {
    loadTimeAnalysis()
  } else if (tab === 'transactions' && transactionList.value.length === 0) {
    loadTransactions()
  } else if (tab === 'sampling' && !layeredData.value.total_sample_size) {
    loadLayeredSampling()
  }
}

// 渲染图表
const renderCharts = () => {
  renderRadarChart()
  renderTrendChart()
  renderRiskPieChart()
  renderSubjectBarChart()
}

// 渲染雷达图
const renderRadarChart = () => {
  if (!radarChartRef.value) return
  const chart = registerChart(radarChartRef.value)
  const dimensionScores = overview.value.dimension_scores || {}

  chart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: [
        { name: '金额重要性', max: 100 },
        { name: '业务复杂性', max: 100 },
        { name: '历史问题', max: 100 },
        { name: '行业风险', max: 100 },
        { name: '异常指标', max: 100 }
      ],
      radius: 65,
      center: ['50%', '55%'],
      splitNumber: 4,
      axisName: {
        color: '#606266',
        fontSize: 12
      },
      splitArea: {
        areaStyle: {
          color: ['#fff', '#f5f7fa']
        }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [
          dimensionScores['金额重要性'] || 50,
          dimensionScores['业务复杂性'] || 50,
          dimensionScores['历史问题'] || 50,
          dimensionScores['行业风险'] || 50,
          dimensionScores['异常指标'] || 50
        ],
        name: '风险维度',
        symbol: 'circle',
        symbolSize: 6,
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.2)' }
            ]
          }
        },
        lineStyle: {
          color: '#409eff',
          width: 2
        },
        itemStyle: {
          color: '#409eff'
        }
      }]
    }]
  })
}

// 渲染趋势图
const renderTrendChart = () => {
  if (!trendChartRef.value) return
  const chart = registerChart(trendChartRef.value)
  const trend = overview.value.risk_trend || []

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: { color: '#303133' }
    },
    grid: {
      top: 30,
      left: 40,
      right: 20,
      bottom: 35
    },
    xAxis: {
      type: 'category',
      data: trend.map(t => t.date || ''),
      axisLabel: { fontSize: 11, color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { fontSize: 11, color: '#909399' },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#ebeef5', type: 'dashed' } }
    },
    series: [{
      type: 'line',
      data: trend.map(t => t.score || 0),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        color: '#409eff',
        width: 2
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ]
        }
      },
      itemStyle: { color: '#409eff' }
    }]
  })
}

// 渲染风险分布饼图
const renderRiskPieChart = () => {
  if (!riskPieChartRef.value) return
  const chart = echarts.init(riskPieChartRef.value)
  const riskCounts = { high: 0, medium: 0, low: 0 }
  profiles.value.forEach(p => {
    riskCounts[p.risk_level] = (riskCounts[p.risk_level] || 0) + 1
  })

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      data: [
        { value: riskCounts.high, name: '高风险', itemStyle: { color: '#f56c6c' } },
        { value: riskCounts.medium, name: '中风险', itemStyle: { color: '#e6a23c' } },
        { value: riskCounts.low, name: '低风险', itemStyle: { color: '#67c23a' } }
      ]
    }]
  })
}

// 渲染科目柱状图
const renderSubjectBarChart = () => {
  if (!subjectBarChartRef.value) return
  const chart = echarts.init(subjectBarChartRef.value)
  const topProfiles = profiles.value.slice(0, 10)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: topProfiles.map(p => p.subject_name?.slice(0, 6) || ''),
      axisLabel: { interval: 0, rotate: 30, fontSize: 10 }
    },
    yAxis: { type: 'value', max: 100 },
    series: [{
      type: 'bar',
      data: topProfiles.map(p => ({
        value: p.risk_score,
        itemStyle: { color: getRiskColor(p.risk_level) }
      }))
    }]
  })
}

// 渲染时间图表
const renderTimeChart = () => {
  if (!timeChartRef.value) return
  const chart = echarts.init(timeChartRef.value)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['金额', '波动分数'] },
    xAxis: {
      type: 'category',
      data: timeAnalysis.value.map(t => t.period),
      axisLabel: { fontSize: 10, rotate: 30 }
    },
    yAxis: [
      { type: 'value', name: '金额' },
      { type: 'value', name: '波动分数', max: 100 }
    ],
    series: [
      {
        name: '金额',
        type: 'bar',
        data: timeAnalysis.value.map(t => t.total_amount)
      },
      {
        name: '波动分数',
        type: 'line',
        yAxisIndex: 1,
        data: timeAnalysis.value.map(t => t.volatility_score)
      }
    ]
  })
}

// 查看科目详情
const viewSubjectDetail = (row) => {
  currentSubject.value = row
  subjectDetailVisible.value = true
}

// 下钻科目
const drillDownSubject = (row) => {
  currentSubject.value = profiles.value.find(p => p.subject_code === row.subject_code) || row
  subjectDetailVisible.value = true
}

// 跳转抽样
const goToSampling = (row) => {
  router.push({
    path: '/sampling/strategy',
    query: { subject_code: row.subject_code }
  })
}

// 搜索交易
const searchTransactions = () => {
  transactionPage.value = 1
  loadTransactions()
}

// 重置筛选
const resetTransactionFilters = () => {
  transactionFilters.value = {
    risk_level: null,
    min_amount: null,
    max_amount: null,
    counterparty: ''
  }
  transactionPage.value = 1
  loadTransactions()
}

// 选择交易
const handleTransactionSelection = (selection) => {
  selectedTransactions.value = selection
}

// 查看交易详情
const viewTransactionDetail = (row) => {
  currentTransaction.value = row
  transactionDetailVisible.value = true
}

// 批量加入抽样
const batchAddToSampling = async () => {
  if (selectedTransactions.value.length === 0) return

  try {
    const ids = selectedTransactions.value.map(t => t.id)
    await riskApi.batchAddToSampling(projectId.value, ids)
    ElMessage.success(`成功添加${ids.length}条凭证到抽样清单`)
    selectedTransactions.value = []
  } catch (error) {
    console.error(error)
    ElMessage.error('操作失败')
  }
}

// 执行分层抽样
const executeLayeredSampling = async () => {
  if (!projectId.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  if (!layeredData.value.total_sample_size) {
    ElMessage.warning('没有可抽样的凭证')
    return
  }

  // 弹出模式选择框
  const modeResult = await ElMessageBox.confirm(
    '请选择分层抽样模式：\n\n• AI增强模式：使用AI重新分析凭证风险后再抽样，更准确但耗时较长\n• 规则模式：直接使用现有风险等级进行随机抽样，速度快',
    '执行分层抽样',
    {
      distinguishCancelAndClose: true,
      confirmButtonText: 'AI增强模式',
      cancelButtonText: '规则模式',
      type: 'info'
    }
  ).then(() => 'ai')  // 点击确认 = AI模式
    .catch((action) => {
      if (action === 'cancel') return 'rule'  // 点击取消 = 规则模式
      return null  // 点击关闭 = 取消操作
    })

  if (modeResult === null) return  // 用户关闭了对话框

  const useAi = modeResult === 'ai'

  // 二次确认
  const totalSamples = layeredData.value.total_sample_size
  try {
    await ElMessageBox.confirm(
      useAi
        ? `确定要执行AI增强分层抽样吗？\n\nAI将重新分析凭证风险后再进行分层抽样，预计抽取样本约 ${totalSamples} 笔。`
        : `确定要执行规则分层抽样吗？预计抽取 ${totalSamples} 笔样本。`,
      '确认执行',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
  } catch {
    return  // 用户取消
  }

  samplingLoading.value = true
  try {
    // 获取分层抽样建议中的比例参数
    const highRatio = layeredData.value.layers?.find(l => l.level === 'high')?.ratio || 1.0
    const mediumRatio = layeredData.value.layers?.find(l => l.level === 'medium')?.ratio || 0.3
    const lowRatio = layeredData.value.layers?.find(l => l.level === 'low')?.ratio || 0.05

    if (useAi) {
      ElMessage.info('正在使用AI分析凭证风险，请耐心等待...')
    }

    const result = await riskApi.executeLayeredSampling(
      projectId.value,
      highRatio,
      mediumRatio,
      lowRatio,
      useAi
    )

    ElMessage.success(result.message || '分层抽样执行成功')

    // 显示抽样结果摘要
    ElMessageBox.alert(
      `抽样完成！\n\n` +
      `• 高风险样本：${result.high_risk_count} 笔\n` +
      `• 中风险样本：${result.medium_risk_count} 笔\n` +
      `• 低风险样本：${result.low_risk_count} 笔\n` +
      `• 总样本量：${result.total_sample_size} 笔\n\n` +
      (useAi ? '（使用AI增强模式）' : '（使用规则模式）'),
      '抽样结果',
      {
        confirmButtonText: '查看抽样清单',
        type: 'success'
      }
    ).then(() => {
      // 跳转到抽样清单页面
      router.push('/sampling/results')
    }).catch(() => {
      // 用户关闭对话框，不做任何操作
    })

    // 重新加载分层抽样建议以更新数据
    await loadLayeredSampling()
  } catch (error) {
    console.error(error)
    ElMessage.error(error.response?.data?.detail || '执行分层抽样失败')
  } finally {
    samplingLoading.value = false
  }
}

// 打开配置
const openRiskConfig = async () => {
  configVisible.value = true
  configTab.value = 'weights'

  // 加载配置
  try {
    const [weights, thresholds, rules, tmpl] = await Promise.all([
      riskApi.getWeights(projectId.value),
      riskApi.getThresholds(projectId.value),
      riskApi.getRules(projectId.value),
      riskApi.getTemplates(projectId.value)
    ])

    configWeights.value = weights || {}
    configThresholds.value = thresholds || { high: 70, medium: 50 }
    configRules.value = rules || []
    templates.value = tmpl || []
  } catch (error) {
    console.error(error)
  }
}

// 保存权重
const saveWeights = async () => {
  try {
    await riskApi.updateWeights(projectId.value, configWeights.value)
    ElMessage.success('权重配置保存成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败')
  }
}

// 保存阈值
const saveThresholds = async () => {
  try {
    await riskApi.updateThresholds(projectId.value, configThresholds.value)
    ElMessage.success('阈值配置保存成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败')
  }
}

// 切换规则
const toggleRule = async (row) => {
  try {
    await riskApi.toggleRule(projectId.value, row.code, row.enabled)
    ElMessage.success(`${row.name}已${row.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error(error)
    row.enabled = !row.enabled
  }
}

// 保存模板
const saveTemplate = async () => {
  if (!templateName.value) return

  try {
    await riskApi.saveTemplate(projectId.value, templateName.value)
    ElMessage.success('模板保存成功')
    templateName.value = ''
    // 刷新模板列表
    templates.value = await riskApi.getTemplates(projectId.value)
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败')
  }
}

// 加载模板
const loadTemplate = async () => {
  if (!selectedTemplate.value) return

  try {
    await riskApi.loadTemplate(projectId.value, selectedTemplate.value)
    ElMessage.success('模板加载成功')
    openRiskConfig() // 重新加载配置
  } catch (error) {
    console.error(error)
    ElMessage.error('加载失败')
  }
}

// 删除模板
const deleteTemplate = async () => {
  if (!selectedTemplate.value) return

  try {
    await riskApi.deleteTemplate(projectId.value, selectedTemplate.value)
    ElMessage.success('模板删除成功')
    selectedTemplate.value = ''
    templates.value = await riskApi.getTemplates(projectId.value)
  } catch (error) {
    console.error(error)
    ElMessage.error('删除失败')
  }
}

// 图表实例缓存
const chartInstances = ref([])

// 窗口resize处理
const handleResize = () => {
  chartInstances.value.forEach(chart => {
    if (chart) chart.resize()
  })
}

// 注册图表实例
const registerChart = (ref) => {
  if (ref) {
    const chart = echarts.getInstanceByDom(ref) || echarts.init(ref)
    if (!chartInstances.value.includes(chart)) {
      chartInstances.value.push(chart)
    }
    return chart
  }
  return null
}

onMounted(() => {
  loadProjects()
  if (projectId.value) {
    loadAllData()
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstances.value.forEach(chart => {
    if (chart) chart.dispose()
  })
})
</script>

<style scoped>
/* 覆盖页面容器边距，参考凭证管理页面 */
.page-container {
  padding: 24px !important;
  max-width: none !important;
  margin: 0 !important;
}

/* 表格横向滚动容器 */
.table-scroll-wrapper {
  width: 100%;
  overflow: auto;
  max-height: 600px;
}

.table-scroll-wrapper::-webkit-scrollbar {
  height: 10px;
  width: 10px;
}

.table-scroll-wrapper::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 5px;
}

.table-scroll-wrapper::-webkit-scrollbar-track {
  background: #f1f1f1;
}

/* 风险标签换行显示 */
.risk-tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  line-height: 1.8;
}

.risk-tags-wrap .el-tag {
  flex-shrink: 0;
}

/* 风险因素单元格格式化 */
.risk-factors-cell {
  line-height: 1.6;
  font-size: 13px;
}

.ai-analysis-section {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 4px;
  padding: 8px 10px;
}

.ai-explanation {
  color: #b88230;
  line-height: 1.5;
  word-break: break-word;
}

.ai-explanation .ai-label,
.ai-attention .ai-label {
  font-weight: 600;
  color: #cf8b2e;
}

.ai-explanation .ai-content {
  display: block;
  margin-top: 4px;
  word-break: break-word;
  white-space: normal;
}

.ai-attention {
  margin-top: 8px;
}

.ai-attention .attention-list {
  margin: 4px 0 0 0;
  padding-left: 16px;
  color: #b88230;
}

.ai-attention .attention-list li {
  margin-bottom: 2px;
  line-height: 1.4;
  word-break: break-word;
  white-space: normal;
}

.no-data {
  color: #909399;
}

/* 交易对手表格单元格自动换行 */
.counterparty-table .el-table__body .el-table__cell .cell {
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
}

/* 概览区域布局 */
.overview-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

/* 统一卡片样式 */
.overview-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: box-shadow 0.3s ease;
}

.overview-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  border-bottom: 1px solid #ebeef5;
}

.header-icon {
  font-size: 20px;
  color: #409eff;
  margin-right: 10px;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

/* 卡片内容 */
.card-body {
  padding: 20px;
  height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

/* 图表容器 */
.chart-container {
  width: 100%;
  height: 100%;
}

/* ===== 整体风险评分卡片 ===== */
.score-card .card-body {
  flex-direction: column;
  gap: 16px;
}

.score-gauge {
  display: flex;
  justify-content: center;
  align-items: center;
}

.score-number {
  display: block;
  font-size: 32px;
  font-weight: bold;
  color: #303133;
}

.score-unit {
  display: block;
  font-size: 14px;
  color: #909399;
  margin-top: 2px;
}

.score-footer {
  display: flex;
  justify-content: center;
}

/* ===== 高风险科目TOP5卡片 ===== */
.top-card .card-body {
  align-items: stretch;
  justify-content: flex-start;
  padding: 16px 20px;
  overflow-y: auto;
}

.top-list {
  width: 100%;
}

.top-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px dashed #ebeef5;
}

.top-item:last-child {
  border-bottom: none;
}

.top-rank {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  font-weight: bold;
  color: #fff;
  margin-right: 12px;
}

.top-rank.rank-1 {
  background: linear-gradient(135deg, #f56c6c 0%, #c45656 100%);
}

.top-rank.rank-2 {
  background: linear-gradient(135deg, #e6a23c 0%, #cf9236 100%);
}

.top-rank.rank-3 {
  background: linear-gradient(135deg, #ffd666 0%, #d4b05a 100%);
  color: #606266;
}

.top-rank.rank-4,
.top-rank.rank-5 {
  background: linear-gradient(135deg, #909399 0%, #7d8085 100%);
}

.top-info {
  flex: 1;
  min-width: 0;
}

.top-name {
  font-size: 14px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.top-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.top-score {
  font-size: 13px;
  font-weight: 600;
}

.top-action {
  flex-shrink: 0;
}

/* ===== 风险趋势卡片 ===== */
.trend-card .card-body {
  padding: 16px 20px;
}

/* 响应式适配 */
@media (max-width: 1400px) {
  .overview-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 800px) {
  .overview-section {
    grid-template-columns: 1fr;
  }
}
</style>