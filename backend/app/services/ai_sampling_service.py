"""
AI智能抽凭服务
基于大语言模型实现凭证语义理解、风险评估、智能抽样推荐
"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from app.core.database import get_db_cursor, get_db
from app.services.llm_service import (
    LLMService, LLMConfig, ChatMessage, llm_service
)
from app.utils.common import extract_json_from_llm_response, generate_id
from app.schemas.enums import RiskLevel


@dataclass
class RiskAssessment:
    """风险评估结果"""
    voucher_id: str
    risk_level: str          # high, medium, low
    risk_score: float        # 0-100
    risk_factors: List[str]
    explanation: str
    confidence: float


@dataclass
class SamplingRecommendation:
    """抽样推荐结果"""
    voucher_id: str
    priority: int            # 优先级 1-5
    reason: str
    risk_indicators: List[str]
    recommended_action: str


@dataclass
class IntelligentSamplingResult:
    """智能抽样结果"""
    project_id: str
    total_analyzed: int
    recommendations: List[SamplingRecommendation]
    risk_summary: Dict[str, int]
    strategy_suggestion: str


class VoucherRiskAnalyzer:
    """凭证风险分析器"""

    def __init__(self, llm_svc: LLMService = None):
        self.llm = llm_svc if llm_svc else llm_service

    async def analyze_voucher(
        self,
        voucher: Dict[str, Any]
    ) -> RiskAssessment:
        """
        分析单个凭证的风险

        Args:
            voucher: 凭证数据

        Returns:
            RiskAssessment: 风险评估结果
        """
        # 构建分析提示
        prompt = self._build_analysis_prompt(voucher)

        messages = [
            ChatMessage(role="system", content=self._get_system_prompt()),
            ChatMessage(role="user", content=prompt)
        ]

        try:
            response = await self.llm.chat(messages, temperature=0.3)

            # 解析响应
            result = self._parse_risk_response(response.content, voucher.get("id"))

            return result

        except Exception as e:
            # 返回默认风险评估
            return RiskAssessment(
                voucher_id=voucher.get("id", ""),
                risk_level="medium",
                risk_score=50.0,
                risk_factors=[f"分析失败: {str(e)}"],
                explanation="无法完成风险评估",
                confidence=0.0
            )

    async def batch_analyze(
        self,
        vouchers: List[Dict[str, Any]],
        batch_size: int = 10
    ) -> List[RiskAssessment]:
        """
        批量分析凭证风险

        Args:
            vouchers: 凭证列表
            batch_size: 批次大小

        Returns:
            List[RiskAssessment]: 风险评估结果列表
        """
        results = []

        for i in range(0, len(vouchers), batch_size):
            batch = vouchers[i:i + batch_size]
            tasks = [self.analyze_voucher(v) for v in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一位资深审计专家，专注于财务凭证风险分析。

你的任务是分析凭证数据，识别潜在风险，并给出风险评估。

分析维度：
1. 金额异常：金额过大/过小、非正常整数、与业务不符
2. 时间异常：非工作日、月末/年末集中、跨期调整
3. 摘要异常：摘要模糊、与科目不匹配、存在敏感词
4. 科目异常：科目使用不当、借贷方向错误
5. 交易对手异常：关联方、新增客户/供应商、地址异常

请严格按照以下JSON格式输出：
{
    "risk_level": "high/medium/low",
    "risk_score": 0-100的数字,
    "risk_factors": ["风险因素1", "风险因素2"],
    "explanation": "风险说明",
    "confidence": 0-1的置信度
}"""

    def _build_analysis_prompt(self, voucher: Dict[str, Any]) -> str:
        """构建分析提示"""
        voucher_info = f"""
凭证编号: {voucher.get('voucher_no', '未知')}
凭证日期: {voucher.get('voucher_date', '未知')}
金额: {voucher.get('amount', 0)}
科目代码: {voucher.get('subject_code', '未知')}
科目名称: {voucher.get('subject_name', '未知')}
摘要: {voucher.get('description', '无')}
交易对手: {voucher.get('counterparty', '未知')}
"""
        return f"请分析以下凭证的风险：\n{voucher_info}\n\n请输出风险评估结果（仅输出JSON，不要其他内容）："

    def _parse_risk_response(self, response: str, voucher_id: str) -> RiskAssessment:
        """解析风险响应"""
        try:
            data = extract_json_from_llm_response(response)

            return RiskAssessment(
                voucher_id=voucher_id,
                risk_level=data.get("risk_level", "medium"),
                risk_score=float(data.get("risk_score", 50)),
                risk_factors=data.get("risk_factors", []),
                explanation=data.get("explanation", ""),
                confidence=float(data.get("confidence", 0.5))
            )

        except (ValueError, KeyError):
            # 解析失败，返回默认值
            return RiskAssessment(
                voucher_id=voucher_id,
                risk_level="medium",
                risk_score=50.0,
                risk_factors=["响应解析失败"],
                explanation=response[:200] if len(response) > 200 else response,
                confidence=0.0
            )


