from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class ConversationSession(Base):
    """对话会话表"""
    __tablename__ = "conversation_sessions"
    
    id = Column(String(36), primary_key=True)  # UUID
    user_name = Column(String(100), index=True, nullable=False, default="default_user")
    title = Column(String(255))  # 会话标题（自动生成）
    mode = Column(String(50), default="agent")  # agent / simple_rag
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    summary = Column(Text, default="")  # 对话摘要
    metadata_json = Column(JSON, default=dict)
    
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")


class ConversationMessage(Base):
    """对话消息表（存储Agent完整轨迹）"""
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), ForeignKey("conversation_sessions.id"), index=True)
    role = Column(String(20))  # user / assistant / system / tool / thought
    content = Column(Text)
    tool_calls = Column(JSON)  # 工具调用记录 [{name, arguments, result, status, duration_ms}]
    token_usage = Column(JSON)  # token消耗统计
    step = Column(Integer, default=0)  # 推理步骤序号
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ConversationSession", back_populates="messages")


class AgentTaskLog(Base):
    """Agent任务执行日志表"""
    __tablename__ = "agent_task_logs"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), index=True)
    task_type = Column(String(50))  # 任务类型
    input_summary = Column(Text)  # 输入摘要
    tools_used = Column(JSON)  # 使用的工具列表
    steps_count = Column(Integer)  # 执行步数
    total_tokens = Column(Integer)
    duration_ms = Column(Integer)
    status = Column(String(20), default="success")  # success / failed / timeout
    error_msg = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
