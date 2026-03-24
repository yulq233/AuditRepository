# AI审计抽凭助手 - 产品需求文档 (PRD)

## 一、项目概述

### 1.1 背景与目标
审计抽凭是审计工作的核心环节，传统方式依赖人工从海量凭证中随机抽取或按规则抽取，效率低下。本项目旨在构建一个AI驱动的智能抽凭助手，通过大语言模型理解凭证内容，实现智能化的抽样审计。

### 1.2 核心功能
1. **数据采集**：从公共审计平台爬取测试数据 + 文件导入实际凭证
2. **AI智能抽凭**：基于规则抽凭 + LLM理解凭证语义进行智能抽凭
3. **多端访问**：支持Web后台管理 + 移动端小程序
4. **智能抽样**：风险画像生成、抽样策略推荐、参数可视化调整
5. **多模态凭证处理**：全格式解析、OCR关键信息提取、智能分类索引
6. **自动化核对与预警**：三单匹配自动化、合规性检查、交叉验证
7. **工作流与底稿**：任务分派、底稿生成、审计轨迹留痕

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                  │
│  ┌─────────────────┐              ┌─────────────────┐           │
│  │   Web管理后台    │              │  移动端(uni-app) │           │
│  │   (Vue/React)   │              │  (微信/小程序)    │           │
│  └────────┬────────┘              └────────┬────────┘           │
└───────────┼───────────────────────────────┼─────────────────────┘
            │                               │
            └───────────┬───────────────────┘
                        │ HTTP/WebSocket
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API网关层                                 │
│                    (FastAPI + CORS中间件)                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  凭证管理模块  │    │   抽凭模块     │    │  爬虫模块     │
│  - 文件导入    │    │  - 规则引擎    │    │  - 平台爬取   │
│  - 数据存储    │    │  - AI智能抽凭  │    │  - 文档下载   │
│  - 查询检索    │    │  - 风险画像    │    │  - 数据清洗   │
│  - 多模态处理  │    │  - 策略推荐    │    │               │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                     │                     │
┌───────┴───────┐    ┌───────┴───────┐    ┌───────┴───────┐
│  核对预警模块  │    │  工作流模块     │    │  底稿生成模块  │
│  - 三单匹配    │    │  - 任务分派     │    │  - 智能摘要   │
│  - 合规检查    │    │  - 进度追踪     │    │  - 报告生成   │
│  - 交叉验证    │    │  - 审计轨迹     │    │  - 导出归档   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       数据服务层                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    DuckDB (嵌入式OLAP)                    │   │
│  │  - 凭证表(vouchers)    - 项目表(projects)                 │   │
│  │  - 抽凭记录表(samples) - 规则表(rules)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    文件存储 (本地/OSS)                    │   │
│  │  - 凭证附件(PDF/图片)  - 爬取文档                          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       AI服务层 (可切换)                          │
│  ┌─────────────────────┐      ┌─────────────────────┐          │
│  │   本地模型 (Ollama)  │      │   商业API (国内)     │          │
│  │   - Qwen/Llama      │      │   - 百度文心一言     │          │
│  │   - 离线可用        │      │   - 阿里通义千问     │          │
│  └─────────────────────┘      │   - 智谱GLM         │          │
│                              └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、技术选型

| 层级 | 技术方案 | 说明 |
|------|---------|------|
| 后端框架 | FastAPI | Python异步框架，高性能，易用 |
| 数据库 | DuckDB | 轻量级嵌入式分析数据库，适合审计场景 |
| AI集成 | LangChain | 统一接口，支持多种LLM切换 |
| 爬虫 | Playwright + Scrapy | 动态页面+结构化采集 |
| 移动端 | uni-app | Vue语法，跨平台(微信/支付宝/H5/App) |
| 文件存储 | 本地磁盘 + 阿里云OSS | 凭证附件存储 |
| OCR识别 | PaddleOCR / EasyOCR | 高精度中文识别，支持多种格式 |
| 向量数据库 | Milvus / Qdrant | (可选)凭证语义检索 |

---

## 四、核心模块设计

### 4.1 凭证管理模块

**功能**：
- 支持Excel/CSV导入凭证数据
- 凭证数据CRUD
- 凭证附件上传与管理
- 凭证检索与筛选

**数据结构**：

