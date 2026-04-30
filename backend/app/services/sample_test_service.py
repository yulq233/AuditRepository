"""
样本测试服务

管理样本测试流程、AI测试、人工复核、错报记录
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid
import json
import base64
import os

from app.core.database import get_db_cursor, get_db
from app.services.llm_service import llm_service, ChatMessage
from app.services.ai_sampling_service import risk_analyzer, RiskAssessment


class SampleTestStatus(str, Enum):
    """样本测试状态"""
    PENDING = "pending"              # 待测试
    TESTING = "testing"              # 测试中
    COMPLETED = "completed"          # 已完成（正常）
    SUSPECTED_ERROR = "suspected_error"  # 疑似错报
    NEEDS_REVIEW = "needs_review"    # 需人工复核
    EXCEPTION = "exception"          # 异常


class AIConclusion(str, Enum):
    """AI判定结论"""
    VALID = "valid"              # 真实合理
    ABNORMAL = "abnormal"        # 存在异常
    UNCERTAIN = "uncertain"      # 无法判断


class MisstatementType(str, Enum):
    """错报类型"""
    AMOUNT_ERROR = "amount_error"          # 金额错误
    MISSING_DOC = "missing_doc"            # 缺少支持性单据
    FICTITIOUS = "fictitious"              # 虚构交易
    CLASSIFICATION = "classification"      # 分类错误
    OTHER = "other"                        # 其他


@dataclass
class MisstatementRecord:
    """错报记录"""
    id: str
    sample_id: str
    project_id: str
    misstatement_type: str
    misstatement_amount: float
    original_amount: float
    correct_amount: float
    description: str
    identified_by: str  # ai/manual
    is_confirmed: bool


class SampleTestService:
    """样本测试服务"""

    async def execute_ai_test(
        self,
        project_id: str,
        sample_ids: List[str]
    ) -> Dict[str, Any]:
        """
        执行AI测试

        对样本列表进行批量AI风险分析和证据链校验

        Args:
            project_id: 项目ID
            sample_ids: 样本ID列表

        Returns:
            Dict: 测试结果统计
        """
        results = []
        tested_count = 0
        need_review_count = 0
        error_count = 0

        for sample_id in sample_ids:
            # 获取样本和凭证信息
            sample_data = self._get_sample_data(sample_id)
            if not sample_data:
                results.append({
                    "sample_id": sample_id,
                    "error": "样本不存在"
                })
                error_count += 1
                continue

            # 更新状态为测试中
            self._update_sample_status(sample_id, SampleTestStatus.TESTING)

            try:
                # 执行风险分析（简化版，实际应调用AI服务）
                risk_assessment = await self._analyze_voucher_risk(
                    sample_data['voucher']
                )

                # 执行证据链校验
                evidence_result = await self._analyze_evidence_chain(
                    sample_data['voucher'],
                    sample_data.get('attachments', [])
                )

                # 综合判定
                ai_conclusion = self._determine_conclusion(
                    risk_assessment,
                    evidence_result
                )

                # 保存AI测试结果
                self._save_ai_test_result(
                    sample_id=sample_id,
                    voucher_id=sample_data['voucher']['id'],
                    conclusion=ai_conclusion,
                    risk_assessment=risk_assessment,
                    evidence_result=evidence_result
                )

                # 如果判定为异常，自动创建疑似错报
                if ai_conclusion == AIConclusion.ABNORMAL:
                    self._create_suspected_misstatement(
                        sample_id=sample_id,
                        project_id=project_id,
                        risk_assessment=risk_assessment
                    )

                needs_review = ai_conclusion in [AIConclusion.ABNORMAL, AIConclusion.UNCERTAIN]
                if needs_review:
                    need_review_count += 1

                results.append({
                    "sample_id": sample_id,
                    "conclusion": ai_conclusion.value,
                    "risk_level": risk_assessment.get('risk_level'),
                    "confidence": risk_assessment.get('confidence'),
                    "needs_review": needs_review
                })
                tested_count += 1

                # 根据AI判定结果更新状态
                if ai_conclusion == AIConclusion.ABNORMAL:
                    # AI判定为"存在异常"，标记为"疑似错报"
                    self._update_sample_status(sample_id, SampleTestStatus.SUSPECTED_ERROR)
                elif ai_conclusion == AIConclusion.UNCERTAIN:
                    # AI判定为"无法判断"，标记为"需人工复核"
                    self._update_sample_status(sample_id, SampleTestStatus.NEEDS_REVIEW)
                else:
                    # AI判定为"真实合理"，标记为"已完成"
                    self._update_sample_status(sample_id, SampleTestStatus.COMPLETED)

            except Exception as e:
                self._update_sample_status(sample_id, SampleTestStatus.EXCEPTION)
                results.append({
                    "sample_id": sample_id,
                    "error": str(e)
                })
                error_count += 1

        # 更新抽样记录的测试统计
        self._update_sampling_record_stats(project_id, tested_count)

        return {
            "total_tested": tested_count,
            "need_review_count": need_review_count,
            "error_count": error_count,
            "results": results
        }

    def _get_sample_data(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """获取样本数据"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT s.id, s.voucher_id, v.id, v.voucher_no, v.amount,
                       v.subject_code, v.subject_name, v.description, v.counterparty
                FROM samples s
                JOIN vouchers v ON s.voucher_id = v.id
                WHERE s.id = ?
                """,
                [sample_id]
            )
            row = cursor.fetchone()
            if not row:
                return None

            voucher = {
                "id": row[2],
                "voucher_no": row[3],
                "amount": float(row[4]) if row[4] else 0,
                "subject_code": row[5],
                "subject_name": row[6],
                "description": row[7],
                "counterparty": row[8]
            }

            # 获取附件
            cursor.execute(
                """
                SELECT id, file_name, file_path, recognition_result
                FROM voucher_attachments
                WHERE voucher_id = ?
                """,
                [voucher['id']]
            )
            attachments = [
                {
                    "id": row[0],
                    "file_name": row[1],
                    "file_path": row[2],
                    "recognition_result": row[3]
                }
                for row in cursor.fetchall()
            ]

            return {
                "sample_id": row[0],
                "voucher": voucher,
                "attachments": attachments
            }

    def _update_sample_status(self, sample_id: str, status: SampleTestStatus):
        """更新样本测试状态"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE samples
                SET test_status = ?, tested_at = ?
                WHERE id = ?
                """,
                [status.value, datetime.now(), sample_id]
            )
            get_db().commit()

    async def _analyze_voucher_risk(self, voucher: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析凭证风险

        使用 VoucherRiskAnalyzer 进行智能风险分析，保持与向导页面风险分析一致
        """
        try:
            # 使用统一的 VoucherRiskAnalyzer 进行风险分析
            assessment = await risk_analyzer.analyze_voucher(voucher)

            return {
                "risk_score": assessment.risk_score,
                "risk_level": assessment.risk_level,
                "confidence": assessment.confidence,
                "risk_factors": assessment.risk_factors,
                "analysis": assessment.explanation
            }

        except Exception as e:
            # 分析失败时，使用与 VoucherRiskAnalyzer 一致的降级处理
            amount = voucher.get('amount', 0)
            description = voucher.get('description', '')

            risk_factors = []
            risk_score = 30  # 默认基础分

            # 金额评估 (与 VoucherRiskAnalyzer 提示词保持一致)
            if amount >= 100000:
                risk_factors.append("金额较大，需重点关注")
                risk_score += 25
            elif amount >= 50000:
                risk_factors.append("金额中等偏高，建议关注")
                risk_score += 15
            elif amount >= 10000:
                risk_score += 5

            # 摘要检查
            if not description or len(description) < 5:
                risk_factors.append("摘要描述不完整")
                risk_score += 10

            # 关联方检查
            counterparty = voucher.get('counterparty', '')
            if counterparty and any(kw in counterparty for kw in ['关联', '集团', '内部']):
                risk_factors.append("关联方交易")
                risk_score += 20

            # 使用与 VoucherRiskAnalyzer 一致的风险等级阈值
            if risk_score >= 70:
                risk_level = "high"
            elif risk_score >= 50:
                risk_level = "medium"
            else:
                risk_level = "low"

            return {
                "risk_score": min(risk_score, 100),
                "risk_level": risk_level,
                "confidence": 0.5,
                "risk_factors": risk_factors if risk_factors else ["基础风险评估"],
                "analysis": f"AI分析失败，使用规则引擎评估: {str(e)[:50]}"
            }

    async def _analyze_evidence_chain(
        self,
        voucher: Dict[str, Any],
        attachments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析证据链

        使用LLM进行多模态识别，检查合同、发票、物流单、银行回单等
        """
        result = {
            "has_contract": False,
            "has_invoice": False,
            "has_receipt": False,
            "has_logistics": False,
            "match_status": "unknown",
            "anomalies": [],
            "completeness_score": 0,
            "attachment_analysis": [],
            "cross_validation": {}
        }

        # 分析每个附件
        for attachment in attachments:
            attachment_result = await self._analyze_single_attachment(voucher, attachment)
            result["attachment_analysis"].append(attachment_result)

            # 汇总附件类型
            doc_type = attachment_result.get("doc_type")
            if doc_type == "contract":
                result["has_contract"] = True
            elif doc_type == "invoice":
                result["has_invoice"] = True
            elif doc_type == "receipt":
                result["has_receipt"] = True
            elif doc_type == "logistics":
                result["has_logistics"] = True

            # 收集异常
            if attachment_result.get("anomalies"):
                result["anomalies"].extend(attachment_result["anomalies"])

        # 如果没有附件，尝试使用规则分析
        if not attachments:
            result["anomalies"].append("缺少支持性单据")
            result["match_status"] = "incomplete"
            return result

        # 计算完整性分数
        if result["has_invoice"]:
            result["completeness_score"] += 35
        if result["has_contract"]:
            result["completeness_score"] += 25
        if result["has_receipt"]:
            result["completeness_score"] += 25
        if result["has_logistics"]:
            result["completeness_score"] += 15

        # 使用LLM进行交叉验证
        if attachments:
            cross_validation = await self._cross_validate_evidence(voucher, result["attachment_analysis"])
            result["cross_validation"] = cross_validation
            if cross_validation.get("discrepancies"):
                result["anomalies"].extend(cross_validation["discrepancies"])

        # 确定匹配状态
        if result["completeness_score"] >= 70 and len(result["anomalies"]) == 0:
            result["match_status"] = "matched"
        elif result["completeness_score"] >= 40:
            result["match_status"] = "partial"
        else:
            result["match_status"] = "incomplete"
            if "证据链不完整" not in result["anomalies"]:
                result["anomalies"].append("证据链不完整")

        return result

    async def _analyze_single_attachment(
        self,
        voucher: Dict[str, Any],
        attachment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析单个附件"""
        file_name = attachment.get('file_name', '')
        file_path = attachment.get('file_path', '')
        recognition_result = attachment.get('recognition_result')

        result = {
            "file_name": file_name,
            "doc_type": "unknown",
            "anomalies": [],
            "extracted_info": {},
            "confidence": 0.5
        }

        # 基于文件名识别文档类型
        file_lower = file_name.lower()
        if '合同' in file_lower or 'contract' in file_lower:
            result["doc_type"] = "contract"
        elif '发票' in file_lower or 'invoice' in file_lower or 'fa piao' in file_lower:
            result["doc_type"] = "invoice"
        elif '回单' in file_lower or 'receipt' in file_lower or '银行' in file_lower:
            result["doc_type"] = "receipt"
        elif '物流' in file_lower or '快递' in file_lower or '运单' in file_lower:
            result["doc_type"] = "logistics"

        # 如果已有OCR识别结果，使用LLM分析
        if recognition_result:
            try:
                analysis = await self._analyze_recognition_result(voucher, recognition_result, result["doc_type"])
                result["extracted_info"] = analysis.get("extracted_info", {})
                result["confidence"] = analysis.get("confidence", 0.7)
                if analysis.get("anomalies"):
                    result["anomalies"].extend(analysis["anomalies"])
                if analysis.get("doc_type") and result["doc_type"] == "unknown":
                    result["doc_type"] = analysis["doc_type"]
            except Exception as e:
                result["anomalies"].append(f"附件分析异常: {str(e)}")

        # 如果是图片文件且有文件路径，尝试多模态识别
        elif file_path and any(file_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.pdf']):
            try:
                multimodal_result = await self._multimodal_analyze_attachment(voucher, file_path, result["doc_type"])
                if multimodal_result:
                    result["extracted_info"] = multimodal_result.get("extracted_info", {})
                    result["confidence"] = multimodal_result.get("confidence", 0.7)
                    if multimodal_result.get("anomalies"):
                        result["anomalies"].extend(multimodal_result["anomalies"])
            except Exception as e:
                # 多模态识别失败，降级为基本信息
                result["anomalies"].append("无法识别附件内容")

        return result

    async def _analyze_recognition_result(
        self,
        voucher: Dict[str, Any],
        recognition_result: str,
        doc_type: str
    ) -> Dict[str, Any]:
        """使用LLM分析OCR识别结果"""
        prompt = f"""请分析以下文档识别结果，提取关键信息并检查是否存在异常。

凭证信息：
- 金额：{voucher.get('amount', 0):,.2f}元
- 日期：{voucher.get('voucher_date', '未知')}
- 摘要：{voucher.get('description', '无')}

文档识别结果：
{recognition_result[:2000]}

请以JSON格式输出：
{{
    "doc_type": "<contract/invoice/receipt/logistics/unknown>",
    "extracted_info": {{
        "amount": <金额>,
        "date": "<日期>",
        "party": "<交易方>",
        "other": "<其他关键信息>"
    }},
    "confidence": <0-1的置信度>,
    "anomalies": ["异常1", "异常2"]
}}

检查要点：
1. 金额是否与凭证金额一致
2. 日期是否合理
3. 交易方是否匹配
4. 是否有涂改、模糊等异常

请直接输出JSON。"""

        try:
            messages = [
                ChatMessage(role="system", content="你是一位专业的审计文档分析专家，擅长从OCR结果中提取关键信息并识别异常。"),
                ChatMessage(role="user", content=prompt)
            ]

            response = await llm_service.chat(messages, temperature=0.2, max_tokens=1024)
            content = response.content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        except Exception:
            return {"extracted_info": {}, "confidence": 0.5, "anomalies": []}

    async def _multimodal_analyze_attachment(
        self,
        voucher: Dict[str, Any],
        file_path: str,
        doc_type: str
    ) -> Optional[Dict[str, Any]]:
        """使用多模态LLM分析附件图片"""
        # 读取图片并编码为base64
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            prompt = f"""请分析这张文档图片，提取关键信息。

凭证参考信息：
- 金额：{voucher.get('amount', 0):,.2f}元
- 日期：{voucher.get('voucher_date', '未知')}

请识别文档类型（合同/发票/银行回单/物流单等），提取关键信息，并检查是否有异常。

以JSON格式输出：
{{
    "doc_type": "<contract/invoice/receipt/logistics/unknown>",
    "extracted_info": {{
        "amount": <识别的金额>,
        "date": "<日期>",
        "party": "<交易方>",
        "doc_number": "<单据编号>"
    }},
    "confidence": <0-1的置信度>,
    "anomalies": ["异常描述"]
}}"""

            messages = [
                ChatMessage(role="system", content="你是一位专业的审计文档识别专家，擅长识别和分析各类财务单据。"),
                ChatMessage(role="user", content=prompt, images=[image_base64])
            ]

            response = await llm_service.chat_with_images(messages, temperature=0.2, max_tokens=1024)
            content = response.content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            return None

    async def _cross_validate_evidence(
        self,
        voucher: Dict[str, Any],
        attachment_analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """交叉验证证据链"""
        if not attachment_analyses:
            return {"is_consistent": False, "discrepancies": ["缺少支持性单据"]}

        prompt = f"""请对以下凭证和附件进行交叉验证，检查信息一致性。

凭证信息：
- 金额：{voucher.get('amount', 0):,.2f}元
- 摘要：{voucher.get('description', '无')}

附件分析结果：
{json.dumps(attachment_analyses, ensure_ascii=False, indent=2)}

请检查：
1. 各附件金额是否一致，是否与凭证金额匹配
2. 日期是否合理
3. 交易方是否一致
4. 是否存在矛盾或不合理之处

以JSON格式输出：
{{
    "is_consistent": <true/false>,
    "discrepancies": ["不一致项1", "不一致项2"],
    "validation_details": "验证说明"
}}"""

        try:
            messages = [
                ChatMessage(role="system", content="你是一位专业的审计证据链验证专家，擅长发现文档之间的不一致。"),
                ChatMessage(role="user", content=prompt)
            ]

            response = await llm_service.chat(messages, temperature=0.2, max_tokens=1024)
            content = response.content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception:
            return {"is_consistent": True, "discrepancies": []}

    def _determine_conclusion(
        self,
        risk_assessment: Dict[str, Any],
        evidence_result: Dict[str, Any]
    ) -> AIConclusion:
        """综合判定"""
        risk_level = risk_assessment.get('risk_level', 'low')
        confidence = risk_assessment.get('confidence', 0.5)
        anomalies = evidence_result.get('anomalies', [])
        completeness = evidence_result.get('completeness_score', 0)

        # 高风险且有异常
        if risk_level == "high" and confidence >= 0.7:
            if anomalies:
                return AIConclusion.ABNORMAL

        # 证据链不完整
        if completeness < 40:
            return AIConclusion.UNCERTAIN

        # 没有发票
        if not evidence_result.get('has_invoice'):
            return AIConclusion.UNCERTAIN

        # 低风险且证据完整
        if risk_level == "low" and completeness >= 70:
            return AIConclusion.VALID

        # 中风险
        if risk_level == "medium":
            if completeness >= 60 and not anomalies:
                return AIConclusion.VALID
            else:
                return AIConclusion.UNCERTAIN

        return AIConclusion.UNCERTAIN

    def _save_ai_test_result(
        self,
        sample_id: str,
        voucher_id: str,
        conclusion: AIConclusion,
        risk_assessment: Dict[str, Any],
        evidence_result: Dict[str, Any]
    ):
        """保存AI测试结果"""
        result_id = str(uuid.uuid4())
        now = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sample_ai_test_results
                (id, sample_id, voucher_id, ai_conclusion, confidence, risk_level,
                 risk_factors, anomaly_descriptions, evidence_analysis, needs_manual_review, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    result_id,
                    sample_id,
                    voucher_id,
                    conclusion.value,
                    risk_assessment.get('confidence', 0.5),
                    risk_assessment.get('risk_level'),
                    json.dumps(risk_assessment.get('risk_factors', [])),
                    json.dumps(evidence_result.get('anomalies', [])),
                    json.dumps(evidence_result),
                    conclusion in [AIConclusion.ABNORMAL, AIConclusion.UNCERTAIN],
                    now
                ]
            )

            # 更新样本的AI测试结果
            cursor.execute(
                """
                UPDATE samples
                SET ai_test_result = ?
                WHERE id = ?
                """,
                [conclusion.value, sample_id]
            )

            get_db().commit()

    def _create_suspected_misstatement(
        self,
        sample_id: str,
        project_id: str,
        risk_assessment: Dict[str, Any]
    ):
        """创建疑似错报记录"""
        misstatement_id = str(uuid.uuid4())
        now = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sample_misstatements
                (id, sample_id, project_id, misstatement_type, misstatement_amount,
                 identified_by, identified_at, is_confirmed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    misstatement_id,
                    sample_id,
                    project_id,
                    MisstatementType.OTHER.value,
                    None,  # 金额需要人工确认
                    "ai",
                    now,
                    False,
                    now
                ]
            )
            get_db().commit()

    def _update_sampling_record_stats(self, project_id: str, tested_count: int):
        """更新抽样记录统计"""
        with get_db_cursor() as cursor:
            # 获取最新的抽样记录
            cursor.execute(
                """
                SELECT id FROM sampling_records
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [project_id]
            )
            row = cursor.fetchone()
            if row:
                record_id = row[0]
                cursor.execute(
                    """
                    UPDATE sampling_records
                    SET tested_count = COALESCE(tested_count, 0) + ?
                    WHERE id = ?
                    """,
                    [tested_count, record_id]
                )
                get_db().commit()

    def record_misstatement(
        self,
        sample_id: str,
        project_id: str,
        misstatement_type: str,
        misstatement_amount: float,
        original_amount: float,
        correct_amount: float,
        description: str,
        evidence_path: str = None
    ) -> str:
        """
        记录错报

        手动记录或确认AI识别的错报
        """
        misstatement_id = str(uuid.uuid4())
        now = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sample_misstatements
                (id, sample_id, project_id, misstatement_type, misstatement_amount,
                 original_amount, correct_amount, description, evidence_path,
                 identified_by, identified_at, is_confirmed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    misstatement_id,
                    sample_id,
                    project_id,
                    misstatement_type,
                    misstatement_amount,
                    original_amount,
                    correct_amount,
                    description,
                    evidence_path,
                    "manual",
                    now,
                    True,
                    now
                ]
            )

            # 更新样本的错报金额
            cursor.execute(
                """
                UPDATE samples
                SET misstatement_amount = COALESCE(misstatement_amount, 0) + ?
                WHERE id = ?
                """,
                [misstatement_amount, sample_id]
            )

            # 更新抽样记录的错报统计
            cursor.execute(
                """
                UPDATE sampling_records
                SET misstatement_count = COALESCE(misstatement_count, 0) + 1,
                    total_misstatement_amount = COALESCE(total_misstatement_amount, 0) + ?
                WHERE id = (
                    SELECT record_id FROM samples WHERE id = ?
                )
                """,
                [misstatement_amount, sample_id]
            )

            get_db().commit()

        return misstatement_id

    def manual_override(
        self,
        sample_id: str,
        ai_result_id: str,
        override_conclusion: str,
        override_reason: str
    ):
        """
        人工修正AI判定

        Args:
            sample_id: 样本ID
            ai_result_id: AI测试结果ID
            override_conclusion: 修正后的结论 (valid/abnormal)
            override_reason: 修正原因
        """
        now = datetime.now()

        with get_db_cursor() as cursor:
            # 更新AI测试结果
            cursor.execute(
                """
                UPDATE sample_ai_test_results
                SET manual_override = ?,
                    override_reason = ?,
                    reviewed_at = ?
                WHERE id = ?
                """,
                [override_conclusion, override_reason, now, ai_result_id]
            )

            # 更新样本状态
            new_status = SampleTestStatus.COMPLETED if override_conclusion == "valid" else SampleTestStatus.EXCEPTION
            cursor.execute(
                """
                UPDATE samples
                SET ai_test_result = ?, test_status = ?
                WHERE id = ?
                """,
                [override_conclusion, new_status.value, sample_id]
            )

            # 如果修正为正常，删除未确认的疑似错报
            if override_conclusion == "valid":
                cursor.execute(
                    """
                    DELETE FROM sample_misstatements
                    WHERE sample_id = ? AND identified_by = 'ai' AND is_confirmed = FALSE
                    """,
                    [sample_id]
                )

            get_db().commit()

    def get_misstatements(self, project_id: str, sample_id: str = None) -> List[Dict[str, Any]]:
        """获取错报记录列表"""
        with get_db_cursor() as cursor:
            conditions = ["project_id = ?"]
            params = [project_id]

            if sample_id:
                conditions.append("sample_id = ?")
                params.append(sample_id)

            cursor.execute(
                f"""
                SELECT id, sample_id, misstatement_type, misstatement_amount,
                       original_amount, correct_amount, description, severity,
                       identified_by, is_confirmed, created_at
                FROM sample_misstatements
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                """,
                params
            )

            return [
                {
                    "id": row[0],
                    "sample_id": row[1],
                    "misstatement_type": row[2],
                    "misstatement_amount": float(row[3]) if row[3] else None,
                    "original_amount": float(row[4]) if row[4] else None,
                    "correct_amount": float(row[5]) if row[5] else None,
                    "description": row[6],
                    "severity": row[7],
                    "identified_by": row[8],
                    "is_confirmed": bool(row[9]),
                    "created_at": row[10]
                }
                for row in cursor.fetchall()
            ]

    def get_test_statistics(self, project_id: str, record_id: str = None) -> Dict[str, Any]:
        """获取测试统计"""
        with get_db_cursor() as cursor:
            conditions = ["s.project_id = ?"]
            params = [project_id]

            if record_id:
                conditions.append("s.record_id = ?")
                params.append(record_id)

            # 样本状态统计
            cursor.execute(
                f"""
                SELECT test_status, COUNT(*)
                FROM samples s
                WHERE {' AND '.join(conditions)}
                GROUP BY test_status
                """,
                params
            )
            status_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # AI测试结果统计
            cursor.execute(
                f"""
                SELECT ai_test_result, COUNT(*)
                FROM samples s
                WHERE {' AND '.join(conditions)} AND ai_test_result IS NOT NULL
                GROUP BY ai_test_result
                """,
                params
            )
            result_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # 错报统计
            cursor.execute(
                f"""
                SELECT COUNT(*), COALESCE(SUM(misstatement_amount), 0)
                FROM sample_misstatements
                WHERE project_id = ?
                """,
                [project_id]
            )
            row = cursor.fetchone()
            misstatement_count = row[0] or 0
            total_misstatement_amount = float(row[1]) if row[1] else 0

            # 样本总数
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM samples s
                WHERE {' AND '.join(conditions)}
                """,
                params
            )
            total_samples = cursor.fetchone()[0] or 0

            return {
                "total_samples": total_samples,
                "status_distribution": status_stats,
                "result_distribution": result_stats,
                "misstatement_count": misstatement_count,
                "total_misstatement_amount": total_misstatement_amount,
                "pending_count": status_stats.get('pending', 0),
                "completed_count": status_stats.get('completed', 0),
                "exception_count": status_stats.get('exception', 0)
            }