from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class HealLog(Base):
    """
    记录 AI 自愈事件。
    每当 Runner 遇到元素定位失败并成功（或失败）自愈时，写入此表供人工审查。
    """
    __tablename__ = "heal_logs"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)
    element_id = Column(Integer, ForeignKey("page_elements.id"), nullable=True)
    step_index = Column(Integer, nullable=True)               # 第几步失败

    # 失败时的选择器
    original_selector = Column(String, nullable=False)
    # AI 修复后采用的选择器
    healed_selector = Column(String, nullable=True)
    heal_method = Column(String, nullable=True)               # locator_chain 的哪个级别生效

    # AI 分析结果
    locator_chain_json = Column(JSON, nullable=True)          # 完整的优先级链
    confidence = Column(Float, default=0.0)
    change_summary = Column(Text, nullable=True)              # AI 对变化的简短描述
    explanation = Column(Text, nullable=True)

    # 状态与截图
    status = Column(String, default="auto_healed")            # auto_healed / manual_review / failed
    screenshot_before = Column(Text, nullable=True)           # Base64 或路径
    screenshot_after = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    test_case = relationship("TestCase", foreign_keys=[case_id])
    element = relationship("PageElement", foreign_keys=[element_id])