```python
# 凭证表 (vouchers)
class Voucher:
    id: str                    # 主键
    project_id: str            # 所属项目
    voucher_no: str            # 凭证编号
    voucher_date: date         # 凭证日期
    amount: float              # 金额
    subject_code: str          # 科目代码
    subject_name: str          # 科目名称
    description: str           # 凭证摘要
    attachment_path: str       # 附件路径
    raw_data: dict             # 原始数据(JSON)
    created_at: datetime
    updated_at: datetime
```

### 4.2 抽凭规则引擎

**功能**：
- 预定义抽凭规则模板
- 自定义抽凭规则
- 规则组合与条件判断
- 规则执行日志

**内置规则**：
1. **随机抽样**：按比例随机抽取n%凭证
2. **金额阈值**：抽取大于/小于某金额的凭证
3. **科目筛选**：按会计科目筛选
4. **日期范围**：按时间段筛选
5. **异常检测**：AI识别异常凭证

### 4.3 AI智能抽凭模块

**功能**：
- 凭证语义理解（摘要、科目、金额）
- 风险评估与重要性判断
- 智能推荐抽样
- 抽凭结果解释

**工作流程**：

```
1. 输入：凭证列表 + 抽凭要求
2. 向量化：使用Embedding模型将凭证文本向量化
3. 理解：LLM分析凭证内容，识别风险点
4. 评估：计算每张凭证的风险分数
5. 抽样：根据风险分数排序，按策略抽取
6. 输出：抽样结果 + 风险说明
```

### 4.4 爬虫模块

**功能**：
- 公共审计平台数据采集
- 按项目维度爬取
- 凭证文档下载
- 数据清洗与格式化

**架构**：

```python
# 爬虫基类
class BaseCrawler:
    def login(self)           # 登录认证
    def list_projects(self)   # 获取项目列表
    def get_vouchers()        # 获取凭证列表
    def download_attachment() # 下载附件
    def cleanup()             # 清理资源

# 具体实现
class AuditPlatformCrawler(BaseCrawler):
    # 实现具体平台的爬取逻辑
```

---

## 五、智能抽样模块

### 5.1 风险画像生成

**功能**：基于财报数据、科目属性、历史问题，自动评估科目风险等级。

**数据结构**：

```python
# 风险画像模型
class RiskProfile:
    subject_code: str              # 科目代码
    subject_name: str             # 科目名称
    risk_level: str                # 风险等级 (high/medium/low)
    risk_factors: List[str]        # 风险因素列表
    material_amount: float         # 重要金额阈值
    anomaly_score: float           # 异常分数 (0-100)
    historical_issues: List[dict]  # 历史问题记录
    recommendation: str            # 抽样建议

# 风险评估输入
class RiskAssessmentInput:
    project_id: str
    financial_statements: dict     # 财报数据
    subject_balances: List[dict]   # 科目余额表
    historical_problems: List[dict] # 历史审计问题
    industry_risks: List[str]      # 行业特定风险
```

**评估维度**：
| 维度 | 指标 | 权重 |
|------|------|------|
| 金额重要性 | 科目余额占比、变动幅度 | 25% |
| 业务复杂性 | 交易笔数、对手方数量 | 20% |
| 历史问题 | 以前年度审计发现 | 20% |
| 行业风险 | 行业特性风险点 | 15% |
| 异常指标 | 波动率、异常交易模式 | 20% |

### 5.2 抽样策略推荐

**功能**：根据风险等级，推荐统计抽样或判断抽样的方法、样本量及抽样依据。

**推荐算法**：

```python
class SamplingStrategyRecommender:
    def recommend(self, risk_profile: RiskProfile,
                   confidence_level: float = 0.95,
                   tolerable_error: float = 0.05) -> SamplingStrategy:
        """根据风险画像推荐抽样策略"""
        if risk_profile.risk_level == "high":
            return self._recommend_judgment_sampling(risk_profile)
        elif risk_profile.risk_level == "medium":
            return self._recommend_mixed_sampling(risk_profile)
        else:
            return self._recommend_statistical_sampling(
                risk_profile, confidence_level, tolerable_error
            )

    def _recommend_statistical_sampling(self, risk_profile, confidence, error):
        """统计抽样推荐"""
        # 样本量计算公式: n = (Z² × p × (1-p)) / e²
        # Z: 置信水平对应z值
        # p: 预期偏差率
        # e: 可容忍误差
        ...

    def _recommend_judgment_sampling(self, risk_profile):
        """判断抽样推荐"""
        # 基于风险因素确定重点抽样范围
        # 金额大于XX元
        # 特定交易对方
        # 异常模式匹配
        ...
```

