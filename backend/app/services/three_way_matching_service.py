"""
三单匹配服务
自动将采购发票、采购订单与入库单的关键信息进行核对，标记差异
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
import uuid

from app.core.database import get_db_cursor, get_db
from app.schemas.enums import MatchStatus
from app.utils.common import format_amount, generate_id
from enum import Enum


class DocumentType(str, Enum):
    """单据类型"""
    INVOICE = "invoice"          # 发票
    PURCHASE_ORDER = "purchase_order"  # 采购订单
    RECEIPT = "receipt"          # 入库单


@dataclass
class MatchDifference:
    """差异项"""
    field: str
    invoice_value: Any
    order_value: Any
    receipt_value: Any
    difference_description: str


@dataclass
class MatchResult:
    """匹配结果"""
    id: str
    project_id: str
    invoice_id: str
    invoice_no: str
    order_id: Optional[str]
    order_no: Optional[str]
    receipt_id: Optional[str]
    receipt_no: Optional[str]
    match_status: MatchStatus
    match_score: float
    amount_difference: float
    quantity_difference: int
    date_difference: int  # 天数
    differences: List[MatchDifference]
    suggestions: List[str]
    matched_at: datetime


@dataclass
class DocumentInfo:
    """单据信息"""
    id: str
    document_no: str
    document_type: DocumentType
    date: Optional[date]
    amount: float
    quantity: int = 0
    supplier: str = ""
    product_name: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


class ThreeWayMatcher:
    """三单匹配器"""

    def __init__(self):
        self.amount_tolerance = 0.01  # 金额容差（1%）
        self.date_tolerance = 30       # 日期容差（30天）
        self.quantity_tolerance = 0    # 数量容差

    def match(
        self,
        project_id: str,
        invoices: List[DocumentInfo],
        orders: List[DocumentInfo],
        receipts: List[DocumentInfo]
    ) -> List[MatchResult]:
        """
        执行三单匹配

        Args:
            project_id: 项目ID
            invoices: 发票列表
            orders: 采购订单列表
            receipts: 入库单列表

        Returns:
            List[MatchResult]: 匹配结果列表
        """
        results = []

        for invoice in invoices:
            result = self._match_single_invoice(
                project_id, invoice, orders, receipts
            )
            results.append(result)

            # 保存结果
            self._save_match_result(result)

        return results

    def match_from_database(
        self,
        project_id: str,
        invoice_ids: List[str] = None
    ) -> List[MatchResult]:
        """
        从数据库获取数据并执行匹配

        Args:
            project_id: 项目ID
            invoice_ids: 指定发票ID列表（可选）

        Returns:
            List[MatchResult]: 匹配结果列表
        """
        # 从数据库获取单据
        invoices, orders, receipts = self._load_documents_from_db(project_id, invoice_ids)

        return self.match(project_id, invoices, orders, receipts)

    def _match_single_invoice(
        self,
        project_id: str,
        invoice: DocumentInfo,
        orders: List[DocumentInfo],
        receipts: List[DocumentInfo]
    ) -> MatchResult:
        """匹配单个发票"""
        # 查找匹配的订单
        matched_order = self._find_matching_order(invoice, orders)

        # 查找匹配的入库单
        matched_receipt = self._find_matching_receipt(invoice, receipts, matched_order)

        # 计算差异
        differences = self._calculate_differences(invoice, matched_order, matched_receipt)

        # 确定匹配状态
        match_status, match_score = self._determine_match_status(
            invoice, matched_order, matched_receipt, differences
        )

        # 计算金额差异
        amount_diff = self._calculate_amount_difference(invoice, matched_order, matched_receipt)

        # 计算日期差异
        date_diff = self._calculate_date_difference(invoice, matched_order, matched_receipt)

        # 生成建议
        suggestions = self._generate_suggestions(match_status, differences)

        return MatchResult(
            id=str(uuid.uuid4()),
            project_id=project_id,
            invoice_id=invoice.id,
            invoice_no=invoice.document_no,
            order_id=matched_order.id if matched_order else None,
            order_no=matched_order.document_no if matched_order else None,
            receipt_id=matched_receipt.id if matched_receipt else None,
            receipt_no=matched_receipt.document_no if matched_receipt else None,
            match_status=match_status,
            match_score=match_score,
            amount_difference=amount_diff,
            quantity_difference=0,
            date_difference=date_diff,
            differences=differences,
            suggestions=suggestions,
            matched_at=datetime.now()
        )

    def _find_matching_order(
        self,
        invoice: DocumentInfo,
        orders: List[DocumentInfo]
    ) -> Optional[DocumentInfo]:
        """查找匹配的采购订单"""
        candidates = []

        for order in orders:
            score = self._calculate_order_match_score(invoice, order)

            if score >= 0.6:  # 匹配阈值
                candidates.append((order, score))

        if candidates:
            # 返回得分最高的
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def _find_matching_receipt(
        self,
        invoice: DocumentInfo,
        receipts: List[DocumentInfo],
        matched_order: Optional[DocumentInfo]
    ) -> Optional[DocumentInfo]:
        """查找匹配的入库单"""
        candidates = []

        for receipt in receipts:
            score = self._calculate_receipt_match_score(invoice, receipt, matched_order)

            if score >= 0.6:
                candidates.append((receipt, score))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def _calculate_order_match_score(
        self,
        invoice: DocumentInfo,
        order: DocumentInfo
    ) -> float:
        """计算发票与订单的匹配分数"""
        score = 0.0

        # 供应商匹配（权重40%）
        if invoice.supplier and order.supplier:
            if invoice.supplier == order.supplier:
                score += 0.4
            elif invoice.supplier in order.supplier or order.supplier in invoice.supplier:
                score += 0.3

        # 金额匹配（权重30%）
        if invoice.amount and order.amount:
            if invoice.amount == order.amount:
                score += 0.3
            else:
                diff_ratio = abs(invoice.amount - order.amount) / max(invoice.amount, order.amount)
                if diff_ratio <= self.amount_tolerance:
                    score += 0.25
                elif diff_ratio <= 0.05:
                    score += 0.15

        # 日期匹配（权重20%）
        if invoice.date and order.date:
            days_diff = abs((invoice.date - order.date).days)
            if days_diff <= 7:
                score += 0.2
            elif days_diff <= self.date_tolerance:
                score += 0.1

        # 商品匹配（权重10%）
        if invoice.product_name and order.product_name:
            if invoice.product_name == order.product_name:
                score += 0.1
            elif invoice.product_name in order.product_name or order.product_name in invoice.product_name:
                score += 0.05

        return score

    def _calculate_receipt_match_score(
        self,
        invoice: DocumentInfo,
        receipt: DocumentInfo,
        matched_order: Optional[DocumentInfo]
    ) -> float:
        """计算发票与入库单的匹配分数"""
        score = 0.0

        # 供应商匹配
        if invoice.supplier and receipt.supplier:
            if invoice.supplier == receipt.supplier:
                score += 0.35
            elif invoice.supplier in receipt.supplier or receipt.supplier in invoice.supplier:
                score += 0.25

        # 金额匹配
        if invoice.amount and receipt.amount:
            if invoice.amount == receipt.amount:
                score += 0.35
            else:
                diff_ratio = abs(invoice.amount - receipt.amount) / max(invoice.amount, receipt.amount)
                if diff_ratio <= self.amount_tolerance:
                    score += 0.3
                elif diff_ratio <= 0.05:
                    score += 0.2

        # 日期匹配
        if invoice.date and receipt.date:
            days_diff = abs((invoice.date - receipt.date).days)
            if days_diff <= 7:
                score += 0.2
            elif days_diff <= self.date_tolerance:
                score += 0.1

        # 如果有匹配的订单，检查入库单是否与订单关联
        if matched_order and receipt.document_no == matched_order.document_no:
            score += 0.1

        return score

    def _calculate_differences(
        self,
        invoice: DocumentInfo,
        order: Optional[DocumentInfo],
        receipt: Optional[DocumentInfo]
    ) -> List[MatchDifference]:
        """计算差异"""
        differences = []

        # 金额差异
        if invoice.amount:
            order_amount = order.amount if order else None
            receipt_amount = receipt.amount if receipt else None

            if order and order_amount and abs(invoice.amount - order_amount) > invoice.amount * 0.01:
                differences.append(MatchDifference(
                    field="金额",
                    invoice_value=invoice.amount,
                    order_value=order_amount,
                    receipt_value=receipt_amount,
                    difference_description=f"发票金额{invoice.amount:,.2f}与订单金额{order_amount:,.2f}不一致"
                ))
            elif receipt and receipt_amount and abs(invoice.amount - receipt_amount) > invoice.amount * 0.01:
                differences.append(MatchDifference(
                    field="金额",
                    invoice_value=invoice.amount,
                    order_value=order_amount,
                    receipt_value=receipt_amount,
                    difference_description=f"发票金额{invoice.amount:,.2f}与入库单金额{receipt_amount:,.2f}不一致"
                ))

        # 日期差异
        if invoice.date:
            order_date = order.date if order else None
            receipt_date = receipt.date if receipt else None

            if order and order_date:
                days_diff = abs((invoice.date - order_date).days)
                if days_diff > self.date_tolerance:
                    differences.append(MatchDifference(
                        field="日期",
                        invoice_value=str(invoice.date),
                        order_value=str(order_date),
                        receipt_value=str(receipt_date) if receipt_date else None,
                        difference_description=f"发票日期与订单日期相差{days_diff}天"
                    ))

        # 供应商差异
        if invoice.supplier:
            order_supplier = order.supplier if order else None
            receipt_supplier = receipt.supplier if receipt else None

            if order and order_supplier and invoice.supplier != order_supplier:
                differences.append(MatchDifference(
                    field="供应商",
                    invoice_value=invoice.supplier,
                    order_value=order_supplier,
                    receipt_value=receipt_supplier,
                    difference_description=f"发票供应商{invoice.supplier}与订单供应商{order_supplier}不一致"
                ))

        return differences

    def _determine_match_status(
        self,
        invoice: DocumentInfo,
        order: Optional[DocumentInfo],
        receipt: Optional[DocumentInfo],
        differences: List[MatchDifference]
    ) -> Tuple[MatchStatus, float]:
        """确定匹配状态"""
        if order and receipt:
            if not differences:
                return MatchStatus.FULLY_MATCHED, 1.0
            else:
                # 根据差异数量和严重程度计算分数
                score = max(0.5, 1.0 - len(differences) * 0.1)
                return MatchStatus.PARTIALLY_MATCHED, score

        elif order or receipt:
            return MatchStatus.PARTIALLY_MATCHED, 0.5

        else:
            return MatchStatus.NOT_MATCHED, 0.0

    def _calculate_amount_difference(
        self,
        invoice: DocumentInfo,
        order: Optional[DocumentInfo],
        receipt: Optional[DocumentInfo]
    ) -> float:
        """计算金额差异"""
        if receipt and receipt.amount and invoice.amount:
            return invoice.amount - receipt.amount
        elif order and order.amount and invoice.amount:
            return invoice.amount - order.amount
        return 0.0

    def _calculate_date_difference(
        self,
        invoice: DocumentInfo,
        order: Optional[DocumentInfo],
        receipt: Optional[DocumentInfo]
    ) -> int:
        """计算日期差异（天数）"""
        if receipt and receipt.date and invoice.date:
            return (invoice.date - receipt.date).days
        elif order and order.date and invoice.date:
            return (invoice.date - order.date).days
        return 0

    def _generate_suggestions(
        self,
        match_status: MatchStatus,
        differences: List[MatchDifference]
    ) -> List[str]:
        """生成处理建议"""
        suggestions = []

        if match_status == MatchStatus.NOT_MATCHED:
            suggestions.append("未找到匹配的订单和入库单，请核实采购流程是否完整")
            suggestions.append("建议检查是否存在漏记或错记的单据")

        elif match_status == MatchStatus.PARTIALLY_MATCHED:
            for diff in differences:
                if diff.field == "金额":
                    suggestions.append(f"金额差异：{diff.difference_description}")
                    suggestions.append("建议核实价格变动是否经过审批")
                elif diff.field == "日期":
                    suggestions.append(f"日期差异：{diff.difference_description}")
                    suggestions.append("建议核实是否存在跨期交易")
                elif diff.field == "供应商":
                    suggestions.append(f"供应商差异：{diff.difference_description}")
                    suggestions.append("建议核实是否为同一供应商的不同名称")

        elif match_status == MatchStatus.FULLY_MATCHED:
            suggestions.append("三单匹配一致，可正常入账")

        return suggestions

    def _load_documents_from_db(
        self,
        project_id: str,
        invoice_ids: List[str] = None
    ) -> Tuple[List[DocumentInfo], List[DocumentInfo], List[DocumentInfo]]:
        """从数据库加载单据"""
        invoices = []
        orders = []
        receipts = []

        with get_db_cursor() as cursor:
            # 查询发票（假设凭证中带有发票标识）
            if invoice_ids:
                placeholders = ",".join(["?" for _ in invoice_ids])
                cursor.execute(
                    f"""
                    SELECT id, voucher_no, voucher_date, amount, counterparty, description
                    FROM vouchers
                    WHERE project_id = ? AND id IN ({placeholders})
                    """,
                    [project_id] + invoice_ids
                )
            else:
                # 默认查询金额较大的凭证作为发票
                cursor.execute(
                    """
                    SELECT id, voucher_no, voucher_date, amount, counterparty, description
                    FROM vouchers
                    WHERE project_id = ?
                    ORDER BY amount DESC
                    LIMIT 50
                    """,
                    [project_id]
                )

            for row in cursor.fetchall():
                invoices.append(DocumentInfo(
                    id=row[0],
                    document_no=row[1],
                    document_type=DocumentType.INVOICE,
                    date=row[2],
                    amount=float(row[3]) if row[3] else 0,
                    supplier=row[4] or "",
                    product_name="",
                    raw_data={"description": row[5]}
                ))

            # 查询入库单（假设通过counterparty字段区分）
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount, counterparty, description
                FROM vouchers
                WHERE project_id = ?
                  AND (description LIKE '%入库%' OR description LIKE '%收货%')
                """,
                [project_id]
            )

            for row in cursor.fetchall():
                receipts.append(DocumentInfo(
                    id=row[0],
                    document_no=row[1],
                    document_type=DocumentType.RECEIPT,
                    date=row[2],
                    amount=float(row[3]) if row[3] else 0,
                    supplier=row[4] or "",
                    product_name="",
                    raw_data={"description": row[5]}
                ))

        return invoices, orders, receipts

    def _save_match_result(self, result: MatchResult):
        """保存匹配结果"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO matching_results
                (id, project_id, invoice_id, order_id, receipt_id,
                 match_status, amount_difference, date_difference,
                 differences, suggestions, matched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    result.id,
                    result.project_id,
                    result.invoice_id,
                    result.order_id,
                    result.receipt_id,
                    result.match_status.value,
                    result.amount_difference,
                    result.date_difference,
                    json.dumps([{
                        "field": d.field,
                        "invoice_value": d.invoice_value,
                        "order_value": d.order_value,
                        "receipt_value": d.receipt_value,
                        "description": d.difference_description
                    } for d in result.differences], ensure_ascii=False),
                    json.dumps(result.suggestions, ensure_ascii=False),
                    result.matched_at
                ]
            )
            get_db().commit()

    def get_match_results(
        self,
        project_id: str,
        status: MatchStatus = None
    ) -> List[MatchResult]:
        """获取匹配结果"""
        with get_db_cursor() as cursor:
            # Use JOIN to avoid N+1 query for voucher_no
            if status:
                cursor.execute(
                    """
                    SELECT m.id, m.project_id, m.invoice_id, m.order_id, m.receipt_id,
                           m.match_status, m.amount_difference, m.date_difference,
                           m.differences, m.suggestions, m.matched_at, v.voucher_no
                    FROM matching_results m
                    LEFT JOIN vouchers v ON m.invoice_id = v.id
                    WHERE m.project_id = ? AND m.match_status = ?
                    """,
                    [project_id, status.value]
                )
            else:
                cursor.execute(
                    """
                    SELECT m.id, m.project_id, m.invoice_id, m.order_id, m.receipt_id,
                           m.match_status, m.amount_difference, m.date_difference,
                           m.differences, m.suggestions, m.matched_at, v.voucher_no
                    FROM matching_results m
                    LEFT JOIN vouchers v ON m.invoice_id = v.id
                    WHERE m.project_id = ?
                    """,
                    [project_id]
                )

            results = []
            for row in cursor.fetchall():
                results.append(MatchResult(
                    id=row[0],
                    project_id=row[1],
                    invoice_id=row[2],
                    invoice_no=row[11] or "",  # voucher_no from JOIN
                    order_id=row[3],
                    order_no="",
                    receipt_id=row[4],
                    receipt_no="",
                    match_status=MatchStatus(row[5]),
                    match_score=0.0,
                    amount_difference=float(row[6]) if row[6] else 0,
                    quantity_difference=0,
                    date_difference=row[7] or 0,
                    differences=[],
                    suggestions=json.loads(row[9]) if isinstance(row[9], str) else row[9],
                    matched_at=row[10]
                ))

            return results


# 全局服务实例
three_way_matcher = ThreeWayMatcher()