class IntelligentSampler:
    """智能抽样器"""

    def __init__(self, llm_svc: LLMService = None):
        self.llm = llm_svc if llm_svc else llm_service
        self.risk_analyzer = VoucherRiskAnalyzer(self.llm)

    async def recommend_samples(
        self,
        project_id: str,
        sample_size: int = 50,
        focus_areas: List[str] = None
    ) -> IntelligentSamplingResult:
        """
        智能推荐抽样凭证

        Args:
            project_id: 项目ID
            sample_size: 期望样本量
            focus_areas: 重点关注领域

        Returns:
            IntelligentSamplingResult: 智能抽样结果
        """
        # 获取项目凭证
        vouchers = self._get_project_vouchers(project_id)

        if not vouchers:
            return IntelligentSamplingResult(
                project_id=project_id,
                total_analyzed=0,
                recommendations=[],
                risk_summary={},
                strategy_suggestion="项目中没有凭证数据"
            )

        # 风险分析
        risk_assessments = await self.risk_analyzer.batch_analyze(vouchers)

        # 生成推荐
        recommendations = self._generate_recommendations(
            vouchers, risk_assessments, sample_size, focus_areas
        )

        # 统计风险分布
        risk_summary = self._summarize_risks(risk_assessments)

        # 生成策略建议
        strategy = await self._generate_strategy(
            risk_summary, sample_size, focus_areas
        )

        # 保存结果
        self._save_sampling_results(project_id, recommendations, risk_assessments)

        return IntelligentSamplingResult(
            project_id=project_id,
            total_analyzed=len(vouchers),
            recommendations=recommendations[:sample_size],
            risk_summary=risk_summary,
            strategy_suggestion=strategy
        )

    def _get_project_vouchers(self, project_id: str) -> List[Dict[str, Any]]:
        """获取项目凭证"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
                FROM vouchers
                WHERE project_id = ?
                ORDER BY amount DESC
                LIMIT 500
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else None,
                    "amount": float(row[3]) if row[3] else 0,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7]
                }
                for row in rows
            ]

    def _generate_recommendations(
        self,
        vouchers: List[Dict[str, Any]],
        risk_assessments: List[RiskAssessment],
        sample_size: int,
        focus_areas: List[str] = None
    ) -> List[SamplingRecommendation]:
        """生成抽样推荐"""
        # 合并凭证和风险评估
        voucher_risks = []
        for v, r in zip(vouchers, risk_assessments):
            voucher_risks.append({
                "voucher": v,
                "risk": r
            })

        # 按风险分数排序
        voucher_risks.sort(key=lambda x: x["risk"].risk_score, reverse=True)

        recommendations = []
        for idx, item in enumerate(voucher_risks[:sample_size * 2]):  # 取2倍候选
            v = item["voucher"]
            r = item["risk"]

            # 计算优先级
            priority = self._calculate_priority(r, focus_areas)

            reason = self._generate_reason(r, v)

            recommendations.append(SamplingRecommendation(
                voucher_id=v["id"],
                priority=priority,
                reason=reason,
                risk_indicators=r.risk_factors,
                recommended_action=self._get_recommended_action(r)
            ))

        # 按优先级排序
        recommendations.sort(key=lambda x: x.priority, reverse=True)

        return recommendations

    def _calculate_priority(
        self,
        risk: RiskAssessment,
        focus_areas: List[str] = None
    ) -> int:
        """计算优先级"""
        priority = 1

        # 风险等级
        if risk.risk_level == "high":
            priority += 3
        elif risk.risk_level == "medium":
            priority += 1

        # 风险分数
        if risk.risk_score >= 70:
            priority += 2
        elif risk.risk_score >= 50:
            priority += 1

        # 置信度
        if risk.confidence >= 0.8:
            priority += 1

        # 关注领域匹配
        if focus_areas:
            for factor in risk.risk_factors:
                if any(area in factor for area in focus_areas):
                    priority += 1

        return min(priority, 5)

    def _generate_reason(self, risk: RiskAssessment, voucher: Dict[str, Any]) -> str:
        """生成推荐理由"""
        reasons = []

        if risk.risk_level == "high":
            reasons.append("高风险凭证")
        elif risk.risk_level == "medium":
            reasons.append("中风险凭证")

        if voucher.get("amount", 0) > 100000:
            reasons.append("大额交易")

        if risk.risk_factors:
            reasons.extend(risk.risk_factors[:2])

        return "；".join(reasons) if reasons else "建议抽查"

    def _get_recommended_action(self, risk: RiskAssessment) -> str:
        """获取推荐操作"""
        if risk.risk_level == "high":
            return "建议重点审查，核实原始凭证"
        elif risk.risk_level == "medium":
            return "建议关注，检查相关附件"
        else:
            return "常规抽查即可"

    def _summarize_risks(self, assessments: List[RiskAssessment]) -> Dict[str, int]:
        """汇总风险分布"""
        summary = {"high": 0, "medium": 0, "low": 0}

        for a in assessments:
            summary[a.risk_level] = summary.get(a.risk_level, 0) + 1

        return summary

    async def _generate_strategy(
        self,
        risk_summary: Dict[str, int],
        sample_size: int,
        focus_areas: List[str] = None
    ) -> str:
        """生成策略建议"""
        total = sum(risk_summary.values())

        if total == 0:
            return "无数据可供分析"

        high_pct = risk_summary.get("high", 0) / total * 100
        medium_pct = risk_summary.get("medium", 0) / total * 100

        strategy = f"共分析{total}张凭证，"
        strategy += f"高风险{risk_summary.get('high', 0)}张({high_pct:.1f}%)，"
        strategy += f"中风险{risk_summary.get('medium', 0)}张({medium_pct:.1f}%)。\n\n"

        if high_pct > 20:
            strategy += "建议：高风险凭证占比较高，建议扩大抽样比例，重点关注异常凭证。"
        elif medium_pct > 30:
            strategy += "建议：中风险凭证较多，建议按科目分层抽样，确保覆盖重点领域。"
        else:
            strategy += "建议：风险分布较正常，可按常规比例抽样。"

        if focus_areas:
            strategy += f"\n关注领域：{', '.join(focus_areas)}"

        return strategy

    def _save_sampling_results(
        self,
        project_id: str,
        recommendations: List[SamplingRecommendation],
        risk_assessments: List[RiskAssessment]
    ):
        """保存抽样结果"""
        now = datetime.now()

        with get_db_cursor() as cursor:
            for rec in recommendations:
                sample_id = str(uuid.uuid4())

                cursor.execute(
                    """
                    INSERT INTO samples
                    (id, project_id, voucher_id, risk_score, reason, sampled_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        sample_id,
                        project_id,
                        rec.voucher_id,
                        None,  # 将优先级作为风险分数参考
                        rec.reason,
                        now
                    ]
                )

            get_db().commit()