**抽样方法映射**：
| 风险等级 | 推荐方法 | 样本量 | 依据 |
|---------|---------|-------|------|
| 高 | 判断抽样 | 100%或重点抽取 | 金额>50万、异常模式 |
| 中 | 分层抽样 | 20-30% | 金额分层+风险分层 |
| 低 | 随机抽样 | 10-15% | 统计公式计算 |

### 5.3 参数可视化调整

**功能**：审计师可直观调整置信水平、可容忍误差等参数，实时查看样本量变化。

**前端交互设计**：
```
┌────────────────────────────────────────────┐
│  置信水平: [██████░░] 95%                   │
│  可容忍误差: [████░░░░] 5%                   │
│  预期偏差率: [██░░░░░░] 10%                  │
│                                            │
│  预估样本量: 168 张                          │
│                                            │
│  ┌─────────────────────────────────────┐   │
│  │         样本量-置信度曲线            │   │
│  │    ●                          ●    │   │
│  │        ●                    ●       │   │
│  │           ●              ●          │   │
│  │              ●     ●                │   │
│  │                 ●                    │   │
│  └─────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

---

## 六、多模态凭证处理模块

### 6.1 全格式解析

**支持格式**：
- 扫描件：PDF扫描件、JPG/PNG/BMP图片
- 照片：手机拍摄凭证照片（自动校正畸变）
- PDF：数字PDF + 扫描PDF
- Excel：财务系统导出格式
- 结构化数据：CSV、JSON、XML

**处理流程**：
```
上传文件 → 格式检测 → 预处理 → OCR识别 → 信息提取 → 结构化存储
```

### 6.2 OCR与关键信息提取

**提取字段**：
| 字段类型 | 说明 | 提取方式 |
|---------|------|---------|
| 凭证号 | 凭证唯一编号 | 正则匹配 |
| 日期 | 凭证日期 | NLP日期解析 |
| 金额 | 金额（中文/数字） | OCR+数字识别 |
| 交易对手 | 供应商/客户名称 | NLP实体识别 |
| 摘要 | 业务描述 | OCR+语义理解 |
| 审批签章 | 审批人、签章位置 | 图像识别 |

**OCR服务架构**：

```python
class OCRService:
    def __init__(self, provider: str = "paddleocr"):
        self.provider = provider

    def extract(self, file_path: str) -> OCRResult:
        """提取凭证关键信息"""
        image = self._preprocess(file_path)
        text_blocks = self._ocr_recognize(image)
        structured_data = self._extract_fields(text_blocks)
        return OCRResult(
            voucher_no=structured_data.get("voucher_no"),
            date=structured_data.get("date"),
            amount=structured_data.get("amount"),
            counterparty=structured_data.get("counterparty"),
            description=structured_data.get("description"),
            signatures=structured_data.get("signatures"),
            confidence=structured_data.get("confidence"),
            raw_text=text_blocks
        )

    def _preprocess(self, image):
        """图像预处理"""
        # 灰度化、降噪、倾斜校正、增强
        ...

    def _extract_fields(self, text_blocks):
        """字段提取"""
        # 使用正则+NLP提取关键字段
        ...
```

### 6.3 智能分类与索引

**分类维度**：
- **凭证类型**：发票、合同、银行回单、收据、审批单
- **会计科目**：按科目代码自动归类
- **业务类型**：采购、销售、费用、资产、负债
- **风险标签**：高风险、异常、需关注

**索引构建**：

```python
class VoucherIndexer:
    def __init__(self, vector_db=None):
        self.vector_db = vector_db  # 可选向量数据库

    def index(self, voucher: Voucher, ocr_result: OCRResult):
        """建立凭证索引"""
        # 1. 结构化索引
        self._build_structured_index(voucher)

        # 2. 向量索引 (可选)
        if self.vector_db:
            self._build_vector_index(voucher, ocr_result)

        # 3. 分类标签
        self._assign_category(voucher, ocr_result)

    def search(self, query: str, filters: dict = None) -> List[Voucher]:
        """语义搜索凭证"""
        # 支持关键词 + 语义搜索
        ...

    def _build_vector_index(self, voucher, ocr_result):
        """构建向量索引用于语义搜索"""
        # 将凭证文本向量化存储
        # 支持"找出所有办公费用发票"等语义查询
        ...
