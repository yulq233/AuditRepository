"""
凭证智能分类服务
支持按凭证类型、会计科目、业务类型、风险标签分类
"""
import os
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db


class VoucherType(str, Enum):
    """凭证类型"""
    INVOICE = "invoice"              # 发票
    CONTRACT = "contract"            # 合同
    BANK_RECEIPT = "bank_receipt"    # 银行回单
    RECEIPT = "receipt"              # 收据
    APPROVAL = "approval"            # 审批单
    EXPENSE = "expense"              # 费用报销单
    PAYMENT = "payment"              # 付款凭证
    RECEIVABLE = "receivable"        # 收款凭证
    JOURNAL = "journal"              # 记账凭证
    OTHER = "other"                  # 其他


class BusinessType(str, Enum):
    """业务类型"""
    PURCHASE = "purchase"            # 采购
    SALES = "sales"                  # 销售
    EXPENSE = "expense"              # 费用
    ASSET = "asset"                  # 资产
    LIABILITY = "liability"          # 负债
    EQUITY = "equity"                # 所有者权益
    PAYROLL = "payroll"              # 薪酬
    TAX = "tax"                      # 税务
    OTHER = "other"                  # 其他


class RiskTag(str, Enum):
    """风险标签"""
    HIGH_RISK = "high_risk"          # 高风险
    ANOMALY = "anomaly"              # 异常
    ATTENTION = "attention"          # 需关注
    NORMAL = "normal"                # 正常
    VERIFIED = "verified"            # 已核实


@dataclass
class VoucherCategory:
    """凭证分类结果"""
    voucher_id: str
    voucher_type: VoucherType
    subject_category: str           # 科目分类
    business_category: BusinessType
    risk_tag: RiskTag
    confidence: float               # 分类置信度
    tags: List[str]                 # 附加标签


# 凭证类型关键词映射
VOUCHER_TYPE_KEYWORDS = {
    VoucherType.INVOICE: [
        "发票", "增值税", "专用发票", "普通发票", "电子发票",
        "invoice", "税务", "税率"
    ],
    VoucherType.CONTRACT: [
        "合同", "协议", "订单", "采购合同", "销售合同",
        "合同编号", "合同金额", "contract"
    ],
    VoucherType.BANK_RECEIPT: [
        "银行", "回单", "转账", "汇款", "收款回单", "付款回单",
        "银行流水", "bank", "账号"
    ],
    VoucherType.RECEIPT: [
        "收据", "收款收据", "付款收据", "收条", "receipt"
    ],
    VoucherType.APPROVAL: [
        "审批", "申请", "报销单", "审批单", "费用申请",
        "签字", "批准", "approval"
    ],
    VoucherType.EXPENSE: [
        "报销", "费用报销", "差旅费", "招待费", "交通费",
        "住宿费", "餐费", "expense"
    ],
    VoucherType.PAYMENT: [
        "付款", "支付", "付款凭证", "支出", "付款申请"
    ],
    VoucherType.RECEIVABLE: [
        "收款", "收入", "收款凭证", "进账", "应收"
    ],
    VoucherType.JOURNAL: [
        "记账", "记账凭证", "凭证", "会计凭证", "转账凭证"
    ],
}

