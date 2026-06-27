from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# backend根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEYS_DIR = os.path.join(BASE_DIR, "keys")


def _read_key_file(filename: str) -> str:
    """从keys目录读取密钥文件"""
    path = os.path.join(KEYS_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


class Settings(BaseSettings):
    PROJECT_NAME: str = "蜀水智库 AI"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = "水利人自己的AI工作助手 - 覆盖设计、审批、施工、运维、应急全场景"
    
    # 数据库
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'shushui_ai.db')}"
    
    # 文件存储
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # 向量数据库
    VECTOR_DB_PATH: str = os.path.join(BASE_DIR, "vector_db")
    
    # Embedding 配置
    EMBEDDING_PROVIDER: str = "local"  # local, openai, volcano
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    VOLCANO_API_KEY: Optional[str] = None
    VOLCANO_BASE_URL: Optional[str] = None
    
    # LLM 配置
    LLM_PROVIDER: str = "mock"  # mock, openai, volcano
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    
    # Mock 模式
    MOCK_MODE: bool = True

    # 免费版额度配置
    FREE_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    PRO_MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    FREE_TOTAL_STORAGE: int = 20 * 1024 * 1024  # 20MB
    PRO_TOTAL_STORAGE: int = 500 * 1024 * 1024  # 500MB
    FREE_DAILY_QA: int = 10  # 每日免费问答次数
    FREE_ISO_TRIES: int = 1  # 免费ISO体验次数

    # 定价配置（前端展示用）
    PRICE_MONTHLY: int = 29  # 月卡价格（元）
    PRICE_YEARLY: int = 99  # 年卡价格（元）
    ADMIN_WECHAT: str = ""  # 管理员微信号（联系获取激活码）

    # 管理员Token（命令行工具使用）
    ADMIN_TOKEN: str = "shushui-admin-change-me"

    # 安全
    SECRET_KEY: str = "shushui-ai-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # 支付宝配置
    ALIPAY_ENABLED: bool = False
    ALIPAY_APP_ID: str = ""
    ALIPAY_PRIVATE_KEY_PATH: str = os.path.join(KEYS_DIR, "app_private_key.pem")
    ALIPAY_PUBLIC_KEY_PATH: str = os.path.join(KEYS_DIR, "alipay_public_key.pem")
    ALIPAY_NOTIFY_URL: str = ""
    ALIPAY_RETURN_URL: str = ""
    ALIPAY_SANDBOX: bool = True
    SERVER_PUBLIC_URL: str = "http://localhost:8000"
    
    # 个人收款码模式（适合个人开发者，无需企业资质）
    # 使用方式：用户扫码转账后，联系管理员获取激活码
    MANUAL_PAYMENT_ENABLED: bool = True  # 启用个人收款码模式
    MANUAL_PAYMENT_QR_URL: str = "/qrcodes/alipay.svg"  # 收款码图片路径（放在frontend/public/qrcodes/下）
    MANUAL_PAYMENT_NOTE: str = "扫码转账后，请添加管理员微信发送转账截图获取激活码"
    
    # Chunk 配置
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    
    # Agent配置
    AGENT_ENABLED: bool = True
    AGENT_MAX_STEPS: int = 8  # 最大推理步数，防止无限循环
    AGENT_MAX_TOOL_TOKENS: int = 4000  # 工具结果最大token
    AGENT_TEMPERATURE: float = 0.1  # Agent模式温度（低温度更稳定）
    AGENT_STREAM_ENABLED: bool = True  # 是否启用流式输出
    AGENT_MEMORY_MAX_TOKENS: int = 6000  # 对话记忆最大token
    AGENT_SUMMARY_TRIGGER: float = 0.8  # 记忆压缩触发阈值
    
    # FAISS配置
    FAISS_INDEX_TYPE: str = "FlatIP"  # 索引类型：FlatIP, IVFFlat, HNSW
    FAISS_NLIST: int = 100  # IVF聚类中心数（数据量>1万时调优）
    FAISS_MIN_VECTORS_FOR_IVF: int = 5000  # 向量数超过此值使用IVF索引
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )
    
    def get_alipay_private_key(self) -> str:
        """获取应用私钥内容"""
        # 优先使用环境变量中的密钥
        if hasattr(self, '_alipay_private_key_content') and self._alipay_private_key_content:
            return self._alipay_private_key_content
        return _read_key_file(os.path.basename(self.ALIPAY_PRIVATE_KEY_PATH)) if self.ALIPAY_PRIVATE_KEY_PATH else ""
    
    def get_alipay_public_key(self) -> str:
        """获取支付宝公钥内容"""
        if hasattr(self, '_alipay_public_key_content') and self._alipay_public_key_content:
            return self._alipay_public_key_content
        return _read_key_file(os.path.basename(self.ALIPAY_PUBLIC_KEY_PATH)) if self.ALIPAY_PUBLIC_KEY_PATH else ""


settings = Settings()
