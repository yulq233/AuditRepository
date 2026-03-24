"""
数据库连接与初始化
"""
import duckdb
from typing import Optional
from contextlib import contextmanager

from app.core.config import settings


# 全局数据库连接
_db_connection: Optional[duckdb.DuckDBPyConnection] = None


def get_db() -> duckdb.DuckDBPyConnection:
    """获取数据库连接"""
    global _db_connection
    if _db_connection is None:
        _db_connection = duckdb.connect(settings.DATABASE_PATH)
    return _db_connection


@contextmanager
def get_db_cursor():
    """获取数据库游标的上下文管理器"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    cursor = conn.cursor()

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

    # 抽凭结果表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS samples (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR REFERENCES projects(id),
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
            rule_name VARCHAR,
            rule_description TEXT,
            severity VARCHAR,
            alert_message TEXT,
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

    conn.commit()
    print(f"Database initialized at {settings.DATABASE_PATH}")


def close_db():
    """关闭数据库连接"""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        _db_connection = None
        print("Database connection closed")