# 科目分类映射
SUBJECT_CATEGORY_MAP = {
    # 资产类
    "1001": "现金", "1002": "银行存款", "1012": "其他货币资金",
    "1101": "交易性金融资产", "1121": "应收票据", "1122": "应收账款",
    "1123": "预付账款", "1131": "应收股利", "1132": "应收利息",
    "1221": "其他应收款", "1231": "坏账准备", "1401": "材料采购",
    "1402": "在途物资", "1403": "原材料", "1404": "材料成本差异",
    "1405": "库存商品", "1406": "发出商品", "1407": "商品进销差价",
    "1408": "委托加工物资", "1411": "周转材料", "1471": "存货跌价准备",
    "1511": "长期股权投资", "1601": "固定资产", "1602": "累计折旧",
    "1603": "固定资产减值准备", "1604": "在建工程", "1605": "工程物资",
    "1606": "固定资产清理", "1701": "无形资产", "1702": "累计摊销",
    "1801": "长期待摊费用", "1811": "递延所得税资产", "1901": "待处理财产损溢",

    # 负债类
    "2001": "短期借款", "2002": "交易性金融负债", "2201": "应付票据",
    "2202": "应付账款", "2203": "预收账款", "2211": "应付职工薪酬",
    "2221": "应交税费", "2231": "应付利息", "2232": "应付股利",
    "2241": "其他应付款", "2401": "递延收益", "2501": "长期借款",
    "2502": "应付债券", "2701": "长期应付款", "2711": "专项应付款",
    "2801": "预计负债", "2901": "递延所得税负债",

    # 所有者权益类
    "4001": "实收资本", "4002": "资本公积", "4101": "盈余公积",
    "4103": "本年利润", "4104": "利润分配", "4201": "库存股",

    # 成本类
    "5001": "生产成本", "5101": "制造费用", "5201": "劳务成本",
    "5301": "研发支出",

    # 损益类
    "6001": "主营业务收入", "6051": "其他业务收入", "6101": "公允价值变动损益",
    "6111": "投资收益", "6301": "营业外收入", "6401": "主营业务成本",
    "6402": "其他业务成本", "6403": "税金及附加", "6601": "销售费用",
    "6602": "管理费用", "6603": "财务费用", "6701": "资产减值损失",
    "6711": "营业外支出", "6801": "所得税费用", "6901": "以前年度损益调整",
}

# 业务类型映射（基于科目代码）
BUSINESS_TYPE_BY_SUBJECT = {
    "purchase": ["1401", "1402", "1403", "1405", "2202"],  # 采购相关
    "sales": ["6001", "1122", "1121"],                      # 销售相关
    "expense": ["6601", "6602", "6603"],                   # 费用相关
    "asset": ["1601", "1604", "1701"],                     # 资产相关
    "liability": ["2001", "2201", "2202", "2221"],         # 负债相关
    "equity": ["4001", "4002", "4101"],                    # 权益相关
    "payroll": ["2211"],                                    # 薪酬相关
    "tax": ["2221", "6403", "6801"],                       # 税务相关
}

# 风险关键词
RISK_KEYWORDS = {
    RiskTag.HIGH_RISK: [
        "大额", "异常", "调整", "冲销", "红字",
        "关联方", "关联交易", "重大"
    ],
    RiskTag.ANOMALY: [
        "周末", "节假日", "跨期", "冲回",
        "调整分录", "以前年度"
    ],
    RiskTag.ATTENTION: [
        "暂估", "待处理", "待核销",
        "预提", "待摊", "分期"
    ],
}


