from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class StepFeedback(Base):
    """
    记录测试人员对 AI 生成步骤的反馈（点赞/点踩/修正）。
    这些数据作为 RLHF 闭环的原始素材，被注入未来的 AI Prompt（项目记忆）。
    """
    __tablename__ = "step_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)  # 与项目绑定
    case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)
    step_index = Column(Integer, nullable=True)               # 对应步骤的下标

    # 反馈类型
    feedback_type = Column(String, nullable=False)            # thumbs_up / thumbs_down / correction
    original_step = Column(JSON, nullable=True)               # AI 原始生成的步骤
    corrected_step = Column(JSON, nullable=True)              # 人工修正后的步骤
    comment = Column(Text, nullable=True)                     # 自由文本说明

    # AI 提炼的规则摘要（在自动分析反馈后回填）
    ai_notes = Column(Text, nullable=True)

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", foreign_keys=[project_id])
    test_case = relationship("TestCase", foreign_keys=[case_id])
    creator = relationship("User", foreign_keys=[creator_id])
