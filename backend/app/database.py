"""Database configuration and helpers for the library management system."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


import os

# ---------------------------------------------------------------------------
# 数据库配置 (自动适配 Docker 和本地环境)
# ---------------------------------------------------------------------------

# 1. MySQL
# 优先读取 Docker 环境变量，读不到则使用你本地的配置 (localhost)
MYSQL_URL = os.getenv(
    "MYSQL_URL", 
    "mysql+pymysql://root:1234@localhost:3306/library_mysql"
)

# 2. PostgreSQL
POSTGRES_URL = os.getenv(
    "POSTGRES_URL", 
    "postgresql+psycopg2://postgres:123456@localhost:5432/library_pg"
)

# 3. SQL Server
# 本地用 sql_user:1，Docker 里自动用 sa:Password123!
SQLSERVER_URL = os.getenv(
    "SQLSERVER_URL", 
    "mssql+pymssql://sql_user:1@localhost:1433/library_sqlserver"
)


# SQLite 配置 (仅作为备用或测试用)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_URL = f"sqlite:///{DATA_DIR / 'library_test.db'}"

# 定义数据库映射字典
DATABASE_URLS: Dict[str, str] = {
    "MySQL": MYSQL_URL,
    "PostgreSQL": POSTGRES_URL,
    "SQLServer": SQLSERVER_URL,
}

# ---------------------------------------------------------------------------
# 2. 数据库引擎创建逻辑
# ---------------------------------------------------------------------------

def _create_engine(url: str) -> Engine:
    """创建数据库引擎，根据数据库类型自动调整参数"""
    connect_args = {}
    
    # 为不同数据库设置正确的编码参数
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    elif url.startswith("mysql"):
        connect_args["charset"] = "utf8mb4"
    elif url.startswith("postgresql"):
        connect_args["client_encoding"] = "utf8"
    elif url.startswith("mssql"):
        # connect_args["charset"] = "utf8"
        # the system default encoding is usually fine for mssql
        pass
    
    # 创建引擎
    return create_engine(
        url,
        connect_args=connect_args,
        future=True,
        # pool_pre_ping=True 能自动检测并重连断开的数据库连接，非常重要
        pool_pre_ping=True, 
        # 连接池配置，防止并发过高时报错 (SQLite 不支持这些参数，这里简单判断一下)
        pool_size=10 if not url.startswith("sqlite") else 5,
        max_overflow=20 if not url.startswith("sqlite") else 10,
    )

# 初始化所有引擎
# 注意：如果某个数据库连接失败，启动时会报错。请确保所有数据库服务都已开启。
ENGINES: Dict[str, Engine] = {name: _create_engine(url) for name, url in DATABASE_URLS.items()}

# 初始化所有 Session 工厂
SessionFactories: Dict[str, sessionmaker] = {
    name: sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    for name, engine in ENGINES.items()
}

Base = declarative_base()

# ---------------------------------------------------------------------------
# 3. 工具函数
# ---------------------------------------------------------------------------

def init_databases() -> None:
    """Create tables on every configured database."""
    from . import models  # noqa: F401 - ensure models are imported

    print("--- 开始初始化数据库表结构 ---")
    for name, engine in ENGINES.items():
        try:
            print(f"正在初始化: {name} ({engine.url.drivername})...")
            Base.metadata.create_all(bind=engine)
            print(f" -> 成功: {name}")
        except Exception as e:
            print(f" -> 失败: {name} 初始化错误! 请检查连接字符串或数据库是否已手动创建。")
            print(f"    错误详情: {e}")
    print("--- 数据库初始化完成 ---")


@contextmanager
def get_session(db_key: str) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    if db_key not in SessionFactories:
        raise ValueError(f"Database key '{db_key}' not found in configuration.")
        
    session = SessionFactories[db_key]()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - defensive
        session.rollback()
        raise
    finally:
        session.close()