class VoucherClassifier:
    """凭证分类器"""

    def __init__(self):
        self.voucher_type_keywords = VOUCHER_TYPE_KEYWORDS
        self.subject_map = SUBJECT_CATEGORY_MAP
        self.business_map = BUSINESS_TYPE_BY_SUBJECT
        self.risk_keywords = RISK_KEYWORDS

    def classify(
        self,
        voucher_id: str,
        description: str = "",
        subject_code: str = "",
        subject_name: str = "",
        amount: float = 0,
        ocr_text: str = ""
    ) -> VoucherCategory:
        """
        分类凭证

        Args:
            voucher_id: 凭证ID
            description: 凭证摘要
            subject_code: 科目代码
            subject_name: 科目名称
            amount: 金额
            ocr_text: OCR识别文本

        Returns:
            VoucherCategory: 分类结果
        """
        # 合并所有文本用于关键词匹配
        all_text = f"{description} {subject_name} {ocr_text}".lower()

        # 1. 识别凭证类型
        voucher_type = self._classify_voucher_type(all_text)

        # 2. 识别科目分类
        subject_category = self._get_subject_category(subject_code, subject_name)

        # 3. 识别业务类型
        business_type = self._classify_business_type(subject_code, all_text)

        # 4. 识别风险标签
        risk_tag = self._assess_risk(all_text, amount)

        # 5. 提取附加标签
        tags = self._extract_tags(all_text)

        # 计算综合置信度
        confidence = self._calculate_confidence(
            voucher_type, subject_category, business_type, risk_tag,
            description, subject_code
        )

        return VoucherCategory(
            voucher_id=voucher_id,
            voucher_type=voucher_type,
            subject_category=subject_category,
            business_category=business_type,
            risk_tag=risk_tag,
            confidence=confidence,
            tags=tags
        )

    def _classify_voucher_type(self, text: str) -> VoucherType:
        """识别凭证类型"""
        scores = {}

        for vtype, keywords in self.voucher_type_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scores[vtype] = score

        if scores:
            return max(scores, key=scores.get)

        return VoucherType.OTHER

    def _get_subject_category(self, subject_code: str, subject_name: str) -> str:
        """获取科目分类"""
        # 尝试直接匹配科目代码
        if subject_code:
            # 尝试完整匹配
            if subject_code in self.subject_map:
                return self.subject_map[subject_code]

            # 尝试前缀匹配（取前4位）
            prefix = subject_code[:4]
            if prefix in self.subject_map:
                return self.subject_map[prefix]

            # 尝试前2位匹配（大类）
            category_prefix = subject_code[:2]
            if category_prefix == "1":
                return "资产类"
            elif category_prefix == "2":
                return "负债类"
            elif category_prefix == "3":
                return "共同类"
            elif category_prefix == "4":
                return "所有者权益类"
            elif category_prefix == "5":
                return "成本类"
            elif category_prefix == "6":
                return "损益类"

        # 返回科目名称或默认值
        return subject_name or "未分类"

    def _classify_business_type(self, subject_code: str, text: str) -> BusinessType:
        """识别业务类型"""
        if subject_code:
            prefix = subject_code[:4]

            for btype, codes in self.business_map.items():
                if prefix in codes:
                    return BusinessType(btype)

        # 基于文本关键词判断
        if any(kw in text for kw in ["采购", "进货", "购买"]):
            return BusinessType.PURCHASE
        elif any(kw in text for kw in ["销售", "销售出库", "出售"]):
            return BusinessType.SALES
        elif any(kw in text for kw in ["费用", "报销", "差旅", "招待"]):
            return BusinessType.EXPENSE
        elif any(kw in text for kw in ["固定资产", "设备", "购入资产"]):
            return BusinessType.ASSET
        elif any(kw in text for kw in ["借款", "贷款", "融资"]):
            return BusinessType.LIABILITY

        return BusinessType.OTHER

    def _assess_risk(self, text: str, amount: float) -> RiskTag:
        """评估风险标签"""
        # 检查高风险关键词
        for keyword in self.risk_keywords.get(RiskTag.HIGH_RISK, []):
            if keyword in text:
                return RiskTag.HIGH_RISK

        # 检查异常关键词
        for keyword in self.risk_keywords.get(RiskTag.ANOMALY, []):
            if keyword in text:
                return RiskTag.ANOMALY

        # 检查需关注关键词
        for keyword in self.risk_keywords.get(RiskTag.ATTENTION, []):
            if keyword in text:
                return RiskTag.ATTENTION

        # 大额凭证标记为需关注
        if amount and amount > 100000:
            return RiskTag.ATTENTION

        return RiskTag.NORMAL

    def _extract_tags(self, text: str) -> List[str]:
        """提取附加标签"""
        tags = []

        # 金额标签
        if "大额" in text:
            tags.append("大额")

        # 时间标签
        if "跨期" in text or "跨年" in text:
            tags.append("跨期")

        # 业务标签
        if "关联" in text:
            tags.append("关联交易")
        if "政府" in text or "财政" in text:
            tags.append("政府补助")
        if "研发" in text:
            tags.append("研发费用")
        if "捐赠" in text:
            tags.append("捐赠")

        return tags

    def _calculate_confidence(
        self,
        voucher_type: VoucherType,
        subject_category: str,
        business_type: BusinessType,
        risk_tag: RiskTag,
        description: str,
        subject_code: str
    ) -> float:
        """计算分类置信度"""
        confidence = 0.5  # 基础置信度

        # 有摘要增加置信度
        if description:
            confidence += 0.1

        # 有科目代码增加置信度
        if subject_code:
            confidence += 0.2

        # 非默认分类增加置信度
        if voucher_type != VoucherType.OTHER:
            confidence += 0.1

        if business_type != BusinessType.OTHER:
            confidence += 0.1

        return min(confidence, 1.0)


