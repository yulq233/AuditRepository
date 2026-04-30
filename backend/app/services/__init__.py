"""
服务模块
"""
from app.services.storage_service import FileStorageService, storage_service
from app.services.rule_engine import RuleEngine, rule_engine, RuleFactory
from app.services.ocr_service import OCRService, ocr_service, OCRResult
from app.services.classification_service import (
    VoucherClassifier, VoucherIndexer,
    voucher_classifier, voucher_indexer,
    VoucherType, BusinessType, RiskTag
)
from app.services.export_service import ExcelExporter, PDFExporter, excel_exporter, pdf_exporter
from app.services.llm_service import (
    LLMService, LLMConfig, LLMAdapter, LLMResponse, ChatMessage,
    LLMFactory, llm_service
)
from app.services.ai_sampling_service import (
    VoucherRiskAnalyzer, IntelligentSampler,
    risk_analyzer, intelligent_sampler,
    RiskAssessment, SamplingRecommendation
)
from app.services.embedding_service import (
    EmbeddingService, SemanticSearchService,
    embedding_service, semantic_search_service
)
from app.services.risk_profile_service import (
    RiskProfileGenerator, RiskProfile, RiskLevel,
    risk_profile_generator
)
from app.services.ai_risk_service import (
    AIRiskAnalyzer, AIRiskAssessment, VoucherAIRisk,
    ai_risk_analyzer
)
from app.services.sampling_strategy_service import (
    SamplingStrategyRecommender, SamplingStrategy, SamplingMethod,
    sampling_strategy_recommender
)
from app.services.three_way_matching_service import (
    ThreeWayMatcher, MatchResult, MatchStatus,
    three_way_matcher
)
from app.services.compliance_service import (
    ComplianceChecker, ComplianceAlert, ComplianceSeverity,
    compliance_checker
)
from app.services.cross_validation_service import (
    CrossValidator, ValidationResult, ValidationSource,
    cross_validator
)
from app.services.task_service import (
    TaskManager, AuditTask, TaskStatus, TaskPriority, TeamMember,
    task_manager
)
from app.services.working_paper_service import (
    WorkingPaperGenerator, WorkingPaper, PaperType,
    working_paper_generator
)
from app.services.audit_trail_service import (
    AuditTrail, AuditEvent, AuditAction,
    audit_trail
)

__all__ = [
    # 存储服务
    "FileStorageService",
    "storage_service",
    # 规则引擎
    "RuleEngine",
    "rule_engine",
    "RuleFactory",
    # OCR服务
    "OCRService",
    "ocr_service",
    "OCRResult",
    # 分类服务
    "VoucherClassifier",
    "VoucherIndexer",
    "voucher_classifier",
    "voucher_indexer",
    "VoucherType",
    "BusinessType",
    "RiskTag",
    # 导出服务
    "ExcelExporter",
    "PDFExporter",
    "excel_exporter",
    "pdf_exporter",
    # LLM服务
    "LLMService",
    "LLMConfig",
    "LLMAdapter",
    "LLMResponse",
    "ChatMessage",
    "LLMFactory",
    "llm_service",
    # AI抽样服务
    "VoucherRiskAnalyzer",
    "IntelligentSampler",
    "risk_analyzer",
    "intelligent_sampler",
    "RiskAssessment",
    "SamplingRecommendation",
    # Embedding服务
    "EmbeddingService",
    "SemanticSearchService",
    "embedding_service",
    "semantic_search_service",
    # 风险画像服务
    "RiskProfileGenerator",
    "RiskProfile",
    "RiskLevel",
    "risk_profile_generator",
    # AI风险分析服务
    "AIRiskAnalyzer",
    "AIRiskAssessment",
    "VoucherAIRisk",
    "ai_risk_analyzer",
    # 抽样策略服务
    "SamplingStrategyRecommender",
    "SamplingStrategy",
    "SamplingMethod",
    "sampling_strategy_recommender",
    # 三单匹配服务
    "ThreeWayMatcher",
    "MatchResult",
    "MatchStatus",
    "three_way_matcher",
    # 合规检查服务
    "ComplianceChecker",
    "ComplianceAlert",
    "ComplianceSeverity",
    "compliance_checker",
    # 交叉验证服务
    "CrossValidator",
    "ValidationResult",
    "ValidationSource",
    "cross_validator",
    # 任务管理服务
    "TaskManager",
    "AuditTask",
    "TaskStatus",
    "TaskPriority",
    "TeamMember",
    "task_manager",
    # 工作底稿服务
    "WorkingPaperGenerator",
    "WorkingPaper",
    "PaperType",
    "working_paper_generator",
    # 审计轨迹服务
    "AuditTrail",
    "AuditEvent",
    "AuditAction",
    "audit_trail"
]