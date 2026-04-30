"""
数据库连接与初始化

DuckDB 连接管理策略：
1. 使用线程锁保护并发写入
2. 提供请求级别的连接管理
3. 自动处理连接的生命周期
"""
import duckdb
import threading
import logging
from typing import Optional
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# 数据库连接（单例，受锁保护）
_db_connection: Optional[duckdb.DuckDBPyConnection] = None
_db_lock = threading.Lock()


def get_db() -> duckdb.DuckDBPyConnection:
    """
    获取数据库连接（线程安全）

    使用单例模式，确保只有一个数据库连接。
    DuckDB 不支持多连接并发写入，因此使用锁保护。

    Returns:
        duckdb.DuckDBPyConnection: 数据库连接
    """
    global _db_connection
    if _db_connection is None:
        with _db_lock:
            # 双重检查锁定
            if _db_connection is None:
                # 确保数据库目录存在
                db_path = Path(settings.DATABASE_PATH)
                db_path.parent.mkdir(parents=True, exist_ok=True)

                _db_connection = duckdb.connect(str(db_path))
                logger.info(f"数据库连接已建立: {db_path}")
    return _db_connection


@contextmanager
def get_db_cursor():
    """
    获取数据库游标的上下文管理器

    使用方式：
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM table")

    注意：对于写操作，应使用 with_db_lock() 包装
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


@contextmanager
def with_db_lock():
    """
    数据库写操作的锁上下文管理器

    使用方式：
        with with_db_lock():
            with get_db_cursor() as cursor:
                cursor.execute("INSERT INTO ...")
                get_db().commit()
    """
    _db_lock.acquire()
    try:
        yield
    finally:
        _db_lock.release()


def db_transaction(func):
    """
    数据库事务装饰器

    自动获取锁并提交事务，发生异常时回滚
    """
    def wrapper(*args, **kwargs):
        with _db_lock:
            conn = get_db()
            try:
                result = func(*args, **kwargs)
                conn.commit()
                return result
            except Exception as e:
                conn.rollback()
                logger.error(f"数据库事务失败: {str(e)}")
                raise
    return wrapper


def close_db():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection is not None:
        with _db_lock:
            if _db_connection is not None:
                _db_connection.close()
                _db_connection = None
                logger.info("数据库连接已关闭")


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR PRIMARY KEY,
            username VARCHAR NOT NULL UNIQUE,
            email VARCHAR,
            full_name VARCHAR,
            hashed_password VARCHAR NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
    """)

    # 项目表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            description TEXT,
            status VARCHAR DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 凭证表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vouchers (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            voucher_no VARCHAR NOT NULL,
            voucher_date DATE,
            amount DECIMAL(18, 2),
            subject_code VARCHAR,
            subject_name VARCHAR,
            description TEXT,
            counterparty VARCHAR,
            attachment_path VARCHAR,
            raw_data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vouchers_project_id ON vouchers(project_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vouchers_voucher_date ON vouchers(voucher_date)
    """)

    # 凭证附件表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voucher_attachments (
            id VARCHAR PRIMARY KEY,
            voucher_id VARCHAR REFERENCES vouchers(id),
            file_name VARCHAR NOT NULL,
            file_path VARCHAR NOT NULL,
            file_size INTEGER,
            file_type VARCHAR,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            recognition_result TEXT
        )
    """)

    # 添加recognition_result列（如果不存在）
    try:
        cursor.execute("ALTER TABLE voucher_attachments ADD COLUMN recognition_result TEXT")
    except:
        pass  # 列已存在，忽略错误

    # 创建附件索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_attachments_voucher_id ON voucher_attachments(voucher_id)
    """)

    # 抽凭规则表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sampling_rules (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            name VARCHAR NOT NULL,
            rule_type VARCHAR NOT NULL,
            rule_config JSON NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 抽样记录表 - 记录每次抽样操作
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sampling_records (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            rule_id VARCHAR REFERENCES sampling_rules(id),
            rule_name VARCHAR NOT NULL,
            rule_type VARCHAR NOT NULL,
            sample_size INTEGER DEFAULT 0,
            high_risk_count INTEGER DEFAULT 0,
            medium_risk_count INTEGER DEFAULT 0,
            low_risk_count INTEGER DEFAULT 0,
            status VARCHAR DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sampling_records_project_id ON sampling_records(project_id)
    """)

    # 抽凭结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            record_id VARCHAR REFERENCES sampling_records(id),
            rule_id VARCHAR REFERENCES sampling_rules(id),
            voucher_id VARCHAR REFERENCES vouchers(id),
            risk_score DECIMAL(5, 2),
            reason TEXT,
            sampled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_samples_project_id ON samples(project_id)
    """)

    # 迁移：检查并添加record_id列（如果不存在）
    try:
        cursor.execute("SELECT record_id FROM samples LIMIT 1")
    except:
        # record_id列不存在，添加它（不带外键约束）
        cursor.execute("ALTER TABLE samples ADD COLUMN record_id VARCHAR")
        print("Added record_id column to samples table")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_record_id ON samples(record_id)")
    except:
        pass  # 索引可能已存在

    # 风险画像表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_profiles (
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
        )
    """)

    # OCR结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voucher_ocr_results (
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
        )
    """)

    # 凭证分类表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voucher_categories (
            id VARCHAR PRIMARY KEY,
            voucher_id VARCHAR REFERENCES vouchers(id),
            category_type VARCHAR,
            subject_category VARCHAR,
            business_category VARCHAR,
            risk_tag VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 三单匹配结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matching_results (
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
        )
    """)

    # 合规检查预警表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compliance_alerts (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            voucher_id VARCHAR REFERENCES vouchers(id),
            voucher_no VARCHAR,
            rule_code VARCHAR,
            rule_name VARCHAR,
            rule_description TEXT,
            severity VARCHAR,
            alert_message TEXT,
            details JSON,
            is_resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 审计任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_tasks (
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
        )
    """)

    # 工作底稿表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS working_papers (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            paper_type VARCHAR,
            title VARCHAR,
            content JSON,
            ai_description TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 审计轨迹表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail (
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
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_trail_project_id ON audit_trail(project_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at ON audit_trail(created_at)
    """)

    # 爬虫任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS crawler_tasks (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            platform VARCHAR,
            status VARCHAR DEFAULT 'pending',
            total_count INTEGER,
            success_count INTEGER,
            error_message TEXT,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_crawler_tasks_project_id ON crawler_tasks(project_id)
    """)

    # 数据库迁移：为已存在的 compliance_alerts 表添加新字段
    try:
        # 检查是否存在 voucher_no 列
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'compliance_alerts' AND column_name = 'voucher_no'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE compliance_alerts ADD COLUMN voucher_no VARCHAR")

        # 检查是否存在 rule_code 列
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'compliance_alerts' AND column_name = 'rule_code'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE compliance_alerts ADD COLUMN rule_code VARCHAR")

        # 检查是否存在 details 列
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'compliance_alerts' AND column_name = 'details'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE compliance_alerts ADD COLUMN details JSON")
    except Exception as e:
        print(f"Migration warning: {e}")

    # ==================== 智能抽样模块扩展 ====================

    # 错报记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_misstatements (
            id VARCHAR PRIMARY KEY,
            sample_id VARCHAR REFERENCES samples(id),
            project_id VARCHAR REFERENCES projects(id),
            misstatement_type VARCHAR NOT NULL,
            misstatement_amount DECIMAL(18, 2),
            original_amount DECIMAL(18, 2),
            correct_amount DECIMAL(18, 2),
            description TEXT,
            evidence_path VARCHAR,
            severity VARCHAR DEFAULT 'medium',
            identified_by VARCHAR,
            identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_by VARCHAR,
            reviewed_at TIMESTAMP,
            review_notes TEXT,
            is_confirmed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_misstatements_sample_id ON sample_misstatements(sample_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_misstatements_project_id ON sample_misstatements(project_id)
    """)

    # 统计推断结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS statistical_inferences (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            record_id VARCHAR REFERENCES sampling_records(id),
            inference_type VARCHAR NOT NULL,
            confidence_level DECIMAL(5, 2),
            tolerable_misstatement DECIMAL(18, 2),
            expected_misstatement DECIMAL(18, 2),
            sample_misstatement_count INTEGER,
            sample_misstatement_amount DECIMAL(18, 2),
            projected_misstatement DECIMAL(18, 2),
            upper_limit DECIMAL(18, 2),
            lower_limit DECIMAL(18, 2),
            precision DECIMAL(18, 2),
            conclusion TEXT,
            is_acceptable BOOLEAN,
            recommendations JSON,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_inferences_record_id ON statistical_inferences(record_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_inferences_project_id ON statistical_inferences(project_id)
    """)

    # AI测试结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sample_ai_test_results (
            id VARCHAR PRIMARY KEY,
            sample_id VARCHAR REFERENCES samples(id),
            voucher_id VARCHAR REFERENCES vouchers(id),
            ai_conclusion VARCHAR NOT NULL,
            confidence DECIMAL(5, 2),
            risk_level VARCHAR,
            risk_factors JSON,
            anomaly_descriptions JSON,
            evidence_analysis JSON,
            key_fields_extracted JSON,
            recommended_action VARCHAR,
            needs_manual_review BOOLEAN DEFAULT FALSE,
            reviewed_at TIMESTAMP,
            manual_override VARCHAR,
            override_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_results_sample_id ON sample_ai_test_results(sample_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_results_voucher_id ON sample_ai_test_results(voucher_id)
    """)

    # ==================== 现有表字段扩展迁移 ====================

    # samples表扩展字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'test_status'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN test_status VARCHAR DEFAULT 'pending'")
    except Exception as e:
        print(f"Migration warning (samples.test_status): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'ai_test_result'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN ai_test_result VARCHAR")
    except Exception as e:
        print(f"Migration warning (samples.ai_test_result): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'misstatement_amount'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN misstatement_amount DECIMAL(18, 2)")
    except Exception as e:
        print(f"Migration warning (samples.misstatement_amount): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'tested_at'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN tested_at TIMESTAMP")
    except Exception as e:
        print(f"Migration warning (samples.tested_at): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'tester'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN tester VARCHAR")
    except Exception as e:
        print(f"Migration warning (samples.tester): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'test_notes'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN test_notes TEXT")
    except Exception as e:
        print(f"Migration warning (samples.test_notes): {e}")

    # 添加风险详情字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'risk_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN risk_level VARCHAR")
    except Exception as e:
        print(f"Migration warning (samples.risk_level): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'risk_factors'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN risk_factors TEXT")
    except Exception as e:
        print(f"Migration warning (samples.risk_factors): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'samples' AND column_name = 'explanation'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE samples ADD COLUMN explanation TEXT")
    except Exception as e:
        print(f"Migration warning (samples.explanation): {e}")

    # sampling_rules表扩展字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_rules' AND column_name = 'confidence_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_rules ADD COLUMN confidence_level DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_rules.confidence_level): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_rules' AND column_name = 'tolerable_error'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_rules ADD COLUMN tolerable_error DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_rules.tolerable_error): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_rules' AND column_name = 'expected_error'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_rules ADD COLUMN expected_error DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_rules.expected_error): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_rules' AND column_name = 'population_amount'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_rules ADD COLUMN population_amount DECIMAL(18, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_rules.population_amount): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_rules' AND column_name = 'sampling_interval'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_rules ADD COLUMN sampling_interval DECIMAL(18, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_rules.sampling_interval): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_rules' AND column_name = 'random_start'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_rules ADD COLUMN random_start DECIMAL(18, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_rules.random_start): {e}")

    # sampling_records表扩展字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'population_count'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN population_count INTEGER")
    except Exception as e:
        print(f"Migration warning (sampling_records.population_count): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'population_amount'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN population_amount DECIMAL(18, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_records.population_amount): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'tested_count'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN tested_count INTEGER DEFAULT 0")
    except Exception as e:
        print(f"Migration warning (sampling_records.tested_count): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'misstatement_count'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN misstatement_count INTEGER DEFAULT 0")
    except Exception as e:
        print(f"Migration warning (sampling_records.misstatement_count): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'total_misstatement_amount'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN total_misstatement_amount DECIMAL(18, 2)")
    except Exception as e:
        print(f"Migration warning (sampling_records.total_misstatement_amount): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'inference_completed'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN inference_completed BOOLEAN DEFAULT FALSE")
    except Exception as e:
        print(f"Migration warning (sampling_records.inference_completed): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'sampling_records' AND column_name = 'inference_conclusion'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE sampling_records ADD COLUMN inference_conclusion VARCHAR")
    except Exception as e:
        print(f"Migration warning (sampling_records.inference_conclusion): {e}")

    # ==================== 风险画像模块扩展 ====================

    # 项目风险概览表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_risk_overview (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            overall_risk_score DECIMAL(5, 2),
            overall_risk_level VARCHAR,
            dimension_scores JSON,
            high_risk_subjects JSON,
            risk_trend JSON,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_project_risk_overview_project_id ON project_risk_overview(project_id)
    """)

    # 交易对手风险分析表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS counterparty_risk (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            counterparty_name VARCHAR,
            total_amount DECIMAL(18, 2),
            transaction_count INTEGER,
            concentration_ratio DECIMAL(5, 4),
            is_related_party BOOLEAN DEFAULT FALSE,
            is_new_customer BOOLEAN DEFAULT FALSE,
            first_transaction_date DATE,
            last_transaction_date DATE,
            risk_score DECIMAL(5, 2),
            risk_level VARCHAR,
            risk_factors JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_counterparty_risk_project_id ON counterparty_risk(project_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_counterparty_risk_name ON counterparty_risk(counterparty_name)
    """)

    # 时间维度风险分析表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_risk_analysis (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            period VARCHAR,
            period_type VARCHAR,
            total_amount DECIMAL(18, 2),
            transaction_count INTEGER,
            volatility_score DECIMAL(5, 2),
            period_end_concentration DECIMAL(5, 4),
            anomaly_indicators JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_time_risk_project_id ON time_risk_analysis(project_id)
    """)

    # 文档完整性检查表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_completeness_check (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            voucher_id VARCHAR REFERENCES vouchers(id),
            has_contract BOOLEAN DEFAULT FALSE,
            has_invoice BOOLEAN DEFAULT FALSE,
            has_logistics BOOLEAN DEFAULT FALSE,
            has_payment_proof BOOLEAN DEFAULT FALSE,
            completeness_score DECIMAL(5, 2),
            missing_documents JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_doc_check_voucher_id ON document_completeness_check(voucher_id)
    """)

    # 凭证风险标签表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voucher_risk_tags (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            voucher_id VARCHAR REFERENCES vouchers(id),
            tag_code VARCHAR,
            tag_name VARCHAR,
            tag_category VARCHAR,
            severity VARCHAR,
            details JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_voucher_tags_voucher_id ON voucher_risk_tags(voucher_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_voucher_tags_tag_code ON voucher_risk_tags(tag_code)
    """)

    # 风险配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_configurations (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            config_type VARCHAR,
            config_name VARCHAR,
            config_data JSON NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_risk_config_project_id ON risk_configurations(project_id)
    """)

    # 风险历史记录表（用于趋势分析）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_history (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
            subject_code VARCHAR,
            risk_score DECIMAL(5, 2),
            risk_level VARCHAR,
            risk_factors JSON,
            snapshot_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_risk_history_project_id ON risk_history(project_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_risk_history_snapshot_date ON risk_history(snapshot_date)
    """)

    # ==================== 现有表扩展迁移（风险画像相关） ====================

    # risk_profiles表扩展字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'risk_profiles' AND column_name = 'risk_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE risk_profiles ADD COLUMN risk_score DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (risk_profiles.risk_score): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'risk_profiles' AND column_name = 'counterparty_risk_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE risk_profiles ADD COLUMN counterparty_risk_score DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (risk_profiles.counterparty_risk_score): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'risk_profiles' AND column_name = 'time_risk_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE risk_profiles ADD COLUMN time_risk_score DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (risk_profiles.time_risk_score): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'risk_profiles' AND column_name = 'document_risk_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE risk_profiles ADD COLUMN document_risk_score DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (risk_profiles.document_risk_score): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'risk_profiles' AND column_name = 'updated_at'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE risk_profiles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except Exception as e:
        print(f"Migration warning (risk_profiles.updated_at): {e}")

    # vouchers表扩展风险字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'vouchers' AND column_name = 'risk_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE vouchers ADD COLUMN risk_score DECIMAL(5, 2)")
    except Exception as e:
        print(f"Migration warning (vouchers.risk_score): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'vouchers' AND column_name = 'risk_level'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE vouchers ADD COLUMN risk_level VARCHAR")
    except Exception as e:
        print(f"Migration warning (vouchers.risk_level): {e}")

    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'vouchers' AND column_name = 'risk_tags'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE vouchers ADD COLUMN risk_tags JSON")
    except Exception as e:
        print(f"Migration warning (vouchers.risk_tags): {e}")

    # vouchers表添加AI分析字段
    try:
        cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'vouchers' AND column_name = 'ai_analysis'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE vouchers ADD COLUMN ai_analysis JSON")
    except Exception as e:
        print(f"Migration warning (vouchers.ai_analysis): {e}")

    # ==================== AI调用日志与用量统计 ====================

    # AI调用日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_call_logs (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR,
            purpose VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            model VARCHAR NOT NULL,
            operation VARCHAR NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            latency_ms DECIMAL(10, 2),
            status VARCHAR DEFAULT 'success',
            error_message TEXT,
            request_content TEXT,
            response_content TEXT,
            user_id VARCHAR,
            session_id VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_logs_project_id ON ai_call_logs(project_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_logs_created_at ON ai_call_logs(created_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_logs_provider ON ai_call_logs(provider)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_logs_purpose ON ai_call_logs(purpose)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_logs_status ON ai_call_logs(status)
    """)

    # AI用量汇总表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage_summary (
            id VARCHAR PRIMARY KEY,
            period_type VARCHAR NOT NULL,
            period_value VARCHAR NOT NULL,
            project_id VARCHAR,
            provider VARCHAR,
            model VARCHAR,
            purpose VARCHAR,
            total_calls INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            total_latency_ms DECIMAL(12, 2),
            avg_latency_ms DECIMAL(10, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_usage_period ON ai_usage_summary(period_type, period_value)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_usage_provider ON ai_usage_summary(provider)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_usage_purpose ON ai_usage_summary(purpose)
    """)

    conn.commit()
    print(f"Database initialized at {settings.DATABASE_PATH}")


def close_db():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None
        print("Database connection closed")