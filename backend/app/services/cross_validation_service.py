"""
交叉验证服务
与银行流水、纳税申报表等外部数据进行交叉验证
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db


class ValidationSource(str, Enum):
    """验证数据源"""
    BANK_STATEMENT = "bank_statement"      # 银行对账单
    TAX_RETURN = "tax_return"              # 纳税申报表
    CONTRACT_LEDGER = "contract_ledger"    # 合同台账
    INVENTORY_RECORD = "inventory_record"  # 库存盘点记录
    PAYROLL_RECORD = "payroll_record"      # 薪酬记录


class ValidationStatus(str, Enum):
    """验证状态"""
    MATCHED = "matched"          # 匹配
    DIFFERENCE = "difference"    # 差异
    MISSING = "missing"          # 缺失
    EXCEPTION = "exception"      # 异常


@dataclass
class ValidationItem:
    """验证项"""
    field: str
    voucher_value: Any
    external_value: Any
    difference: Any
    status: ValidationStatus


@dataclass
class ValidationResult:
    """验证结果"""
    id: str
    project_id: str
    voucher_id: str
    voucher_no: str
    validation_source: ValidationSource
    status: ValidationStatus
    match_score: float
    items: List[ValidationItem]
    summary: str
    recommendations: List[str]
    validated_at: datetime


@dataclass
class ExternalData:
    """外部数据"""
    source: ValidationSource
    date: date
    amount: float
    counterparty: str
    reference_no: str
    description: str
    raw_data: Dict[str, Any] = field(default_factory=dict)


class CrossValidator:
    """交叉验证器"""

    def __init__(self):
        self.amount_tolerance = 0.01  # 金额容差
        self.date_tolerance = 3        # 日期容差（天）

    def validate_with_bank(
        self,
        project_id: str,
        voucher_id: str,
        bank_statements: List[ExternalData]
    ) -> ValidationResult:
        """
        与银行流水验证

        Args:
            project_id: 项目ID
            voucher_id: 凭证ID
            bank_statements: 银行流水数据

        Returns:
            ValidationResult: 验证结果
        """
        voucher = self._get_voucher(voucher_id)
        if not voucher:
            raise ValueError(f"凭证不存在: {voucher_id}")

        # 查找匹配的银行流水
        matched_statement = self._find_matching_bank_statement(voucher, bank_statements)

        # 执行验证
        items = self._validate_bank_items(voucher, matched_statement)

        # 确定状态
        status, score = self._determine_validation_status(items)

        # 生成摘要和建议
        summary = self._generate_bank_summary(voucher, matched_statement, items)
        recommendations = self._generate_bank_recommendations(status, items)

        result = ValidationResult(
            id=str(uuid.uuid4()),
            project_id=project_id,
            voucher_id=voucher_id,
            voucher_no=voucher["voucher_no"],
            validation_source=ValidationSource.BANK_STATEMENT,
            status=status,
            match_score=score,
            items=items,
            summary=summary,
            recommendations=recommendations,
            validated_at=datetime.now()
        )

        return result

    def validate_with_tax(
        self,
        project_id: str,
        voucher_id: str,
        tax_returns: List[ExternalData]
    ) -> ValidationResult:
        """
        与纳税申报表验证

        Args:
            project_id: 项目ID
            voucher_id: 凭证ID
            tax_returns: 纳税申报数据

        Returns:
            ValidationResult: 验证结果
        """
        voucher = self._get_voucher(voucher_id)
        if not voucher:
            raise ValueError(f"凭证不存在: {voucher_id}")

        # 查找匹配的税务记录
        matched_tax = self._find_matching_tax_record(voucher, tax_returns)

        # 执行验证
        items = self._validate_tax_items(voucher, matched_tax)

        # 确定状态
        status, score = self._determine_validation_status(items)

        # 生成摘要和建议
        summary = self._generate_tax_summary(voucher, matched_tax, items)
        recommendations = self._generate_tax_recommendations(status, items)

        result = ValidationResult(
            id=str(uuid.uuid4()),
            project_id=project_id,
            voucher_id=voucher_id,
            voucher_no=voucher["voucher_no"],
            validation_source=ValidationSource.TAX_RETURN,
            status=status,
            match_score=score,
            items=items,
            summary=summary,
            recommendations=recommendations,
            validated_at=datetime.now()
        )

        return result

    def batch_validate(
        self,
        project_id: str,
        voucher_ids: List[str],
        external_data: Dict[str, List[ExternalData]]
    ) -> List[ValidationResult]:
        """
        批量验证

        Args:
            project_id: 项目ID
            voucher_ids: 凭证ID列表
            external_data: 外部数据字典

        Returns:
            List[ValidationResult]: 验证结果列表
        """
        results = []

        bank_statements = external_data.get("bank_statements", [])
        tax_returns = external_data.get("tax_returns", [])

        for voucher_id in voucher_ids:
            # 银行流水验证
            if bank_statements:
                try:
                    result = self.validate_with_bank(project_id, voucher_id, bank_statements)
                    results.append(result)
                except Exception as e:
                    results.append(self._create_error_result(project_id, voucher_id, str(e)))

            # 税务验证
            if tax_returns:
                try:
                    result = self.validate_with_tax(project_id, voucher_id, tax_returns)
                    results.append(result)
                except Exception as e:
                    results.append(self._create_error_result(project_id, voucher_id, str(e)))

        return results

    def _get_voucher(self, voucher_id: str) -> Optional[Dict[str, Any]]:
        """获取凭证"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
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
                "counterparty": row[7]
            }

    def _find_matching_bank_statement(
        self,
        voucher: Dict[str, Any],
        statements: List[ExternalData]
    ) -> Optional[ExternalData]:
        """查找匹配的银行流水"""
        candidates = []

        for stmt in statements:
            score = 0

            # 金额匹配
            if voucher.get("amount") and stmt.amount:
                diff = abs(voucher["amount"] - stmt.amount)
                if diff == 0:
                    score += 50
                elif diff / max(voucher["amount"], stmt.amount) <= self.amount_tolerance:
                    score += 40
                elif diff / max(voucher["amount"], stmt.amount) <= 0.05:
                    score += 20

            # 日期匹配
            if voucher.get("voucher_date") and stmt.date:
                voucher_date = voucher["voucher_date"]
                if isinstance(voucher_date, str):
                    voucher_date = datetime.strptime(voucher_date, "%Y-%m-%d").date()

                days_diff = abs((voucher_date - stmt.date).days)
                if days_diff == 0:
                    score += 30
                elif days_diff <= self.date_tolerance:
                    score += 20

            # 交易对手匹配
            if voucher.get("counterparty") and stmt.counterparty:
                if voucher["counterparty"] == stmt.counterparty:
                    score += 20
                elif voucher["counterparty"] in stmt.counterparty or stmt.counterparty in voucher["counterparty"]:
                    score += 10

            if score >= 40:
                candidates.append((stmt, score))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def _find_matching_tax_record(
        self,
        voucher: Dict[str, Any],
        tax_records: List[ExternalData]
    ) -> Optional[ExternalData]:
        """查找匹配的税务记录"""
        # 检查是否为税务相关科目
        tax_subjects = ["2221", "6403", "6801"]  # 应交税费、税金及附加、所得税费用
        subject_code = voucher.get("subject_code", "") or ""

        is_tax_voucher = any(subject_code.startswith(ts) for ts in tax_subjects)

        if not is_tax_voucher:
            return None

        candidates = []

        for record in tax_records:
            score = 0

            # 金额匹配
            if voucher.get("amount") and record.amount:
                diff = abs(voucher["amount"] - record.amount)
                if diff / max(voucher["amount"], record.amount) <= 0.05:
                    score += 50

            # 日期匹配（同一月份）
            if voucher.get("voucher_date") and record.date:
                voucher_date = voucher["voucher_date"]
                if isinstance(voucher_date, str):
                    voucher_date = datetime.strptime(voucher_date, "%Y-%m-%d").date()

                if voucher_date.year == record.date.year and voucher_date.month == record.date.month:
                    score += 30

            if score >= 50:
                candidates.append((record, score))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def _validate_bank_items(
        self,
        voucher: Dict[str, Any],
        statement: Optional[ExternalData]
    ) -> List[ValidationItem]:
        """验证银行项目"""
        items = []

        # 金额验证
        voucher_amount = voucher.get("amount", 0)
        bank_amount = statement.amount if statement else None

        if statement:
            diff = voucher_amount - bank_amount
            status = ValidationStatus.MATCHED if abs(diff) <= voucher_amount * self.amount_tolerance else ValidationStatus.DIFFERENCE
        else:
            diff = None
            status = ValidationStatus.MISSING

        items.append(ValidationItem(
            field="金额",
            voucher_value=voucher_amount,
            external_value=bank_amount,
            difference=diff,
            status=status
        ))

        # 日期验证
        voucher_date = voucher.get("voucher_date")
        bank_date = statement.date if statement else None

        if statement and voucher_date and bank_date:
            if isinstance(voucher_date, str):
                voucher_date = datetime.strptime(voucher_date, "%Y-%m-%d").date()

            days_diff = (voucher_date - bank_date).days
            status = ValidationStatus.MATCHED if abs(days_diff) <= self.date_tolerance else ValidationStatus.DIFFERENCE
        else:
            days_diff = None
            status = ValidationStatus.MISSING

        items.append(ValidationItem(
            field="日期",
            voucher_value=str(voucher_date) if voucher_date else None,
            external_value=str(bank_date) if bank_date else None,
            difference=days_diff,
            status=status
        ))

        # 交易对手验证
        voucher_counterparty = voucher.get("counterparty")
        bank_counterparty = statement.counterparty if statement else None

        if statement and voucher_counterparty and bank_counterparty:
            matched = voucher_counterparty == bank_counterparty or \
                     voucher_counterparty in bank_counterparty or \
                     bank_counterparty in voucher_counterparty
            status = ValidationStatus.MATCHED if matched else ValidationStatus.DIFFERENCE
        else:
            status = ValidationStatus.MISSING

        items.append(ValidationItem(
            field="交易对手",
            voucher_value=voucher_counterparty,
            external_value=bank_counterparty,
            difference=None,
            status=status
        ))

        return items

    def _validate_tax_items(
        self,
        voucher: Dict[str, Any],
        tax_record: Optional[ExternalData]
    ) -> List[ValidationItem]:
        """验证税务项目"""
        items = []

        # 税额验证
        voucher_amount = voucher.get("amount", 0)
        tax_amount = tax_record.amount if tax_record else None

        if tax_record:
            diff = voucher_amount - tax_amount
            status = ValidationStatus.MATCHED if abs(diff) <= voucher_amount * 0.05 else ValidationStatus.DIFFERENCE
        else:
            diff = None
            status = ValidationStatus.MISSING

        items.append(ValidationItem(
            field="税额",
            voucher_value=voucher_amount,
            external_value=tax_amount,
            difference=diff,
            status=status
        ))

        # 申报期间验证
        voucher_date = voucher.get("voucher_date")
        tax_period = tax_record.date if tax_record else None

        if tax_record and voucher_date and tax_period:
            if isinstance(voucher_date, str):
                voucher_date = datetime.strptime(voucher_date, "%Y-%m-%d").date()

            same_period = voucher_date.year == tax_period.year and voucher_date.month == tax_period.month
            status = ValidationStatus.MATCHED if same_period else ValidationStatus.DIFFERENCE
        else:
            status = ValidationStatus.MISSING

        items.append(ValidationItem(
            field="申报期间",
            voucher_value=f"{voucher_date.year}-{voucher_date.month}" if voucher_date else None,
            external_value=f"{tax_period.year}-{tax_period.month}" if tax_period else None,
            difference=None,
            status=status
        ))

        return items

    def _determine_validation_status(
        self,
        items: List[ValidationItem]
    ) -> tuple:
        """确定验证状态"""
        if not items:
            return ValidationStatus.EXCEPTION, 0

        matched_count = sum(1 for item in items if item.status == ValidationStatus.MATCHED)
        total_count = len(items)

        score = matched_count / total_count if total_count > 0 else 0

        if score == 1.0:
            return ValidationStatus.MATCHED, score
        elif score >= 0.5:
            return ValidationStatus.DIFFERENCE, score
        else:
            return ValidationStatus.MISSING, score

    def _generate_bank_summary(
        self,
        voucher: Dict[str, Any],
        statement: Optional[ExternalData],
        items: List[ValidationItem]
    ) -> str:
        """生成银行验证摘要"""
        if not statement:
            return f"凭证{voucher['voucher_no']}未找到匹配的银行流水记录"

        matched_items = [i for i in items if i.status == ValidationStatus.MATCHED]
        diff_items = [i for i in items if i.status == ValidationStatus.DIFFERENCE]

        summary = f"凭证{voucher['voucher_no']}与银行流水核对："

        if matched_items:
            summary += f"{len(matched_items)}项匹配"

        if diff_items:
            summary += f"，{len(diff_items)}项存在差异"

        return summary

    def _generate_bank_recommendations(
        self,
        status: ValidationStatus,
        items: List[ValidationItem]
    ) -> List[str]:
        """生成银行验证建议"""
        recommendations = []

        if status == ValidationStatus.MATCHED:
            recommendations.append("银行流水核对一致")
        elif status == ValidationStatus.DIFFERENCE:
            for item in items:
                if item.status == ValidationStatus.DIFFERENCE:
                    if item.field == "金额":
                        recommendations.append(f"金额差异{item.difference:,.2f}元，建议核实")
                    elif item.field == "日期":
                        recommendations.append(f"日期相差{abs(item.difference)}天，关注跨期问题")
                    elif item.field == "交易对手":
                        recommendations.append("交易对手不一致，建议核实")
        elif status == ValidationStatus.MISSING:
            recommendations.append("未找到匹配的银行流水，请核实是否遗漏")

        return recommendations

    def _generate_tax_summary(
        self,
        voucher: Dict[str, Any],
        tax_record: Optional[ExternalData],
        items: List[ValidationItem]
    ) -> str:
        """生成税务验证摘要"""
        if not tax_record:
            return f"凭证{voucher['voucher_no']}未找到匹配的税务申报记录"

        matched_items = [i for i in items if i.status == ValidationStatus.MATCHED]
        diff_items = [i for i in items if i.status == ValidationStatus.DIFFERENCE]

        summary = f"凭证{voucher['voucher_no']}与税务申报核对："

        if matched_items:
            summary += f"{len(matched_items)}项匹配"

        if diff_items:
            summary += f"，{len(diff_items)}项存在差异"

        return summary

    def _generate_tax_recommendations(
        self,
        status: ValidationStatus,
        items: List[ValidationItem]
    ) -> List[str]:
        """生成税务验证建议"""
        recommendations = []

        if status == ValidationStatus.MATCHED:
            recommendations.append("税务申报核对一致")
        elif status == ValidationStatus.DIFFERENCE:
            for item in items:
                if item.status == ValidationStatus.DIFFERENCE:
                    if item.field == "税额":
                        recommendations.append(f"税额差异{item.difference:,.2f}元，建议核实申报")
                    elif item.field == "申报期间":
                        recommendations.append("申报期间不一致，关注税务风险")
        elif status == ValidationStatus.MISSING:
            recommendations.append("未找到匹配的税务申报，请核实是否遗漏申报")

        return recommendations

    def _create_error_result(
        self,
        project_id: str,
        voucher_id: str,
        error_message: str
    ) -> ValidationResult:
        """创建错误结果"""
        return ValidationResult(
            id=str(uuid.uuid4()),
            project_id=project_id,
            voucher_id=voucher_id,
            voucher_no="",
            validation_source=ValidationSource.BANK_STATEMENT,
            status=ValidationStatus.EXCEPTION,
            match_score=0,
            items=[],
            summary=f"验证异常: {error_message}",
            recommendations=[],
            validated_at=datetime.now()
        )

    def import_bank_statements(
        self,
        project_id: str,
        statements: List[Dict[str, Any]]
    ) -> int:
        """
        导入银行流水数据

        Args:
            project_id: 项目ID
            statements: 银行流水数据列表

        Returns:
            int: 导入数量
        """
        # 创建临时表存储银行流水
        with get_db_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bank_statements (
                    id VARCHAR PRIMARY KEY,
                    project_id VARCHAR,
                    statement_date DATE,
                    amount DECIMAL(18, 2),
                    counterparty VARCHAR,
                    reference_no VARCHAR,
                    description TEXT,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            count = 0
            for stmt in statements:
                stmt_id = str(uuid.uuid4())

                cursor.execute(
                    """
                    INSERT INTO bank_statements
                    (id, project_id, statement_date, amount, counterparty, reference_no, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        stmt_id,
                        project_id,
                        stmt.get("date"),
                        stmt.get("amount"),
                        stmt.get("counterparty"),
                        stmt.get("reference_no"),
                        stmt.get("description")
                    ]
                )
                count += 1

            get_db().commit()

        return count

    def get_bank_statements(self, project_id: str) -> List[ExternalData]:
        """获取银行流水数据"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT statement_date, amount, counterparty, reference_no, description
                FROM bank_statements
                WHERE project_id = ?
                ORDER BY statement_date
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                ExternalData(
                    source=ValidationSource.BANK_STATEMENT,
                    date=row[0],
                    amount=float(row[1]) if row[1] else 0,
                    counterparty=row[2] or "",
                    reference_no=row[3] or "",
                    description=row[4] or ""
                )
                for row in rows
            ]


# 全局服务实例
cross_validator = CrossValidator()