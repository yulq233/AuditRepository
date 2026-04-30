"""
AI风险分析服务
基于大语言模型实现智能风险评估、凭证分析、审计建议生成
"""
import asyncio
import logging
import time
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

from app.core.database import get_db_cursor, get_db
from app.services.llm_service import (
    LLMService, LLMConfig, ChatMessage, llm_service, get_risk_analysis_service
)
from app.utils.common import extract_json_from_llm_response, generate_id


@dataclass
class AIRiskAssessment:
    """AI风险评估结果"""
    subject_code: str
    subject_name: str
    risk_level: str
    risk_score: float
    risk_factors: List[str]
    key_concerns: List[str]
    audit_suggestions: List[str]
    confidence: float
    analysis_summary: str


@dataclass
class VoucherAIRisk:
    """凭证AI风险分析结果"""
    voucher_id: str
    voucher_no: str
    risk_level: str
    risk_score: float
    risk_tags: List[str]
    risk_explanation: str
    audit_attention: List[str]
    confidence: float


@dataclass
class CounterpartyAIRisk:
    """交易对手AI风险分析"""
    counterparty_name: str
    risk_indicators: List[str]
    relationship_analysis: str
    transaction_patterns: List[str]
    risk_level: str
    audit_suggestions: List[str]


class AIRiskAnalyzer:
    """AI风险分析器"""

    def __init__(self, llm_svc: LLMService = None):
        # 使用专用风险分析服务，或传入自定义服务
        # 注意：如果不传入llm_svc，则每次调用时动态获取最新配置的服务
        self._llm = llm_svc

    @property
    def llm(self) -> LLMService:
        """动态获取LLM服务，确保使用最新配置"""
        return self._llm if self._llm else get_risk_analysis_service()

    async def analyze_subject_risk(
        self,
        project_id: str,
        subject_code: str,
        subject_name: str,
        voucher_stats: Dict[str, Any],
        historical_issues: List[Dict] = None
    ) -> AIRiskAssessment:
        """
        AI分析科目风险

        Args:
            project_id: 项目ID
            subject_code: 科目代码
            subject_name: 科目名称
            voucher_stats: 凭证统计信息
            historical_issues: 历史问题列表

        Returns:
            AIRiskAssessment: AI风险评估结果
        """
        start_time = time.time()

        prompt = self._build_subject_analysis_prompt(
            subject_code, subject_name, voucher_stats, historical_issues
        )

        messages = [
            ChatMessage(role="system", content=self._get_subject_system_prompt()),
            ChatMessage(role="user", content=prompt)
        ]

        try:
            logger.info(f"[AI科目分析] 开始分析科目: {subject_code} - {subject_name}")
            response = await self.llm.chat(messages, temperature=0.3)

            result = self._parse_subject_risk_response(
                response.content, subject_code, subject_name
            )

            elapsed = time.time() - start_time
            logger.info(f"[AI科目分析] 完成: {subject_code}, 风险={result.risk_level}, 分数={result.risk_score:.1f}, 耗时={elapsed:.2f}s")

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[AI科目分析] 失败: {subject_code}, 耗时={elapsed:.2f}s, 错误: {str(e)}")

            # 返回默认风险评估
            return AIRiskAssessment(
                subject_code=subject_code,
                subject_name=subject_name,
                risk_level="medium",
                risk_score=50.0,
                risk_factors=["AI分析暂时不可用"],
                key_concerns=["建议人工复核"],
                audit_suggestions=["请稍后重试AI分析"],
                confidence=0.0,
                analysis_summary="AI分析服务暂时不可用，请使用规则引擎结果或稍后重试"
            )

    async def analyze_voucher_risk(
        self,
        voucher: Dict[str, Any],
        attachment_content: Optional[str] = None
    ) -> VoucherAIRisk:
        """
        AI分析单个凭证风险

        Args:
            voucher: 凭证数据
            attachment_content: 附件识别内容（可选）

        Returns:
            VoucherAIRisk: 凭证AI风险分析结果
        """
        start_time = time.time()
        voucher_no = voucher.get('voucher_no', '未知')
        voucher_id = voucher.get('id', '')

        prompt = self._build_voucher_analysis_prompt(voucher, attachment_content)

        messages = [
            ChatMessage(role="system", content=self._get_voucher_system_prompt()),
            ChatMessage(role="user", content=prompt)
        ]

        try:
            logger.debug(f"[AI凭证分析] 开始分析: {voucher_no}")
            response = await self.llm.chat(messages, temperature=0.3)

            result = self._parse_voucher_risk_response(response.content, voucher_id, voucher_no)

            elapsed = time.time() - start_time
            logger.debug(f"[AI凭证分析] 完成: {voucher_no}, 风险={result.risk_level}, 耗时={elapsed:.2f}s")

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[AI凭证分析] 失败: {voucher_no}, 耗时={elapsed:.2f}s, 错误: {str(e)}")

            return VoucherAIRisk(
                voucher_id=voucher_id,
                voucher_no=voucher_no,
                risk_level="medium",
                risk_score=50.0,
                risk_tags=["分析失败"],
                risk_explanation="AI分析暂时不可用",
                audit_attention=["建议人工复核"],
                confidence=0.0
            )

    async def batch_analyze_vouchers(
        self,
        vouchers: List[Dict[str, Any]],
        batch_size: int = 10,
        attachment_contents: Optional[Dict[str, str]] = None
    ) -> List[VoucherAIRisk]:
        """
        批量AI分析凭证风险

        Args:
            vouchers: 凭证列表
            batch_size: 批次大小
            attachment_contents: 附件内容字典，key为voucher_id，value为附件识别内容

        Returns:
            List[VoucherAIRisk]: 风险分析结果列表
        """
        start_time = time.time()
        total_count = len(vouchers)
        logger.info(f"[AI批量分析] 开始分析 {total_count} 张凭证")

        results = []

        for i in range(0, total_count, batch_size):
            batch = vouchers[i:i + batch_size]
            batch_start = time.time()

            try:
                # 为每张凭证获取对应的附件内容
                tasks = []
                for v in batch:
                    voucher_id = v.get('id', '')
                    attachment_content = attachment_contents.get(voucher_id) if attachment_contents else None
                    tasks.append(self.analyze_voucher_risk(v, attachment_content))

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        logger.error(f"[AI批量分析] 凭证 {batch[j].get('voucher_no')} 分析异常: {result}")
                        results.append(VoucherAIRisk(
                            voucher_id=batch[j].get('id', ''),
                            voucher_no=batch[j].get('voucher_no', '未知'),
                            risk_level="medium",
                            risk_score=50.0,
                            risk_tags=["分析异常"],
                            risk_explanation=str(result),
                            audit_attention=["建议人工复核"],
                            confidence=0.0
                        ))
                    else:
                        results.append(result)

            except Exception as e:
                logger.error(f"[AI批量分析] 批次处理失败: {e}")

            batch_elapsed = time.time() - batch_start
            logger.info(f"[AI批量分析] 批次 {i//batch_size + 1} 完成, 耗时: {batch_elapsed:.2f}s")

        elapsed = time.time() - start_time
        logger.info(f"[AI批量分析] 全部完成: {len(results)}/{total_count}, 总耗时: {elapsed:.2f}s")

        return results

    async def analyze_counterparty(
        self,
        counterparty_name: str,
        transactions: List[Dict[str, Any]]
    ) -> CounterpartyAIRisk:
        """
        AI分析交易对手风险

        Args:
            counterparty_name: 交易对手名称
            transactions: 交易记录列表

        Returns:
            CounterpartyAIRisk: 交易对手风险分析
        """
        start_time = time.time()

        prompt = self._build_counterparty_analysis_prompt(counterparty_name, transactions)

        messages = [
            ChatMessage(role="system", content=self._get_counterparty_system_prompt()),
            ChatMessage(role="user", content=prompt)
        ]

        try:
            logger.info(f"[AI交易对手分析] 开始分析: {counterparty_name}")
            response = await self.llm.chat(messages, temperature=0.3)

            result = self._parse_counterparty_risk_response(response.content, counterparty_name)

            elapsed = time.time() - start_time
            logger.info(f"[AI交易对手分析] 完成: {counterparty_name}, 耗时: {elapsed:.2f}s")

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[AI交易对手分析] 失败: {counterparty_name}, 错误: {str(e)}")

            return CounterpartyAIRisk(
                counterparty_name=counterparty_name,
                risk_indicators=["AI分析暂时不可用"],
                relationship_analysis="无法分析",
                transaction_patterns=[],
                risk_level="medium",
                audit_suggestions=["建议人工核实交易对手背景"]
            )

    async def generate_audit_recommendation(
        self,
        subject_code: str,
        subject_name: str,
        risk_score: float,
        risk_factors: List[str],
        material_amount: float,
        voucher_count: int
    ) -> str:
        """
        AI生成审计建议

        Args:
            subject_code: 科目代码
            subject_name: 科目名称
            risk_score: 风险分数
            risk_factors: 风险因素列表
            material_amount: 重要性金额
            voucher_count: 凭证数量

        Returns:
            str: 审计建议
        """
        prompt = f"""请为以下审计科目生成专业、具体的审计建议：

科目信息：
- 科目代码：{subject_code}
- 科目名称：{subject_name}
- 风险分数：{risk_score:.1f}分（满分100）
- 风险因素：{', '.join(risk_factors)}
- 重要性金额：¥{material_amount:,.2f}
- 凭证数量：{voucher_count}笔

请根据风险分数和风险因素，给出具体的审计程序建议，包括：
1. 重点关注的审计领域
2. 建议实施的审计程序
3. 需要获取的审计证据
4. 建议的抽样策略

请用专业但简洁的语言，输出一段审计建议（200字以内）。"""

        messages = [
            ChatMessage(role="system", content="你是一位资深审计专家，专注于审计程序设计和风险评估。请给出专业、可操作的审计建议。"),
            ChatMessage(role="user", content=prompt)
        ]

        try:
            response = await self.llm.chat(messages, temperature=0.5, max_tokens=500)
            return response.content.strip()
        except Exception as e:
            logger.error(f"[AI审计建议] 生成失败: {e}")
            return f"建议对该科目进行{voucher_count}笔凭证的详细检查，重点关注金额较大和异常的交易。"

    # ==================== 内部方法 ====================

    def _get_subject_system_prompt(self) -> str:
        """获取科目分析系统提示词"""
        return """你是一位资深审计专家，拥有丰富的财务审计和风险评估经验。

你的任务是分析会计科目的风险，识别潜在问题，并给出审计建议。

【分析框架】
1. 金额风险：金额大小、波动幅度、异常值
2. 业务复杂性：交易性质、关联关系、跨期交易
3. 内控风险：授权审批、职责分离、记录完整性
4. 合规风险：法规遵循、会计准则、披露要求
5. 舞弊风险：异常模式、关联方交易、资产挪用

【输出格式】
请严格按照以下JSON格式输出：
{
    "risk_level": "high/medium/low",
    "risk_score": 0-100,
    "risk_factors": ["简短标签1", "简短标签2", ...],
    "key_concerns": ["关键关注点1", "关键关注点2", ...],
    "audit_suggestions": ["审计建议1", "审计建议2", ...],
    "analysis_summary": "200字以内的风险分析总结"
}

【风险因素标签规范】
risk_factors中的每个标签应简短精炼（2-8字），例如：
- 金额类：大额交易、金额异常、整数金额
- 时间类：月末集中、年末集中、非工作日
- 摘要类：摘要模糊、敏感词汇、信息不足
- 科目类：敏感科目、科目异常
- 交易类：关联方、交易对手异常"""

    def _get_voucher_system_prompt(self) -> str:
        """获取凭证分析系统提示词"""
        return """你是一位专业的审计凭证分析专家。

你的任务是分析单张凭证的风险，识别潜在问题和异常。

【分析维度】
1. 金额合理性：是否异常（过大/过小/整数/拆分）
2. 时间合理性：工作日、月末、年末、跨期
3. 摘要完整性：是否清晰、合理、有敏感词
4. 科目匹配性：科目与摘要是否匹配
5. 交易对手：是否关联方、新客户、异常方
6. 附件一致性：附件内容与凭证信息是否一致，附件是否有异常信息

【风险标签要求】
risk_tags数组中必须包含具体的风险标签，每个标签应：
1. 简短精炼，控制在2-8个汉字（如"大额交易"、"月末集中"、"摘要模糊"）
2. 使用名词或名词短语，不加解释说明
3. 如果发现风险，至少列出2-3个标签

参考标签：大额交易、金额异常、月末集中、年末集中、非工作日、摘要模糊、敏感词汇、敏感科目、关联方、交易对手异常、附件不符、整数金额、跨期调整

【输出格式】
请严格按照以下JSON格式输出：
{
    "risk_level": "high/medium/low",
    "risk_score": 0-100,
    "risk_tags": ["风险标签1", "风险标签2", ...],
    "risk_explanation": "风险说明（100字以内）",
    "audit_attention": ["需关注事项1", "需关注事项2", ...]
}"""

    def _get_counterparty_system_prompt(self) -> str:
        """获取交易对手分析系统提示词"""
        return """你是一位审计专家，专注于交易对手风险分析。

你的任务是分析交易对手的风险，识别关联方、异常交易模式。

【分析维度】
1. 关联方识别：名称特征、交易频率、定价公允性
2. 交易集中度：金额占比、交易频次
3. 交易模式：时间分布、金额分布、业务类型
4. 异常信号：突击交易、大额往来、频繁调整

【输出格式】
请严格按照以下JSON格式输出：
{
    "risk_indicators": ["风险指标1", "风险指标2", ...],
    "relationship_analysis": "关联关系分析",
    "transaction_patterns": ["交易模式1", "交易模式2", ...],
    "risk_level": "high/medium/low",
    "audit_suggestions": ["审计建议1", "审计建议2", ...]
}"""

    def _build_subject_analysis_prompt(
        self,
        subject_code: str,
        subject_name: str,
        voucher_stats: Dict[str, Any],
        historical_issues: List[Dict] = None
    ) -> str:
        """构建科目分析提示词"""
        prompt = f"""请分析以下会计科目的风险：

【科目信息】
- 科目代码：{subject_code}
- 科目名称：{subject_name}

【凭证统计】
- 凭证数量：{voucher_stats.get('voucher_count', 0)} 笔
- 借方金额：¥{voucher_stats.get('debit_amount', 0):,.2f}
- 贷方金额：¥{voucher_stats.get('credit_amount', 0):,.2f}
- 最大单笔金额：¥{voucher_stats.get('max_amount', 0):,.2f}
- 平均金额：¥{voucher_stats.get('avg_amount', 0):,.2f}
- 交易对手数量：{voucher_stats.get('counterparty_count', 0)} 个

【金额分布】
- 10万以上凭证：{voucher_stats.get('large_count', 0)} 笔
- 1万-10万凭证：{voucher_stats.get('medium_count', 0)} 笔
- 1万以下凭证：{voucher_stats.get('small_count', 0)} 笔

【时间分布】
- 月末交易占比：{voucher_stats.get('month_end_ratio', 0)*100:.1f}%
- 年末交易占比：{voucher_stats.get('year_end_ratio', 0)*100:.1f}%
- 周末交易占比：{voucher_stats.get('weekend_ratio', 0)*100:.1f}%
"""

        if historical_issues:
            prompt += f"\n【历史问题】\n"
            for issue in historical_issues[:5]:
                prompt += f"- {issue.get('description', '未知问题')}\n"

        return prompt

    def _build_voucher_analysis_prompt(self, voucher: Dict[str, Any], attachment_content: Optional[str] = None) -> str:
        """构建凭证分析提示词"""
        amount = voucher.get('amount', 0)
        amount_hint = ""
        if amount >= 100000:
            amount_hint = "（金额较大，需重点关注）"
        elif amount >= 50000:
            amount_hint = "（金额中等偏高，建议关注）"

        prompt = f"""请分析以下凭证的风险：

【凭证信息】
- 凭证编号：{voucher.get('voucher_no', '未知')}
- 凭证日期：{voucher.get('voucher_date', '未知')}
- 凭证金额：¥{amount:,.2f} {amount_hint}
- 科目代码：{voucher.get('subject_code', '未知')}
- 科目名称：{voucher.get('subject_name', '未知')}
- 摘要：{voucher.get('description', '无')}
- 交易对手：{voucher.get('counterparty', '无')}"""

        # 处理附件状态
        if attachment_content:
            prompt += "\n\n【附件识别内容】\n" + attachment_content

            # 检查是否有附件金额汇总
            import re
            summary_match = re.search(r'【附件金额汇总】.*?合计:\s*([\d,\.]+)', attachment_content)
            if summary_match:
                attachment_total = float(summary_match.group(1).replace(',', ''))
                # 计算差异
                diff = abs(amount - attachment_total)
                diff_ratio = (diff / amount * 100) if amount > 0 else 0

                prompt += f"\n\n【金额核对】"
                prompt += f"\n- 凭证金额: ¥{amount:,.2f}"
                prompt += f"\n- 附件合计: ¥{attachment_total:,.2f}"

                if diff_ratio < 1:
                    prompt += f"\n- 差异: ¥{diff:,.2f}（差异率{diff_ratio:.1f}%，基本一致）"
                elif diff_ratio < 5:
                    prompt += f"\n- 差异: ¥{diff:,.2f}（差异率{diff_ratio:.1f}%，存在小额差异）"
                else:
                    prompt += f"\n- 差异: ¥{diff:,.2f}（差异率{diff_ratio:.1f}%，金额不一致！）"

                prompt += "\n\n请重点核对凭证金额与附件合计金额是否一致。如金额不一致，请在risk_tags中添加\"附件金额不符\"标签。"
            else:
                prompt += "\n\n请结合附件内容与凭证信息进行风险分析，特别关注凭证信息与附件内容的一致性，如发现不一致请在risk_tags中添加相关标签"
        else:
            prompt += "\n\n【附件状态】该凭证暂无附件或附件未识别。如金额较大但缺少附件支撑，请在risk_tags中添加相关标签"

        prompt += "\n\n请识别风险并给出审计建议，务必在risk_tags中列出具体的风险标签。"
        return prompt

    def _build_counterparty_analysis_prompt(
        self,
        counterparty_name: str,
        transactions: List[Dict[str, Any]]
    ) -> str:
        """构建交易对手分析提示词"""
        total_amount = sum(t.get('amount', 0) for t in transactions)
        avg_amount = total_amount / len(transactions) if transactions else 0

        return f"""请分析以下交易对手的风险：

【交易对手信息】
- 名称：{counterparty_name}
- 交易笔数：{len(transactions)} 笔
- 交易总额：¥{total_amount:,.2f}
- 平均金额：¥{avg_amount:,.2f}

【交易明细】
{json.dumps(transactions[:10], ensure_ascii=False, indent=2)}

请识别关联方风险、异常交易模式，并给出审计建议。"""

    def _parse_subject_risk_response(
        self,
        response: str,
        subject_code: str,
        subject_name: str
    ) -> AIRiskAssessment:
        """解析科目风险响应"""
        try:
            data = extract_json_from_llm_response(response)

            # 清理 risk_level，移除多余标点
            risk_level = data.get("risk_level", "medium").strip().rstrip('.。,，')
            # 标准化风险等级
            if '高' in risk_level or risk_level.lower() == 'high':
                risk_level = 'high'
            elif '中' in risk_level or risk_level.lower() == 'medium':
                risk_level = 'medium'
            elif '低' in risk_level or risk_level.lower() == 'low':
                risk_level = 'low'
            else:
                risk_level = 'medium'

            # 清理风险因素，移除多余标点（包括中间位置的·）
            risk_factors = []
            for factor in data.get("risk_factors", []):
                factor = factor.strip()
                if factor:
                    # 移除中间位置的间隔号·
                    factor = factor.replace('·', '')
                    # 移除末尾标点
                    factor = factor.rstrip('.。,，')
                    if factor:
                        risk_factors.append(factor)

            return AIRiskAssessment(
                subject_code=subject_code,
                subject_name=subject_name,
                risk_level=risk_level,
                risk_score=float(data.get("risk_score", 50)),
                risk_factors=risk_factors,
                key_concerns=data.get("key_concerns", []),
                audit_suggestions=data.get("audit_suggestions", []),
                confidence=0.8,
                analysis_summary=data.get("analysis_summary", "")
            )
        except Exception as e:
            logger.error(f"[AI科目分析] 解析响应失败: {e}")
            return AIRiskAssessment(
                subject_code=subject_code,
                subject_name=subject_name,
                risk_level="medium",
                risk_score=50.0,
                risk_factors=["AI分析响应解析失败"],
                key_concerns=["建议人工复核"],
                audit_suggestions=["请检查AI服务状态"],
                confidence=0.0,
                analysis_summary="AI分析响应解析失败，请使用规则引擎结果"
            )

    def _parse_voucher_risk_response(
        self,
        response: str,
        voucher_id: str,
        voucher_no: str
    ) -> VoucherAIRisk:
        """解析凭证风险响应"""
        try:
            data = extract_json_from_llm_response(response)

            # 清理 risk_level，移除多余标点
            risk_level = data.get("risk_level", "medium").strip().rstrip('.。,，')
            # 标准化风险等级
            if '高' in risk_level or risk_level.lower() == 'high':
                risk_level = 'high'
            elif '中' in risk_level or risk_level.lower() == 'medium':
                risk_level = 'medium'
            elif '低' in risk_level or risk_level.lower() == 'low':
                risk_level = 'low'
            else:
                risk_level = 'medium'

            # 清理风险标签，移除多余标点（包括中间位置的·）
            risk_tags = []
            for tag in data.get("risk_tags", []):
                tag = tag.strip()
                if tag:
                    # 移除中间位置的间隔号·
                    tag = tag.replace('·', '')
                    # 移除末尾标点
                    tag = tag.rstrip('.。,，')
                    if tag:
                        risk_tags.append(tag)

            return VoucherAIRisk(
                voucher_id=voucher_id,
                voucher_no=voucher_no,
                risk_level=risk_level,
                risk_score=float(data.get("risk_score", 50)),
                risk_tags=risk_tags,
                risk_explanation=data.get("risk_explanation", ""),
                audit_attention=data.get("audit_attention", []),
                confidence=0.8
            )
        except Exception as e:
            logger.error(f"[AI凭证分析] 解析响应失败: {e}")
            return VoucherAIRisk(
                voucher_id=voucher_id,
                voucher_no=voucher_no,
                risk_level="medium",
                risk_score=50.0,
                risk_tags=["解析失败"],
                risk_explanation="AI响应解析失败",
                audit_attention=["建议人工复核"],
                confidence=0.0
            )

    def _parse_counterparty_risk_response(
        self,
        response: str,
        counterparty_name: str
    ) -> CounterpartyAIRisk:
        """解析交易对手风险响应"""
        try:
            data = extract_json_from_llm_response(response)

            return CounterpartyAIRisk(
                counterparty_name=counterparty_name,
                risk_indicators=data.get("risk_indicators", []),
                relationship_analysis=data.get("relationship_analysis", ""),
                transaction_patterns=data.get("transaction_patterns", []),
                risk_level=data.get("risk_level", "medium"),
                audit_suggestions=data.get("audit_suggestions", [])
            )
        except Exception as e:
            logger.error(f"[AI交易对手分析] 解析响应失败: {e}")
            return CounterpartyAIRisk(
                counterparty_name=counterparty_name,
                risk_indicators=["解析失败"],
                relationship_analysis="无法解析",
                transaction_patterns=[],
                risk_level="medium",
                audit_suggestions=["建议人工核实"]
            )


# 全局AI风险分析器实例
ai_risk_analyzer = AIRiskAnalyzer()