class VoucherIndexer:
    """凭证索引器"""

    def __init__(self):
        self.classifier = VoucherClassifier()

    def index_voucher(
        self,
        voucher_id: str,
        description: str = "",
        subject_code: str = "",
        subject_name: str = "",
        amount: float = 0,
        ocr_text: str = "",
        save: bool = True
    ) -> VoucherCategory:
        """
        为凭证建立分类索引

        Args:
            voucher_id: 凭证ID
            description: 凭证摘要
            subject_code: 科目代码
            subject_name: 科目名称
            amount: 金额
            ocr_text: OCR识别文本
            save: 是否保存到数据库

        Returns:
            VoucherCategory: 分类结果
        """
        # 执行分类
        category = self.classifier.classify(
            voucher_id=voucher_id,
            description=description,
            subject_code=subject_code,
            subject_name=subject_name,
            amount=amount,
            ocr_text=ocr_text
        )

        # 保存到数据库
        if save:
            self._save_category(category)

        return category

    def _save_category(self, category: VoucherCategory):
        """保存分类结果到数据库"""
        with get_db_cursor() as cursor:
            # 检查是否已有分类
            cursor.execute(
                "SELECT id FROM voucher_categories WHERE voucher_id = ?",
                [category.voucher_id]
            )
            existing = cursor.fetchone()

            if existing:
                # 更新
                cursor.execute(
                    """
                    UPDATE voucher_categories SET
                        category_type = ?,
                        subject_category = ?,
                        business_category = ?,
                        risk_tag = ?
                    WHERE voucher_id = ?
                    """,
                    [
                        category.voucher_type.value,
                        category.subject_category,
                        category.business_category.value,
                        category.risk_tag.value,
                        category.voucher_id
                    ]
                )
            else:
                # 插入
                cursor.execute(
                    """
                    INSERT INTO voucher_categories
                    (id, voucher_id, category_type, subject_category,
                     business_category, risk_tag)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        str(uuid.uuid4()),
                        category.voucher_id,
                        category.voucher_type.value,
                        category.subject_category,
                        category.business_category.value,
                        category.risk_tag.value
                    ]
                )

            get_db().commit()

    def batch_index(self, vouchers: List[Dict[str, Any]]) -> List[VoucherCategory]:
        """批量建立索引"""
        results = []

        for v in vouchers:
            category = self.index_voucher(
                voucher_id=v.get("id"),
                description=v.get("description", ""),
                subject_code=v.get("subject_code", ""),
                subject_name=v.get("subject_name", ""),
                amount=v.get("amount", 0),
                ocr_text=v.get("ocr_text", "")
            )
            results.append(category)

        return results

    def get_statistics(self, project_id: str) -> Dict[str, Any]:
        """获取分类统计"""
        with get_db_cursor() as cursor:
            stats = {}

            # 凭证类型统计
            cursor.execute(
                """
                SELECT vc.category_type, COUNT(*) as cnt
                FROM voucher_categories vc
                JOIN vouchers v ON vc.voucher_id = v.id
                WHERE v.project_id = ?
                GROUP BY vc.category_type
                """,
                [project_id]
            )
            stats["voucher_types"] = {row[0]: row[1] for row in cursor.fetchall()}

            # 风险标签统计
            cursor.execute(
                """
                SELECT vc.risk_tag, COUNT(*) as cnt
                FROM voucher_categories vc
                JOIN vouchers v ON vc.voucher_id = v.id
                WHERE v.project_id = ?
                GROUP BY vc.risk_tag
                """,
                [project_id]
            )
            stats["risk_tags"] = {row[0]: row[1] for row in cursor.fetchall()}

            # 业务类型统计
            cursor.execute(
                """
                SELECT vc.business_category, COUNT(*) as cnt
                FROM voucher_categories vc
                JOIN vouchers v ON vc.voucher_id = v.id
                WHERE v.project_id = ?
                GROUP BY vc.business_category
                """,
                [project_id]
            )
            stats["business_types"] = {row[0]: row[1] for row in cursor.fetchall()}

            return stats


# 全局实例
voucher_classifier = VoucherClassifier()
voucher_indexer = VoucherIndexer()