```

---

## 七、自动化核对与预警模块

### 7.1 "三单匹配"自动化

**功能**：自动将采购发票、采购订单与入库单的关键信息进行核对，标记差异。

**核对逻辑**：

```python
class ThreeWayMatcher:
    """三单匹配：发票 - 订单 - 入库单"""

    def match(self, invoices: List[Voucher],
              orders: List[Voucher],
              receipts: List[Voucher]) -> MatchResult:
        """执行三单匹配"""
        results = []

        for invoice in invoices:
            # 1. 按关键字段匹配
            matched_order = self._find_matching_order(invoice, orders)
            matched_receipt = self._find_matching_receipt(invoice, receipts)

            # 2. 比对金额差异
            differences = self._compare_amounts(
                invoice, matched_order, matched_receipt
            )

            # 3. 生成匹配结果
            result = MatchResult(
                invoice_id=invoice.id,
                order_id=matched_order.id if matched_order else None,
                receipt_id=matched_receipt.id if matched_receipt else None,
                match_status=self._determine_status(differences),
                differences=differences,
                suggestions=self._generate_suggestions(differences)
            )
            results.append(result)

        return results

    def _find_matching_order(self, invoice, orders):
        """查找匹配的订单"""
        # 匹配规则：供应商+金额+日期相近
        for order in orders:
            if (order.supplier == invoice.supplier and
                self._amount_similar(invoice.amount, order.amount) and
                self._date_within_range(invoice.date, order.date, 30)):
                return order
        return None
```

**匹配结果状态**：
| 状态 | 说明 | 颜色标识 |
|------|------|---------|
| 完全匹配 | 三单金额、日期完全一致 | 🟢 绿色 |
| 部分匹配 | 部分单据匹配，存在差异 | 🟡 黄色 |
| 未匹配 | 无法找到匹配单据 | 🔴 红色 |

### 7.2 合规性检查

**预设规则**：

```python
class ComplianceChecker:
    """合规性检查规则"""

    RULES = {
        "budget_exceed": {
            "name": "预算超标",
            "description": "超预算支出检查",
            "check": lambda v: v.amount > v.budget_limit
        },
        "approval_missing": {
            "name": "审批流程不全",
            "description": "缺少必要的审批签字",
            "check": lambda v: not v.has_approval
        },
        "sequential_invoices": {
            "name": "连号发票",
            "description": "检查异常连号发票",
            "check": lambda v: self._check_sequence(v)
        },
        " weekend_transactions": {
            "name": "周末大额交易",
            "description": "周末异常大额支出",
            "check": lambda v: v.is_weekend and v.amount > 100000
        },
        "cash_exceed": {
            "name": "现金超限",
            "description": "现金支付超过规定限额",
            "check": lambda v: v.payment_method == "cash" and v.amount > 1000
        }
    }

    def check(self, vouchers: List[Voucher]) -> List[ComplianceAlert]:
        """执行所有合规检查"""
        alerts = []
        for voucher in vouchers:
            for rule_name, rule in self.RULES.items():
                if rule["check"](voucher):
                    alerts.append(ComplianceAlert(
                        voucher_id=voucher.id,
                        rule=rule_name,
                        severity=self._get_severity(rule_name),
                        message=rule["description"]
                    ))
        return alerts
```

### 7.3 交叉验证

**验证数据源**：
- 银行对账单/流水
- 纳税申报表
- 合同台账
- 库存盘点记录

```python
class CrossValidator:
    """交叉验证"""

    def validate(self, voucher: Voucher,
                 bank_statements: List[dict],
                 tax_returns: List[dict]) -> ValidationResult:
        """交叉验证凭证与外部数据"""
        validations = []

        # 1. 银行流水勾稽
        bank_match = self._check_bank_reconciliation(
            voucher, bank_statements
        )
        validations.append(bank_match)

        # 2. 纳税申报勾稽
        tax_match = self._check_tax_reconciliation(
            voucher, tax_returns
        )
        validations.append(tax_match)

        return ValidationResult(
            voucher_id=voucher.id,
            is_valid=all(v.passed for v in validations),
            details=validations
        )
```

---

## 八、工作流管理与底稿生成模块

### 8.1 任务分派与追踪

**功能**：将抽样样本自动分派给项目组成员，实时追踪抽凭进度。

**工作流状态**：

```
待分派 → 已分派 → 进行中 → 待复核 → 已完成
                ↓
              [超时/阻塞] → 重新分派
