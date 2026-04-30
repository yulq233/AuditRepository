"""
风险配置服务
提供风险权重、阈值、规则的配置管理功能
"""
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid

from app.core.database import get_db_cursor, get_db

logger = logging.getLogger(__name__)


# 默认风险权重配置
DEFAULT_WEIGHTS = {
    "amount_significance": 0.25,      # 金额重要性
    "business_complexity": 0.20,      # 业务复杂性
    "historical_issues": 0.20,        # 历史问题
    "industry_risk": 0.15,            # 行业风险
    "anomaly_indicators": 0.20,       # 异常指标
    "counterparty_risk": 0.0,         # 交易对手风险（新增，默认0保持兼容）
    "time_risk": 0.0,                 # 时间风险（新增，默认0保持兼容）
    "document_completeness": 0.0      # 文档完整性（新增，默认0保持兼容）
}

# 默认风险阈值配置
DEFAULT_THRESHOLDS = {
    "high": 70,     # 高风险阈值
    "medium": 50,   # 中风险阈值
    "low": 0        # 低风险阈值
}

# 默认规则开关配置
DEFAULT_RULES = {
    # 金额类规则
    "large_amount_check": {"enabled": True, "name": "大额交易检查", "description": "检查金额超过10万的交易"},
    "super_large_amount_check": {"enabled": True, "name": "超大额交易检查", "description": "检查金额超过50万的交易"},
    "round_amount_check": {"enabled": True, "name": "整数金额检查", "description": "检查金额为整数万的交易"},

    # 时间类规则
    "weekend_check": {"enabled": True, "name": "周末交易检查", "description": "检查周末发生的交易"},
    "month_end_check": {"enabled": True, "name": "月末集中检查", "description": "检查月末最后5天的交易"},
    "year_end_check": {"enabled": True, "name": "年末交易检查", "description": "检查年末集中发生的交易"},

    # 交易对手类规则
    "related_party_check": {"enabled": True, "name": "关联方检查", "description": "检查关联方交易"},
    "new_customer_check": {"enabled": True, "name": "新客户检查", "description": "检查新客户/供应商交易"},
    "concentration_check": {"enabled": True, "name": "集中度检查", "description": "检查交易对手集中度"},

    # 业务类规则
    "sensitive_keyword_check": {"enabled": True, "name": "敏感词检查", "description": "检查摘要中的敏感词"},
    "vague_description_check": {"enabled": True, "name": "模糊摘要检查", "description": "检查摘要描述模糊的交易"},

    # 科目类规则
    "high_risk_subject_check": {"enabled": True, "name": "高风险科目检查", "description": "检查应收账款、收入等高风险科目"},
    "attention_subject_check": {"enabled": True, "name": "关注科目检查", "description": "检查库存、固定资产等关注科目"}
}


