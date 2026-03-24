"""
合规检查服务
实现预算超标、审批流程、连号发票、周末大额交易等合规规则检查
"""
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, date
import uuid

from app.core.database import get_db_cursor, get_db
from app.utils.common import format_amount, generate_id
from app.schemas.enums import ComplianceSeverity


@dataclass
class ComplianceRule:
    """合规规则"""
    code: str
    name: str
    description: str
    severity: ComplianceSeverity
    check_func: Callable
    enabled: bool = True


@dataclass
class ComplianceAlert:
    """合规预警"""
    id: str
    project_id: str
    voucher_id: str
    voucher_no: str
    rule_code: str
    rule_name: str
    rule_description: str
    severity: ComplianceSeverity
    alert_message: str
    details: Dict[str, Any]
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComplianceCheckResult:
    """合规检查结果"""
    project_id: str
    total_checked: int
    alerts: List[ComplianceAlert]
    summary: Dict[str, int]
    checked_at: datetime


class ComplianceChecker:
    """合规检查器"""

    def __init__(self):
        self.rules: Dict[str, ComplianceRule] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        """注册默认合规规则"""

        # 1. 预算超标检查
        self.register_rule(ComplianceRule(
            code="BUDGET_EXCEED",
            name="预算超标",
            description="支出超过预算限额",
            severity=ComplianceSeverity.HIGH,
            check_func=self._check_budget_exceed
        ))

        # 2. 审批流程缺失检查
        self.register_rule(ComplianceRule(
            code="APPROVAL_MISSING",
            name="审批流程不全",
            description="缺少必要的审批签字",
            severity=ComplianceSeverity.HIGH,
            check_func=self._check_approval_missing
        ))

        # 3. 连号发票检查
        self.register_rule(ComplianceRule(
            code="SEQUENTIAL_INVOICES",
            name="连号发票",
            description="存在异常连号发票",
            severity=ComplianceSeverity.MEDIUM,
            check_func=self._check_sequential_invoices
        ))

        # 4. 周末大额交易检查
        self.register_rule(ComplianceRule(
            code="WEEKEND_LARGE_TRANSACTION",
            name="周末大额交易",
            description="周末发生的大额支出",
            severity=ComplianceSeverity.MEDIUM,
            check_func=self._check_weekend_large_transaction
        ))

        # 5. 现金超限检查
        self.register_rule(ComplianceRule(
            code="CASH_EXCEED",
            name="现金超限",
            description="现金支付超过规定限额",
            severity=ComplianceSeverity.HIGH,
            check_func=self._check_cash_exceed
        ))

        # 6. 金额异常检查
        self.register_rule(ComplianceRule(
            code="AMOUNT_ANOMALY",
            name="金额异常",
            description="金额存在异常特征",
            severity=ComplianceSeverity.MEDIUM,
            check_func=self._check_amount_anomaly
        ))

        # 7. 日期异常检查
        self.register_rule(ComplianceRule(
            code="DATE_ANOMALY",
            name="日期异常",
            description="凭证日期存在异常",
            severity=ComplianceSeverity.LOW,
            check_func=self._check_date_anomaly
        ))

        # 8. 摘要不完整检查
        self.register_rule(ComplianceRule(
            code="INCOMPLETE_DESCRIPTION",
            name="摘要不完整",
            description="凭证摘要不完整或过于简单",
            severity=ComplianceSeverity.LOW,
            check_func=self._check_incomplete_description
        ))

        # 9. 关联方交易检查
        self.register_rule(ComplianceRule(
            code="RELATED_PARTY",
            name="关联方交易",
            description="涉及关联方的交易",
            severity=ComplianceSeverity.INFO,
            check_func=self._check_related_party
        ))

        # 10. 跨期调整检查
        self.register_rule(ComplianceRule(
            code="CROSS_PERIOD",
            name="跨期调整",
            description="存在跨期调整事项",
            severity=ComplianceSeverity.MEDIUM,
            check_func=self._check_cross_period
        ))

    def register_rule(self, rule: ComplianceRule):
        """注册规则"""
        self.rules[rule.code] = rule

    def check_project(
        self,
        project_id: str,
        rule_codes: List[str] = None
    ) -> ComplianceCheckResult:
        """
        检查项目合规性

        Args:
            project_id: 项目ID
            rule_codes: 指定检查的规则代码列表（可选）

        Returns:
            ComplianceCheckResult: 检查结果
        """
        # 获取凭证数据
        vouchers = self._get_project_vouchers(project_id)

        # 确定要检查的规则
        if rule_codes:
            rules_to_check = [self.rules[code] for code in rule_codes if code in self.rules]
        else:
            rules_to_check = [r for r in self.rules.values() if r.enabled]

        # 执行检查
        all_alerts = []

        for rule in rules_to_check:
            alerts = rule.check_func(project_id, vouchers)
            all_alerts.extend(alerts)

        # 保存预警
        for alert in all_alerts:
            self._save_alert(alert)

        # 统计汇总
        summary = self._summarize_alerts(all_alerts)

        return ComplianceCheckResult(
            project_id=project_id,
            total_checked=len(vouchers),
            alerts=all_alerts,
            summary=summary,
            checked_at=datetime.now()
        )

    def check_voucher(
        self,
        project_id: str,
        voucher_id: str,
        rule_codes: List[str] = None
    ) -> List[ComplianceAlert]:
        """
        检查单个凭证合规性

        Args:
            project_id: 项目ID
            voucher_id: 凭证ID
            rule_codes: 指定检查的规则代码列表

        Returns:
            List[ComplianceAlert]: 预警列表
        """
        voucher = self._get_voucher(voucher_id)
        if not voucher:
            return []

        if rule_codes:
            rules_to_check = [self.rules[code] for code in rule_codes if code in self.rules]
        else:
            rules_to_check = [r for r in self.rules.values() if r.enabled]

        alerts = []
        for rule in rules_to_check:
            alerts.extend(rule.check_func(project_id, [voucher]))

        return alerts

    def _get_project_vouchers(self, project_id: str) -> List[Dict[str, Any]]:
        """获取项目凭证"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
                FROM vouchers
                WHERE project_id = ?
                ORDER BY voucher_date, voucher_no
                LIMIT 10000
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": row[2],
                    "amount": float(row[3]) if row[3] else 0,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7]
                }
                for row in rows
            ]

    def _get_voucher(self, voucher_id: str) -> Optional[Dict[str, Any]]:
        """获取单个凭证"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty, project_id
                FROM vouchers
                WHERE id = ?
                """,
                [voucher_id]
            )
            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "voucher_no": row[1],
                "voucher_date": row[2],
                "amount": float(row[3]) if row[3] else 0,
                "subject_code": row[4],
                "subject_name": row[5],
                "description": row[6],
                "counterparty": row[7],
                "project_id": row[8]
            }

    # ==================== 规则检查函数 ====================

    def _check_budget_exceed(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查预算超标"""
        alerts = []

        # 简化实现：检查单笔大额支出
        threshold = 100000  # 10万阈值

        for v in vouchers:
            if v["amount"] and v["amount"] > threshold:
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=v["id"],
                    voucher_no=v["voucher_no"],
                    rule_code="BUDGET_EXCEED",
                    rule_name="预算超标",
                    rule_description="单笔支出超过预算限额",
                    severity=ComplianceSeverity.HIGH,
                    alert_message=f"凭证{v['voucher_no']}金额{format_amount(v['amount'])}元超过大额阈值{format_amount(threshold)}元",
                    details={"amount": v["amount"], "threshold": threshold}
                ))

        return alerts

    def _check_approval_missing(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查审批流程缺失"""
        alerts = []

        # 检查摘要中是否包含审批相关关键词
        approval_keywords = ["审批", "核准", "签字", "批准"]

        for v in vouchers:
            if v["amount"] and v["amount"] > 50000:
                desc = v.get("description", "") or ""

                # 检查是否有审批标记（简化检查）
                has_approval = any(kw in desc for kw in approval_keywords)

                if not has_approval:
                    alerts.append(ComplianceAlert(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        voucher_id=v["id"],
                        voucher_no=v["voucher_no"],
                        rule_code="APPROVAL_MISSING",
                        rule_name="审批流程不全",
                        rule_description="大额支出缺少审批标记",
                        severity=ComplianceSeverity.HIGH,
                        alert_message=f"凭证{v['voucher_no']}金额{format_amount(v['amount'])}元，摘要中未见审批标记",
                        details={"amount": v["amount"]}
                    ))

        return alerts

    def _check_sequential_invoices(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查连号发票"""
        alerts = []

        # 提取发票号并排序
        invoice_numbers = []
        for v in vouchers:
            # 假设凭证号包含发票信息
            match = re.search(r'\d{8,}', v.get("voucher_no", ""))
            if match:
                invoice_numbers.append({
                    "voucher_id": v["id"],
                    "voucher_no": v["voucher_no"],
                    "number": int(match.group())
                })

        if len(invoice_numbers) < 2:
            return alerts

        # 排序
        invoice_numbers.sort(key=lambda x: x["number"])

        # 检查连续
        for i in range(1, len(invoice_numbers)):
            if invoice_numbers[i]["number"] - invoice_numbers[i-1]["number"] == 1:
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=invoice_numbers[i]["voucher_id"],
                    voucher_no=invoice_numbers[i]["voucher_no"],
                    rule_code="SEQUENTIAL_INVOICES",
                    rule_name="连号发票",
                    rule_description="存在连续编号的发票",
                    severity=ComplianceSeverity.MEDIUM,
                    alert_message=f"凭证{invoice_numbers[i]['voucher_no']}与{invoice_numbers[i-1]['voucher_no']}编号连续",
                    details={
                        "current": invoice_numbers[i]["voucher_no"],
                        "previous": invoice_numbers[i-1]["voucher_no"]
                    }
                ))

        return alerts

    def _check_weekend_large_transaction(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查周末大额交易"""
        alerts = []
        threshold = 50000  # 5万阈值

        for v in vouchers:
            if not v.get("voucher_date"):
                continue

            voucher_date = v["voucher_date"]
            if isinstance(voucher_date, str):
                voucher_date = datetime.strptime(voucher_date, "%Y-%m-%d").date()

            # 检查是否为周末
            weekday = voucher_date.weekday()
            if weekday >= 5 and v.get("amount", 0) > threshold:
                day_name = "周六" if weekday == 5 else "周日"
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=v["id"],
                    voucher_no=v["voucher_no"],
                    rule_code="WEEKEND_LARGE_TRANSACTION",
                    rule_name="周末大额交易",
                    rule_description=f"{day_name}发生大额支出",
                    severity=ComplianceSeverity.MEDIUM,
                    alert_message=f"凭证{v['voucher_no']}于{day_name}({voucher_date})发生金额{format_amount(v['amount'])}元",
                    details={"date": str(voucher_date), "weekday": day_name, "amount": v["amount"]}
                ))

        return alerts

    def _check_cash_exceed(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查现金超限"""
        alerts = []
        threshold = 1000  # 现金限额1000元

        cash_keywords = ["现金", "现款", "备用金"]

        for v in vouchers:
            desc = v.get("description", "") or ""
            subject = v.get("subject_name", "") or ""

            # 检查是否为现金支付
            is_cash = any(kw in desc or kw in subject for kw in cash_keywords)

            if is_cash and v.get("amount", 0) > threshold:
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=v["id"],
                    voucher_no=v["voucher_no"],
                    rule_code="CASH_EXCEED",
                    rule_name="现金超限",
                    rule_description="现金支付超过规定限额",
                    severity=ComplianceSeverity.HIGH,
                    alert_message=f"凭证{v['voucher_no']}现金支付{format_amount(v['amount'])}元超过限额{threshold}元",
                    details={"amount": v["amount"], "threshold": threshold}
                ))

        return alerts

    def _check_amount_anomaly(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查金额异常"""
        alerts = []

        for v in vouchers:
            amount = v.get("amount", 0)
            if not amount:
                continue

            anomalies = []

            # 检查超大额整数
            if amount >= 100000 and amount % 10000 == 0:
                anomalies.append("超大额整数")

            # 检查尾数异常
            if amount >= 1000 and amount % 100 == 0:
                anomalies.append("整千/整百金额")

            if anomalies:
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=v["id"],
                    voucher_no=v["voucher_no"],
                    rule_code="AMOUNT_ANOMALY",
                    rule_name="金额异常",
                    rule_description="金额存在异常特征",
                    severity=ComplianceSeverity.MEDIUM,
                    alert_message=f"凭证{v['voucher_no']}金额{format_amount(amount)}元存在异常：{', '.join(anomalies)}",
                    details={"amount": amount, "anomalies": anomalies}
                ))

        return alerts

    def _check_date_anomaly(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查日期异常"""
        alerts = []

        for v in vouchers:
            if not v.get("voucher_date"):
                continue

            voucher_date = v["voucher_date"]
            if isinstance(voucher_date, str):
                voucher_date = datetime.strptime(voucher_date, "%Y-%m-%d").date()

            # 检查月末集中
            day = voucher_date.day
            if day >= 28:
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=v["id"],
                    voucher_no=v["voucher_no"],
                    rule_code="DATE_ANOMALY",
                    rule_name="日期异常",
                    rule_description="月末集中记账",
                    severity=ComplianceSeverity.LOW,
                    alert_message=f"凭证{v['voucher_no']}记账日期为月末第{day}日",
                    details={"date": str(voucher_date), "day": day}
                ))

        return alerts

    def _check_incomplete_description(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查摘要不完整"""
        alerts = []

        for v in vouchers:
            desc = v.get("description", "") or ""

            # 检查摘要长度
            if len(desc) < 5:
                alerts.append(ComplianceAlert(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    voucher_id=v["id"],
                    voucher_no=v["voucher_no"],
                    rule_code="INCOMPLETE_DESCRIPTION",
                    rule_name="摘要不完整",
                    rule_description="凭证摘要过于简单",
                    severity=ComplianceSeverity.LOW,
                    alert_message=f"凭证{v['voucher_no']}摘要'{desc}'过于简单",
                    details={"description": desc}
                ))

        return alerts

    def _check_related_party(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查关联方交易"""
        alerts = []

        # 假设的关联方名单（实际应从数据库获取）
        related_parties = ["集团", "母公司", "子公司", "联营", "合营"]

        for v in vouchers:
            counterparty = v.get("counterparty", "") or ""
            desc = v.get("description", "") or ""

            for party in related_parties:
                if party in counterparty or party in desc:
                    alerts.append(ComplianceAlert(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        voucher_id=v["id"],
                        voucher_no=v["voucher_no"],
                        rule_code="RELATED_PARTY",
                        rule_name="关联方交易",
                        rule_description="涉及关联方的交易",
                        severity=ComplianceSeverity.INFO,
                        alert_message=f"凭证{v['voucher_no']}涉及关联方'{party}'",
                        details={"counterparty": counterparty, "related_party": party}
                    ))
                    break

        return alerts

    def _check_cross_period(
        self,
        project_id: str,
        vouchers: List[Dict[str, Any]]
    ) -> List[ComplianceAlert]:
        """检查跨期调整"""
        alerts = []

        cross_period_keywords = ["跨期", "调整", "以前年度", "上年", "预提", "待摊"]

        for v in vouchers:
            desc = v.get("description", "") or ""

            for keyword in cross_period_keywords:
                if keyword in desc:
                    alerts.append(ComplianceAlert(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        voucher_id=v["id"],
                        voucher_no=v["voucher_no"],
                        rule_code="CROSS_PERIOD",
                        rule_name="跨期调整",
                        rule_description="存在跨期调整事项",
                        severity=ComplianceSeverity.MEDIUM,
                        alert_message=f"凭证{v['voucher_no']}摘要包含'{keyword}'关键词",
                        details={"keyword": keyword, "description": desc}
                    ))
                    break

        return alerts

    def _summarize_alerts(self, alerts: List[ComplianceAlert]) -> Dict[str, int]:
        """汇总预警统计"""
        summary = {
            "total": len(alerts),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "by_rule": {}
        }

        for alert in alerts:
            severity = alert.severity.value
            summary[severity] = summary.get(severity, 0) + 1

            rule_code = alert.rule_code
            summary["by_rule"][rule_code] = summary["by_rule"].get(rule_code, 0) + 1

        return summary

    def _save_alert(self, alert: ComplianceAlert):
        """保存预警"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO compliance_alerts
                (id, project_id, voucher_id, rule_name, rule_description,
                 severity, alert_message, is_resolved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    alert.id,
                    alert.project_id,
                    alert.voucher_id,
                    alert.rule_name,
                    alert.rule_description,
                    alert.severity.value,
                    alert.alert_message,
                    alert.is_resolved,
                    alert.created_at
                ]
            )
            get_db().commit()

    def get_alerts(
        self,
        project_id: str,
        severity: ComplianceSeverity = None,
        resolved: bool = None
    ) -> List[ComplianceAlert]:
        """获取预警列表"""
        with get_db_cursor() as cursor:
            conditions = ["project_id = ?"]
            params = [project_id]

            if severity:
                conditions.append("severity = ?")
                params.append(severity.value)

            if resolved is not None:
                conditions.append("is_resolved = ?")
                params.append(resolved)

            where_clause = " AND ".join(conditions)

            cursor.execute(
                f"""
                SELECT id, project_id, voucher_id, rule_name, rule_description,
                       severity, alert_message, is_resolved, resolved_at, created_at
                FROM compliance_alerts
                WHERE {where_clause}
                ORDER BY created_at DESC
                """,
                params
            )
            rows = cursor.fetchall()

            return [
                ComplianceAlert(
                    id=row[0],
                    project_id=row[1],
                    voucher_id=row[2],
                    voucher_no="",
                    rule_code="",
                    rule_name=row[3],
                    rule_description=row[4],
                    severity=ComplianceSeverity(row[5]),
                    alert_message=row[6],
                    details={},
                    is_resolved=bool(row[7]),
                    resolved_at=row[8],
                    created_at=row[9]
                )
                for row in rows
            ]

    def resolve_alert(self, alert_id: str, resolved_by: str = None):
        """标记预警为已处理"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE compliance_alerts
                SET is_resolved = TRUE, resolved_at = ?
                WHERE id = ?
                """,
                [datetime.now(), alert_id]
            )
            get_db().commit()


# 全局服务实例
compliance_checker = ComplianceChecker()