```

**数据结构**：

```python
class AuditTask:
    id: str
    project_id: str
    sample_ids: List[str]          # 抽凭样本ID列表
    assignee_id: str                # 被分派人
    assignee_name: str
    status: str                    # pending/assigned/in_progress/review/completed
    deadline: datetime             # 截止日期
    priority: str                  # high/medium/low
    progress: int                  # 进度百分比
    created_at: datetime
    started_at: datetime
    completed_at: datetime

class TaskProgress:
    """实时进度追踪"""
    project_id: str
    total_samples: int
    completed: int
    in_progress: int
    pending: int
    overdue: int
    completion_rate: float
```

### 8.2 智能摘要与底稿生成

**功能**：自动汇总抽样结果、差异说明、替代测试结论，生成结构化工作底稿初稿。

**底稿模板**：

```python
class WorkingPaperGenerator:
    """工作底稿自动生成"""

    def generate(self, project_id: str,
                 sampling_results: List[SamplingResult],
                 validation_results: List[ValidationResult]) -> WorkingPaper:
        """生成工作底稿"""

        # 1. 汇总抽样情况
        summary = self._generate_summary(sampling_results)

        # 2. 汇总差异分析
        differences = self._analyze_differences(validation_results)

        # 3. 替代测试结论
        alternative_tests = self._generate_alt_test_conclusions(
            sampling_results, validation_results
        )

        # 4. AI生成描述
        ai_description = self._generate_ai_description(
            summary, differences, alternative_tests
        )

        return WorkingPaper(
            project_name=project_id,
            sampling_summary=summary,
            difference_analysis=differences,
            alternative_test_conclusions=alternative_tests,
            ai_generated_description=ai_description,
            generated_at=datetime.now(),
            template_type="standard"
        )

    def export_pdf(self, working_paper: WorkingPaper) -> bytes:
        """导出PDF底稿"""
        # 使用WeasyPrint或ReportLab生成
        ...
```

**底稿结构**：
```
一、抽凭概述
   - 项目信息
   - 抽样方法
   - 样本量及分布

二、抽样结果汇总
   - 各科目抽样情况
   - 风险分布统计

三、差异及异常分析
   - 三单匹配差异
   - 合规检查异常
   - 交叉验证结果

四、替代测试结论
   - 未能查验项目的替代测试
   - 测试结论

五、审计说明
   - AI自动生成的审计说明