class VoucherUnderstandingService:
    """凭证理解服务"""

    def __init__(self, llm_svc: LLMService = None):
        self.llm = llm_svc if llm_svc else llm_service

    async def understand_voucher(
        self,
        voucher: Dict[str, Any],
        ocr_text: str = None
    ) -> Dict[str, Any]:
        """
        理解凭证内容

        Args:
            voucher: 凭证数据
            ocr_text: OCR识别文本

        Returns:
            Dict: 理解结果
        """
        prompt = self._build_understanding_prompt(voucher, ocr_text)

        messages = [
            ChatMessage(role="system", content=self._get_understanding_system_prompt()),
            ChatMessage(role="user", content=prompt)
        ]

        try:
            response = await self.llm.chat(messages, temperature=0.5)

            # 解析响应
            result = self._parse_understanding_response(response.content)

            return result

        except Exception as e:
            return {
                "error": str(e),
                "business_type": "未知",
                "accounting_entry": "",
                "risk_points": [],
                "key_notes": []
            }

    def _get_understanding_system_prompt(self) -> str:
        """获取理解任务的系统提示"""
        return """你是一位资深会计师，请分析并理解凭证的内容。

请识别以下信息：
1. 业务类型：采购、销售、费用、资产、负债等
2. 涉及的会计分录：借方和贷方科目
3. 可能的风险点
4. 需要关注的要点

请以JSON格式输出：
{
    "business_type": "业务类型",
    "accounting_entry": "借：xxx 贷：xxx",
    "risk_points": ["风险点1", "风险点2"],
    "key_notes": ["关注要点1", "关注要点2"],
    "summary": "凭证内容摘要"
}"""

    def _build_understanding_prompt(
        self,
        voucher: Dict[str, Any],
        ocr_text: str = None
    ) -> str:
        """构建理解提示"""
        info = f"""
凭证编号: {voucher.get('voucher_no', '未知')}
日期: {voucher.get('voucher_date', '未知')}
金额: {voucher.get('amount', 0)}
科目: {voucher.get('subject_code', '')} {voucher.get('subject_name', '')}
摘要: {voucher.get('description', '无')}
"""
        if ocr_text:
            info += f"\nOCR识别内容:\n{ocr_text[:500]}"

        return f"请分析以下凭证：\n{info}\n\n请输出分析结果（仅输出JSON）："

    def _parse_understanding_response(self, response: str) -> Dict[str, Any]:
        """解析理解响应"""
        try:
            return extract_json_from_llm_response(response)

        except (ValueError, KeyError):
            return {
                "business_type": "未知",
                "accounting_entry": "",
                "risk_points": [],
                "key_notes": [],
                "summary": response[:200] if len(response) > 200 else response
            }


# 全局服务实例
risk_analyzer = VoucherRiskAnalyzer()
intelligent_sampler = IntelligentSampler()
voucher_understanding_service = VoucherUnderstandingService()