@dataclass
class RiskConfig:
    """风险配置"""
    id: str
    project_id: str
    config_type: str
    config_name: str
    config_data: Dict[str, Any]
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RiskConfigService:
    """风险配置服务"""

    def __init__(self):
        self.default_weights = DEFAULT_WEIGHTS.copy()
        self.default_thresholds = DEFAULT_THRESHOLDS.copy()
        self.default_rules = DEFAULT_RULES.copy()

    def get_weights(self, project_id: str) -> Dict[str, Any]:
        """
        获取风险权重配置

        Args:
            project_id: 项目ID

        Returns:
            Dict: 权重配置
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT config_data FROM risk_configurations
                WHERE project_id = ? AND config_type = 'weights' AND is_active = TRUE
                ORDER BY updated_at DESC LIMIT 1
                """,
                [project_id]
            )
            row = cursor.fetchone()

            if row:
                config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                return {**self.default_weights, **config}

            return self.default_weights.copy()

    def update_weights(
        self,
        project_id: str,
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        更新风险权重配置

        Args:
            project_id: 项目ID
            weights: 新的权重配置

        Returns:
            Dict: 更新后的配置
        """
        # 验证权重总和
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            # 自动归一化
            weights = {k: v / total for k, v in weights.items()}

        with get_db_cursor() as cursor:
            # 停用旧配置
            cursor.execute(
                """
                UPDATE risk_configurations
                SET is_active = FALSE
                WHERE project_id = ? AND config_type = 'weights'
                """,
                [project_id]
            )

            # 插入新配置
            config_id = str(uuid.uuid4())
            now = datetime.now()
            cursor.execute(
                """
                INSERT INTO risk_configurations
                (id, project_id, config_type, config_name, config_data, is_default, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    config_id,
                    project_id,
                    "weights",
                    "风险权重配置",
                    json.dumps(weights, ensure_ascii=False),
                    False,
                    True,
                    now,
                    now
                ]
            )
            get_db().commit()

        return weights

    def get_thresholds(self, project_id: str) -> Dict[str, Any]:
        """
        获取风险阈值配置

        Args:
            project_id: 项目ID

        Returns:
            Dict: 阈值配置
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT config_data FROM risk_configurations
                WHERE project_id = ? AND config_type = 'thresholds' AND is_active = TRUE
                ORDER BY updated_at DESC LIMIT 1
                """,
                [project_id]
            )
            row = cursor.fetchone()

            if row:
                config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                return {**self.default_thresholds, **config}

            return self.default_thresholds.copy()

    def update_thresholds(
        self,
        project_id: str,
        thresholds: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        更新风险阈值配置

        Args:
            project_id: 项目ID
            thresholds: 新的阈值配置

        Returns:
            Dict: 更新后的配置
        """
        # 验证阈值逻辑
        high = thresholds.get('high', 70)
        medium = thresholds.get('medium', 50)

        if high <= medium:
            raise ValueError("高风险阈值必须大于中风险阈值")
        if medium <= 0:
            raise ValueError("中风险阈值必须大于0")

        with get_db_cursor() as cursor:
            # 停用旧配置
            cursor.execute(
                """
                UPDATE risk_configurations
                SET is_active = FALSE
                WHERE project_id = ? AND config_type = 'thresholds'
                """,
                [project_id]
            )

            # 插入新配置
            config_id = str(uuid.uuid4())
            now = datetime.now()
            cursor.execute(
                """
                INSERT INTO risk_configurations
                (id, project_id, config_type, config_name, config_data, is_default, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    config_id,
                    project_id,
                    "thresholds",
                    "风险阈值配置",
                    json.dumps(thresholds, ensure_ascii=False),
                    False,
                    True,
                    now,
                    now
                ]
            )
            get_db().commit()

        return thresholds

    def get_rules(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取风险规则列表

        Args:
            project_id: 项目ID

        Returns:
            List[Dict]: 规则列表
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT config_data FROM risk_configurations
                WHERE project_id = ? AND config_type = 'rules' AND is_active = TRUE
                ORDER BY updated_at DESC LIMIT 1
                """,
                [project_id]
            )
            row = cursor.fetchone()

            if row:
                config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                # 合并默认规则
                merged = {}
                for code, rule in self.default_rules.items():
                    merged[code] = {
                        **rule,
                        "enabled": config.get(code, {}).get("enabled", rule["enabled"])
                    }
                return [
                    {"code": code, **rule}
                    for code, rule in merged.items()
                ]

            return [
                {"code": code, **rule}
                for code, rule in self.default_rules.items()
            ]

    def toggle_rule(
        self,
        project_id: str,
        rule_code: str,
        enabled: bool
    ) -> Dict[str, Any]:
        """
        切换规则开关

        Args:
            project_id: 项目ID
            rule_code: 规则代码
            enabled: 是否启用

        Returns:
            Dict: 操作结果
        """
        if rule_code not in self.default_rules:
            raise ValueError(f"未知规则代码: {rule_code}")

        with get_db_cursor() as cursor:
            # 获取当前配置
            cursor.execute(
                """
                SELECT id, config_data FROM risk_configurations
                WHERE project_id = ? AND config_type = 'rules' AND is_active = TRUE
                ORDER BY updated_at DESC LIMIT 1
                """,
                [project_id]
            )
            row = cursor.fetchone()

            if row:
                config_id = row[0]
                config = json.loads(row[1]) if isinstance(row[1], str) else row[1]
            else:
                config_id = str(uuid.uuid4())
                config = {}

            # 更新规则状态
            if rule_code not in config:
                config[rule_code] = {}
            config[rule_code]["enabled"] = enabled

            if row:
                # 更新现有配置
                cursor.execute(
                    """
                    UPDATE risk_configurations
                    SET config_data = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    [json.dumps(config, ensure_ascii=False), datetime.now(), config_id]
                )
            else:
                # 插入新配置
                now = datetime.now()
                cursor.execute(
                    """
                    INSERT INTO risk_configurations
                    (id, project_id, config_type, config_name, config_data, is_default, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        config_id,
                        project_id,
                        "rules",
                        "风险规则配置",
                        json.dumps(config, ensure_ascii=False),
                        False,
                        True,
                        now,
                        now
                    ]
                )
            get_db().commit()

        return {
            "code": rule_code,
            "enabled": enabled,
            "message": f"规则{rule_code}已{'启用' if enabled else '禁用'}"
        }

    def save_template(
        self,
        project_id: str,
        template_name: str
    ) -> Dict[str, Any]:
        """
        保存当前配置为模板

        Args:
            project_id: 项目ID
            template_name: 模板名称

        Returns:
            Dict: 操作结果
        """
        # 获取当前所有配置
        weights = self.get_weights(project_id)
        thresholds = self.get_thresholds(project_id)
        rules = {r["code"]: r["enabled"] for r in self.get_rules(project_id)}

        template_data = {
            "weights": weights,
            "thresholds": thresholds,
            "rules": rules
        }

        with get_db_cursor() as cursor:
            # 检查是否已存在同名模板
            cursor.execute(
                """
                SELECT id FROM risk_configurations
                WHERE project_id = ? AND config_type = 'template' AND config_name = ?
                """,
                [project_id, template_name]
            )
            existing = cursor.fetchone()

            now = datetime.now()
            if existing:
                # 更新现有模板
                cursor.execute(
                    """
                    UPDATE risk_configurations
                    SET config_data = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    [json.dumps(template_data, ensure_ascii=False), now, existing[0]]
                )
            else:
                # 创建新模板
                cursor.execute(
                    """
                    INSERT INTO risk_configurations
                    (id, project_id, config_type, config_name, config_data, is_default, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        str(uuid.uuid4()),
                        project_id,
                        "template",
                        template_name,
                        json.dumps(template_data, ensure_ascii=False),
                        False,
                        True,
                        now,
                        now
                    ]
                )
            get_db().commit()

        return {
            "success": True,
            "template_name": template_name,
            "message": f"模板'{template_name}'保存成功"
        }

    def load_template(
        self,
        project_id: str,
        template_name: str
    ) -> Dict[str, Any]:
        """
        加载配置模板

        Args:
            project_id: 项目ID
            template_name: 模板名称

        Returns:
            Dict: 加载的配置
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT config_data FROM risk_configurations
                WHERE project_id = ? AND config_type = 'template' AND config_name = ?
                """,
                [project_id, template_name]
            )
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"模板'{template_name}'不存在")

            template_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]

        # 应用模板配置
        if "weights" in template_data:
            self.update_weights(project_id, template_data["weights"])
        if "thresholds" in template_data:
            self.update_thresholds(project_id, template_data["thresholds"])
        if "rules" in template_data:
            for code, enabled in template_data["rules"].items():
                self.toggle_rule(project_id, code, enabled)

        return {
            "success": True,
            "template_name": template_name,
            "message": f"模板'{template_name}'加载成功",
            "config": template_data
        }

    def get_templates(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取配置模板列表

        Args:
            project_id: 项目ID

        Returns:
            List[Dict]: 模板列表
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, config_name, created_at, updated_at
                FROM risk_configurations
                WHERE project_id = ? AND config_type = 'template'
                ORDER BY updated_at DESC
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "created_at": str(row[2]) if row[2] else None,
                    "updated_at": str(row[3]) if row[3] else None
                }
                for row in rows
            ]

    def delete_template(
        self,
        project_id: str,
        template_name: str
    ) -> Dict[str, Any]:
        """
        删除配置模板

        Args:
            project_id: 项目ID
            template_name: 模板名称

        Returns:
            Dict: 操作结果
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM risk_configurations
                WHERE project_id = ? AND config_type = 'template' AND config_name = ?
                """,
                [project_id, template_name]
            )
            get_db().commit()

        return {
            "success": True,
            "template_name": template_name,
            "message": f"模板'{template_name}'删除成功"
        }

    def get_full_config(self, project_id: str) -> Dict[str, Any]:
        """
        获取完整配置

        Args:
            project_id: 项目ID

        Returns:
            Dict: 完整配置
        """
        return {
            "weights": self.get_weights(project_id),
            "thresholds": self.get_thresholds(project_id),
            "rules": self.get_rules(project_id),
            "templates": self.get_templates(project_id)
        }

    def reset_to_default(self, project_id: str) -> Dict[str, Any]:
        """
        重置为默认配置

        Args:
            project_id: 项目ID

        Returns:
            Dict: 操作结果
        """
        with get_db_cursor() as cursor:
            # 停用所有现有配置
            cursor.execute(
                """
                UPDATE risk_configurations
                SET is_active = FALSE
                WHERE project_id = ? AND config_type IN ('weights', 'thresholds', 'rules')
                """,
                [project_id]
            )
            get_db().commit()

        return {
            "success": True,
            "message": "已重置为默认配置",
            "config": self.get_full_config(project_id)
        }


# 全局服务实例
risk_config_service = RiskConfigService()