```

### 8.3 审计轨迹留痕

**功能**：完整记录每一笔样本的"为什么抽、如何抽、结果如何"，满足质控要求。

**轨迹记录**：

```python
class AuditTrail:
    """审计轨迹记录"""

    def record(self, event: AuditEvent):
        """记录审计事件"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": event.user_id,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "details": event.details,
            "reason": event.reason,          # 为什么
            "method": event.method,          # 如何做
            "result": event.result,           # 结果如何
            "ip_address": event.ip_address,
            "session_id": event.session_id
        }
        self.storage.save(record)

# 审计事件类型
class AuditEvent:
    SAMPLE_CREATED = "sample.created"           # 创建抽样
    SAMPLE_REVIEWED = "sample.reviewed"          # 复核样本
    VOUCHER_UPLOADED = "voucher.uploaded"        # 凭证上传
    RULE_EXECUTED = "rule.executed"              # 规则执行
    RESULT_EXPORTED = "result.exported"          # 结果导出
    AI_ANALYZED = "ai.analyzed"                  # AI分析
```

**轨迹查询接口**：
```python
GET /api/projects/{id}/audit-trail?start_date=&end_date=&user=&action=
```

---

## 九、API设计

### 9.1 项目管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects | 获取项目列表 |
| POST | /api/projects | 创建项目 |
| GET | /api/projects/{id} | 获取项目详情 |
| PUT | /api/projects/{id} | 更新项目 |
| DELETE | /api/projects/{id} | 删除项目 |

### 9.2 凭证管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects/{id}/vouchers | 获取凭证列表 |
| POST | /api/projects/{id}/vouchers/import | 导入凭证(Excel/CSV) |
| POST | /api/projects/{id}/vouchers/{voucher_id}/attachment | 上传附件 |
| GET | /api/projects/{id}/vouchers/{voucher_id} | 获取凭证详情 |
| POST | /api/projects/{id}/vouchers/{voucher_id}/ocr | OCR识别凭证 |

### 9.3 智能抽样
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/risk-profile/generate | 生成风险画像 |
| GET | /api/projects/{id}/risk-profile | 获取风险画像 |
| POST | /api/projects/{id}/sampling/strategy/recommend | 推荐抽样策略 |
| GET | /api/projects/{id}/sampling/calculate-sample-size | 计算样本量(参数调整) |

### 9.4 抽凭功能
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects/{id}/sampling-rules | 获取抽凭规则 |
| POST | /api/projects/{id}/sampling-rules | 创建规则 |
| POST | /api/projects/{id}/sampling/execute | 执行抽凭 |
| GET | /api/projects/{id}/samples | 获取抽凭结果 |
| POST | /api/projects/{id}/samples/export | 导出抽凭结果 |

### 9.5 核对与预警
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/matching/three-way | 执行三单匹配 |
| GET | /api/projects/{id}/matching/results | 获取匹配结果 |
| POST | /api/projects/{id}/compliance/check | 执行合规检查 |
| GET | /api/projects/{id}/compliance/alerts | 获取合规预警 |
| POST | /api/projects/{id}/validation/cross | 交叉验证 |

### 9.6 工作流与底稿
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/projects/{id}/tasks/assign | 分派任务 |
| GET | /api/projects/{id}/tasks | 获取任务列表 |
| PUT | /api/projects/{id}/tasks/{task_id} | 更新任务状态 |
| GET | /api/projects/{id}/tasks/progress | 获取进度追踪 |
| POST | /api/projects/{id}/working-paper/generate | 生成底稿 |
| GET | /api/projects/{id}/working-paper | 获取底稿列表 |
| GET | /api/projects/{id}/working-paper/{paper_id}/export | 导出底稿(PDF) |

### 9.7 审计轨迹
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/projects/{id}/audit-trail | 查询审计轨迹 |
| GET | /api/projects/{id}/audit-trail/export | 导出轨迹记录 |

### 9.8 AI服务
| 方法 | 路径 |说明 |
|------|------|------|
| POST | /api/ai/analyze | 分析凭证风险 |
| POST | /api/ai/intelligent-sample | AI智能抽凭 |
| POST | /api/ai/describe-voucher | AI理解凭证内容 |
| GET | /api/ai/models | 获取可用模型列表 |
| PUT | /api/ai/config | 配置AI模型 |

### 9.9 爬虫
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/crawler/start | 启动爬虫 |
| GET | /api/crawler/status/{task_id} | 获取爬取状态 |
| POST | /api/crawler/stop | 停止爬虫 |

---

## 十、数据库设计 (DuckDB)

```sql
-- 项目表
CREATE TABLE projects (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 凭证表
CREATE TABLE vouchers (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    voucher_no VARCHAR NOT NULL,
    voucher_date DATE,
    amount DECIMAL(18, 2),
    subject_code VARCHAR,
    subject_name VARCHAR,
    description TEXT,
    attachment_path VARCHAR,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 抽凭规则表
CREATE TABLE sampling_rules (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    name VARCHAR NOT NULL,
    rule_type VARCHAR NOT NULL,
    rule_config JSON NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 抽凭结果表
CREATE TABLE samples (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    rule_id VARCHAR REFERENCES sampling_rules(id),
    voucher_id VARCHAR REFERENCES vouchers(id),
    risk_score DECIMAL(5, 2),
    reason TEXT,
    sampled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 爬虫任务表
CREATE TABLE crawler_tasks (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    platform VARCHAR,
    status VARCHAR DEFAULT 'pending',
    total_count INTEGER,
    success_count INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- 风险画像表
CREATE TABLE risk_profiles (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    subject_code VARCHAR NOT NULL,
    subject_name VARCHAR,
    risk_level VARCHAR DEFAULT 'medium',
    risk_factors JSON,
    material_amount DECIMAL(18, 2),
    anomaly_score DECIMAL(5, 2),
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 凭证OCR结果表
CREATE TABLE voucher_ocr_results (
    id VARCHAR PRIMARY KEY,
    voucher_id VARCHAR REFERENCES vouchers(id),
    ocr_provider VARCHAR,
    voucher_no VARCHAR,
    voucher_date DATE,
    amount DECIMAL(18, 2),
    counterparty VARCHAR,
    description TEXT,
    signatures JSON,
    raw_text TEXT,
    confidence DECIMAL(5, 2),
    raw_result JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 凭证分类表
CREATE TABLE voucher_categories (
    id VARCHAR PRIMARY KEY,
    voucher_id VARCHAR REFERENCES vouchers(id),
    category_type VARCHAR,
    subject_category VARCHAR,
    business_category VARCHAR,
    risk_tag VARCHAR,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 三单匹配结果表
CREATE TABLE matching_results (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    invoice_id VARCHAR REFERENCES vouchers(id),
    order_id VARCHAR,
    receipt_id VARCHAR,
    match_status VARCHAR,
    amount_difference DECIMAL(18, 2),
    date_difference INTEGER,
    differences JSON,
    suggestions JSON,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 合规检查预警表
CREATE TABLE compliance_alerts (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    voucher_id VARCHAR REFERENCES vouchers(id),
    rule_name VARCHAR,
    rule_description TEXT,
    severity VARCHAR,
    alert_message TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 审计任务表
CREATE TABLE audit_tasks (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    sample_ids JSON,
    assignee_id VARCHAR,
    assignee_name VARCHAR,
    status VARCHAR DEFAULT 'pending',
    deadline TIMESTAMP,
    priority VARCHAR DEFAULT 'medium',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 工作底稿表
CREATE TABLE working_papers (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    paper_type VARCHAR,
    title VARCHAR,
    content JSON,
    ai_description TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 审计轨迹表
CREATE TABLE audit_trail (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR REFERENCES projects(id),
    user_id VARCHAR,
    action VARCHAR,
    target_type VARCHAR,
    target_id VARCHAR,
    details JSON,
    reason TEXT,
    method TEXT,
    result TEXT,
    ip_address VARCHAR,
    session_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 十一、AI模型集成设计

### 11.1 模型适配器模式

```python
from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

# 具体实现
class QwenAdapter(LLMAdapter):
    def __init__(self, api_key: str, base_url: str):
        ...

class OllamaAdapter(LLMAdapter):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        ...

# 工厂类
class LLMFactory:
    @staticmethod
    def create(provider: str, **config) -> LLMAdapter:
        adapters = {
            "qwen": QwenAdapter,
            "ollama": OllamaAdapter,
            "ERNIE": ERNIEAdapter,
        }
        return adapters[provider](**config)
```

### 11.2 配置管理

```yaml
# config/ai_config.yaml
ai_providers:
  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    default_model: "qwen2.5:14b"

  qwen:
    enabled: true
    api_key: "${QWEN_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model: "qwen-turbo"

  ernie:
    enabled: true
    api_key: "${ERNIE_API_KEY}"
    default_model: "ernie-4.0-8k"

default_provider: "ollama"
```

---

## 十二、移动端设计 (uni-app)

### 12.1 页面结构

```
pages/
├── index/index            # 首页（项目列表）
├── project/detail         # 项目详情
├── vouchers/list          # 凭证列表
├── vouchers/detail        # 凭证详情
├── risk/                  # 风险画像
├── sampling/execute       # 执行抽凭
├── sampling/result        # 抽凭结果
├── task/                  # 任务追踪
├── paper/                 # 底稿查看
├── profile/profile        # 个人中心
└── settings/settings      # 设置
```

### 12.2 核心功能页面

1. **项目列表**：展示审计项目，支持创建/切换项目
2. **凭证浏览**：查看凭证列表，支持筛选搜索
3. **风险画像**：查看科目风险等级分布
4. **抽凭执行**：选择规则，执行抽凭，查看结果
5. **任务追踪**：查看任务进度
6. **抽凭报告**：导出/分享抽凭结果

---

## 十三、部署方案

### 13.1 开发环境
```bash
# 后端
pip install -r requirements.txt
uvicorn main:app --reload

# 前端
cd web && npm install && npm run dev

# 移动端
cd mobile && npm install && npm run dev:%PLATFORM%
```

### 13.2 生产环境

**Docker Compose 部署**：
```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./attachments:/app/attachments
    environment:
      - DATABASE_URL=duckdb:///app/data/audit.db

  web:
    build: ./web
    ports:
      - "3000:3000"

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
```

---

## 十四、实施计划

### Phase 1: 基础架构搭建 (第1-2周)
- [ ] 项目初始化，目录结构创建
- [ ] FastAPI后端基础框架搭建
- [ ] DuckDB数据库初始化
- [ ] 基础API开发
- [ ] 用户认证与权限管理

### Phase 2: 核心功能开发 (第3-6周)
- [ ] 凭证管理模块（导入、存储、查询）
- [ ] 抽凭规则引擎
- [ ] 文件上传与存储
- [ ] 多模态凭证处理（OCR集成）
- [ ] 凭证智能分类与索引

### Phase 3: 智能抽样模块 (第7-8周)
- [ ] 风险画像生成引擎
- [ ] 科目风险评估算法
- [ ] 抽样策略推荐系统
- [ ] 参数可视化调整界面
- [ ] 样本量计算器

### Phase 4: AI能力集成 (第9-10周)
- [ ] LLM适配器开发（支持多种国内API）
- [ ] AI智能抽凭功能
- [ ] 向量数据库集成（可选）
- [ ] 凭证语义理解

### Phase 5: 核对与预警模块 (第11-12周)
- [ ] 三单匹配引擎
- [ ] 合规性检查规则库
- [ ] 交叉验证功能
- [ ] 预警通知系统

### Phase 6: 工作流与底稿 (第13-15周)
- [ ] 任务分派与追踪系统
- [ ] 底稿模板引擎
- [ ] AI底稿生成
- [ ] 审计轨迹留痕
- [ ] PDF导出功能

### Phase 7: 爬虫模块 (第16周)
- [ ] 爬虫基础框架
- [ ] 至少一个平台爬取实现

### Phase 8: 前端与移动端 (第17-19周)
- [ ] Web管理后台
- [ ] uni-app移动端
- [ ] 参数可视化前端

### Phase 9: 优化与部署 (第20周)
- [ ] 性能优化
- [ ] 容器化部署
- [ ] 测试与修复

---

## 十五、关键文件路径

```
audit-project02/
├── backend/                  # FastAPI后端
│   ├── app/
│   │   ├── api/             # API路由
│   │   │   ├── projects.py  # 项目管理
│   │   │   ├── vouchers.py  # 凭证管理
│   │   │   ├── sampling.py  # 抽凭模块
│   │   │   ├── risk.py      # 风险画像
│   │   │   ├── matching.py  # 三单匹配
│   │   │   ├── compliance.py # 合规检查
│   │   │   ├── tasks.py     # 任务管理
│   │   │   ├── working_paper.py # 底稿生成
│   │   │   ├── crawler.py    # 爬虫
│   │   │   └── ai.py        # AI服务
│   │   ├── core/            # 核心配置
│   │   ├── models/          # 数据模型
│   │   ├── services/        # 业务逻辑
│   │   │   ├── ocr_service.py     # OCR服务
│   │   │   ├── risk_service.py    # 风险评估
│   │   │   ├── matching_service.py # 匹配服务
│   │   │   ├── compliance_service.py # 合规服务
│   │   │   ├── workflow_service.py # 工作流服务
│   │   │   └── paper_service.py   # 底稿服务
│   │   └── utils/           # 工具函数
│   ├── main.py
│   └── requirements.txt
│
├── web/                      # Web管理后台 (Vue/React)
│   ├── src/
│   │   ├── views/
│   │   │   ├── sampling/    # 智能抽样页面
│   │   │   ├── ocr/         # OCR识别页面
│   │   │   ├── matching/    # 三单匹配页面
│   │   │   ├── compliance/  # 合规检查页面
│   │   │   ├── workflow/    # 工作流管理
│   │   │   └── papers/      # 底稿生成
│   │   └── components/
│   └── package.json
│
├── mobile/                   # uni-app移动端
│   ├── pages/
│   │   ├── risk/            # 风险画像
│   │   ├── sampling/        # 抽样执行
│   │   ├── task/            # 任务追踪
│   │   └── paper/           # 底稿查看
│   └── package.json
│
├── data/                     # 数据目录
│   ├── db/                  # DuckDB数据库
│   ├── attachments/         # 凭证附件
│   ├── ocr/                 # OCR缓存
│   └── papers/              # 生成的底稿
│
└── config/                   # 配置文件
    ├── ai_config.yaml       # AI模型配置
    ├── ocr_config.yaml      # OCR配置
    └── rules/               # 合规规则配置
```

---

## 十六、验证方案

### 功能验证
1. **凭证导入**：上传Excel/CSV文件，验证数据正确解析
2. **规则抽凭**：配置规则，执行抽凭，验证结果
3. **AI抽凭**：配置LLM，执行智能抽凭，验证返回结果
4. **爬虫**：启动爬虫，验证数据采集
5. **API测试**：使用curl/Postman测试所有接口

### 性能验证
1. **大数据量**：导入10000+凭证，测试响应时间
2. **并发测试**：多用户同时访问，验证稳定性

### 部署验证
1. Docker容器构建成功
2. 服务启动正常
3. 移动端可以正常访问

---

*文档版本: v2.0*
*更新日期: 2026-03-23*