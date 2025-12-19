# 📚 Library Management System with Data Synchronization
> **基于异构数据库同步的高可用图书管理系统**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue 3](https://img.shields.io/badge/Frontend-Vue.js_3-4FC08D.svg?style=flat&logo=vuedotjs&logoColor=white)](https://vuejs.org)
[![Docker](https://img.shields.io/badge/Deployment-Docker-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

本项目是一个全栈图书管理系统，核心亮点在于实现了 **MySQL、PostgreSQL 和 SQL Server** 三种异构数据库之间的实时数据同步。系统采用前后端分离架构，集成了冲突检测、基于 JWT 的安全裁决机制以及交互式数据可视化报表。

---

## ✨ 核心特性 (Key Features)

- **🔄 异构数据库实时同步**
  - 自研 `SyncManager` 引擎，支持在 MySQL、PostgreSQL 和 SQL Server 之间进行微秒级的数据同步。
  - 智能识别数据变动，自动分发至所有已配置的副本数据库。

- **🛡️ 冲突检测与安全裁决**
  - **自动冲突捕获**：当多库数据版本不一致时，自动记录冲突详情。
  - **安全闭环**：通过邮件发送包含 **专用 JWT 令牌** 的深链接 (Deep Link)，管理员需二次验证密码后方可处理冲突，严格符合安全规范。

- **📊 交互式可视化看板**
  - 集成 **ECharts** 图表，提供数据同步趋势的下钻分析（从宏观趋势到单日详情）。
  - 实时监控各节点的同步状态、成功率及错误分布。

- **⚡ 高性能异步架构**
  - 后端基于 **FastAPI**，利用 `asyncio` 运行非阻塞的后台维护任务（如逾期检查），确保高并发下的系统响应速度。
  - 业务逻辑采用 SQLAlchemy 连接池技术，自动适配不同数据库的编码与方言。

- **🔐 完善的权限管理**
  - 基于 JWT (JSON Web Tokens) 的身份认证。
  - 细粒度的 RBAC 权限控制，区分 `admin` (管理员) 和 `student` (学生) 角色。

---

## 🛠️ 技术栈 (Tech Stack)

| 模块 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **Backend** | Python 3.10+, FastAPI | 高性能异步 Web 框架 |
| **ORM** | SQLAlchemy | 数据库对象映射与会话管理 |
| **Database** | MySQL, PostgreSQL, SQL Server | 多源异构数据库集群 |
| **Frontend** | Vue 3, Vue Router | 现代化的响应式前端框架 |
| **UI/Charts** | CSS3, ECharts | 交互式数据可视化 |
| **DevOps** | Docker, Docker Compose | 容器化部署与编排 |

---

## 📂 项目结构 (Project Layout)

```text
.
├── backend/                          # 🐍 后端工程 (FastAPI + SQLAlchemy)
│   ├── Dockerfile                    # 后端容器构建文件
│   ├── requirements.txt              # Python 依赖清单
│   ├── logs/                         # 日志目录
│   │   └── .gitignore
│   └── app/                          # 应用核心代码
│       ├── main.py                   # 🚀 程序入口 (App entry & Startup events)
│       ├── database.py               # 💾 异构数据库连接池与 Session 配置
│       ├── models.py                 # 🗄️ ORM 数据模型定义
│       ├── schemas.py                # 📝 Pydantic 数据校验模型
│       ├── crud.py                   # 🛠️ 数据库 CRUD 基础操作
│       ├── sync_manager.py           # 🔄 核心：多源数据同步引擎
│       ├── security.py               # 🔐 JWT 加密、解密与密码哈希
│       ├── email.py                  # 📧 邮件发送模块 (SMTP)
│       ├── config.py                 # ⚙️ 全局配置加载
│       ├── dependencies.py           # 💉 FastAPI 依赖注入 (Depends)
│       ├── consistency.py            # ⚖️ 数据一致性检查工具
│       ├── compat.py                 # 🐍 Python 版本兼容补丁
│       └── routers/                  # 🌐 API 路由模块
│           ├── books.py              # 图书管理接口
│           ├── borrow.py             # 借阅/归还流程接口
│           ├── seats.py              # 座位预约接口
│           ├── user.py               # 用户认证与管理接口
│           ├── conflicts.py          # ⚔️ 数据冲突查询与解决接口
│           ├── stats.py              # 📊 统计报表接口
│           ├── dashboard.py          # 仪表盘聚合数据接口
│           └── settings.py           # 系统参数设置接口
│
├── frontend/                         # ⚡ 前端工程 (Vue 3 + Vite)
│   ├── index.html                    # 静态入口文件
│   ├── package.json                  # 前端依赖配置
│   ├── vite.config.js                # Vite 构建配置
│   └── src/                          # 前端源码目录
│       ├── main.js                   # Vue 入口文件
│       ├── App.vue                   # 根组件
│       ├── api.js                    # 📡 Axios 接口封装层
│       ├── router/
│       │   └── index.js              # 🚦 前端路由配置
│       ├── components/
│       │   ├── Login.vue             # 登录组件
│       │   └── WebLayout.vue         # 全局布局组件 (Sidebar/Header)
│       ├── views/                    # 📺 页面视图
│       │   ├── Dashboard.vue         # 仪表盘主页
│       │   ├── BookList.vue          # 图书查询与管理
│       │   ├── MyBorrow.vue          # 我的借阅记录
│       │   ├── SeatReservation.vue   # 座位预约页面
│       │   ├── AdminSeats.vue        # 座位后台管理
│       │   ├── SyncStats.vue         # 📈 数据同步监控看板
│       │   ├── SyncLogs.vue          # 📝 详细同步日志
│       │   ├── ConflictResolution.vue# 🛡️ 冲突裁决与处理
│       │   └── SystemSettings.vue    # 系统设置
│       └── assets/
│           └── logo.png              # 静态资源
│
└── docker-compose.yml                # 🐳 容器编排配置 (一键启动)
```

## 🚀 快速开始 (Getting Started)
方式一：使用 Docker 部署 (推荐)
这是最简单的运行方式，可以一键启动前后端及三个数据库实例。

```Bash

# 1. 构建并启动所有服务
docker-compose up -d --build

# 2. 检查运行状态
docker ps

# 3. 访问系统
# 前端页面: http://localhost:8080
# API 文档: http://localhost:8000/docs
```
方式二：本地开发模式
如果您需要调试代码，可以分别启动后端和前端。

1. 启动后端
```Bash

cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows 使用: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动 FastAPI 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
2. 启动前端
```Bash

cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 前端通常运行在 http://localhost:5173 或 http://localhost:8081
```
🔗 API 文档
后端启动后，访问 `http://localhost:8000/docs` 即可查看自动生成的 Swagger UI 文档。

主要 API 模块包括：

`Auth`: 用户注册、登录 (JWT 获取)

`Books`: 图书增删改查

`Sync`: 同步日志查询、冲突解决

`Stats`: 系统统计数据

`Dashboard`: 仪表盘聚合数据
---
🤝 贡献与反馈
欢迎提交 Issue 或 Pull Request 来改进本项目。
---
- Note: 本项目为演示异构数据库同步原理的教学/原型系统，生产环境使用建议配置更严格的防火墙与密钥管理策略。