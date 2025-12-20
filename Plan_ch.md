# 在线图书馆管理系统技术报告
> **基于 FastAPI + Vue 3 的异构数据库同步与高可用架构实践**

---

### 1. 实践目标

本课程实践旨在运用数据库系统的基本理论知识，结合现代软件工程方法，独立设计并实现一个完整的**分布式数据库应用系统**。通过本项目，重点掌握以下核心能力：

1.  **全栈开发能力**：基于 **FastAPI (后端)** 和 **Vue 3 (前端)** 构建高性能的前后端分离应用。
2.  **异构数据库集成**：实现 **MySQL、PostgreSQL、SQL Server** 三种不同数据库之间的数据互通与一致性维护。
3.  **复杂业务逻辑实现**：设计并实现包括借阅管理、座位预约、冲突裁决在内的完整业务流。
4.  **工程化部署**：利用 **Docker** 容器技术实现多数据库环境的一键编排与隔离部署。

---

### 2. 系统需求分析与总体架构

#### 2.1 需求分析
系统旨在解决传统单体图书馆系统在数据容灾和跨平台访问上的局限，主要功能模块包括：
* **资源管理**：图书的增删改查、实时库存监控。
* **流通管理**：借书、还书、逾期检测及罚款计算。
* **用户服务**：读者权限管理、座位在线预约与释放。
* **数据同步核心**：实现多源数据库的实时同步，提供数据冲突检测与可视化监控。
* **安全运维**：基于 JWT 的身份认证、基于邮件和深链接（Deep Link）的安全冲突处理。

#### 2.2 系统架构设计
本系统采用 **B/S (Browser/Server)** 架构，整体部署在 Docker 容器群中。

* **前端层 (Frontend)**：基于 **Vue 3 + Vite** 构建单页应用 (SPA)。使用 **Axios** 进行 API 请求，**ECharts** 渲染数据看板。
* **应用层 (Backend)**：基于 **FastAPI** 框架。利用 Python 的 `asyncio` 实现异步任务调度（如邮件发送、同步分发），利用 **SQLAlchemy** 连接池管理多数据库会话。
* **数据层 (Data Layer)**：部署三个独立的数据库实例（MySQL, PostgreSQL, SQL Server），通过应用层中间件 `SyncManager` 保证数据最终一致性。

---

### 3. 数据库与同步机制设计

#### 3.1 数据库表结构设计
系统数据库严格遵循 **3NF (第三范式)** 设计，共包含 **9 张核心数据表**，覆盖业务、日志及系统配置。

**(1) 图书信息表 (`books`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键，自增 |
| title | String | 书名 |
| author | String | 作者 |
| isbn | String | ISBN (唯一索引) |
| category | String | 分类 |
| total_copies | Integer | 总藏书量 |
| available_copies | Integer | 在馆数量 |
| rating | Float | 评分 |
| updated_at | DateTime | 最后更新时间 |

**(2) 用户信息表 (`users`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| username | String | 用户名 (唯一) |
| password_hash | String | 密码哈希值 (SHA-256) |
| email | String | 邮箱地址 |
| role | Enum | 用户角色 (admin/student) |
| created_at | DateTime | 注册时间 |

**(3) 借阅记录表 (`borrow_records`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| user_id | Integer | 外键 -> users.id |
| book_id | Integer | 外键 -> books.id |
| borrowed_at | DateTime | 借出时间 |
| due_at | DateTime | 应还时间 |
| returned_at | DateTime | 实际归还时间 |
| status | String | 状态 (borrowed/returned) |

**(4) 逾期罚款表 (`fines`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| user_id | Integer | 外键 -> users.id |
| borrow_record_id | Integer | 外键 -> borrow_records.id |
| amount | Numeric | 罚款金额 |
| paid | Boolean | 是否已支付 |

**(5) 座位信息表 (`seats`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| floor | Integer | 楼层 |
| code | String | 座位号 (如 "2F-A01", 唯一) |
| status | String | 状态 (available/occupied) |

**(6) 座位预约表 (`seat_reservations`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| user_id | Integer | 外键 -> users.id |
| seat_id | Integer | 外键 -> seats.id |
| reserved_at | DateTime | 预约创建时间 |
| expires_at | DateTime | 预约过期时间 |
| status | String | 状态 (active/cancelled) |

**(7) 同步日志表 (`sync_logs`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| source_db | String | 源数据库标识 |
| target_db | String | 目标数据库标识 |
| table_name | String | 操作表名 |
| record_id | Integer | 操作记录ID |
| status | String | 同步状态 (synced/failed/conflict) |
| details | Text | 详细日志或错误信息 |
| conflict_id | Integer | 外键 -> data_conflicts.id |

**(8) 数据冲突表 (`data_conflicts`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| table_name | String | 发生冲突的表 |
| record_id | Integer | 发生冲突的记录ID |
| conflicting_data | JSON | 冲突现场快照 (存储各库数据的 JSON) |
| status | String | 状态 (unresolved/resolved) |
| resolved_at | DateTime | 解决时间 |

**(9) 系统设置表 (`system_settings`)**
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | Integer | 主键 |
| key | String | 配置键 (如 "overdue_days") |
| value | String | 配置值 |
| updated_at | DateTime | 更新时间 |

#### 3.2 异构同步机制 (`SyncManager`)
系统摒弃了传统的数据库底层复制（如 Binlog），自主实现了应用层同步引擎：
1.  **变更捕获**：当业务逻辑执行写操作（如 `create_book`）时，系统首先写入当前主选数据库。
2.  **方言转换**：`SyncManager` 捕获数据对象，利用 ORM 将其转换为适应其他数据库（PostgreSQL/SQL Server）的 SQL 方言。
3.  **异步分发**：通过 `asyncio` 创建后台任务，并行地将转换后的数据写入副本数据库，最大限度降低前端响应延迟。

#### 3.3 冲突检测与安全裁决
针对多节点写入可能导致的数据版本冲突，设计了闭环处理流程：
1.  **自动冻结**：同步失败时，系统自动在 `data_conflicts` 表生成记录。
2.  **安全通报**：系统生成一个包含 **专用 JWT Token** 的深链接（有效期 24 小时），并通过邮件发送给管理员。
3.  **人工裁决**：管理员点击链接进入前端 `ConflictResolution` 页面，经过**二次密码验证**后，可视化对比各库数据差异，手动选择保留版本。

---

### 4. 前端交互与访问控制设计

#### 4.1 核心页面交互
* **仪表盘 (`Dashboard.vue`)**：聚合展示图书总量、今日借阅数、活跃用户数等 KPI 指标。
* **同步监控 (`SyncStats.vue`)**：使用 ECharts 饼图和折线图，实时展示三个数据库节点的同步健康度与延迟趋势。
* **座位预约 (`SeatReservation.vue`)**：提供可视化的座位布局图，支持点击选座与即时状态更新。

#### 4.2 访问控制 (RBAC)
系统基于 JWT 标准实现无状态认证：
* **Admin (管理员)**：拥有全系统权限，包括数据修改、同步日志审计、冲突解决、系统参数配置。
* **Student (学生)**：仅拥有只读权限（查书、查记录）及受限的写权限（预约座位、提交借阅申请）。
* **路由守卫**：前端 Vue Router 通过 `meta.requiresAuth` 拦截未登录访问，后端通过 `Depends(get_current_active_user)` 依赖项进行接口级权限校验。

---

### 5. 性能优化与安全控制

#### 5.1 性能优化策略
* **数据库连接池**：在 `database.py` 中为 MySQL、PG 和 SQL Server 分别配置了 SQLAlchemy 连接池（Pool），显著减少高并发下的 TCP 握手开销。
* **非阻塞 I/O**：后端核心同步逻辑与邮件发送服务完全异步化，避免 I/O 密集型任务阻塞主线程，提高吞吐量。
* **静态资源构建**：前端使用 Vite 进行 Tree-shaking 和代码分割，大幅缩短首屏加载时间。

#### 5.2 安全防护措施
* **密码加密**：用户密码采用加盐哈希（Salted Hash）存储，防止彩虹表攻击。
* **最小权限原则**：冲突解决链接使用独立的 Token 类型 (`type="conflict_view"`)，仅能用于查看特定冲突，无法用于登录系统。
* **环境隔离**：数据库连接串、密钥等敏感信息通过 `.env` 文件和 Docker 环境变量注入，避免硬编码风险。

---

### 6. 技术栈与部署环境

* **开发语言**：Python 3.10+, JavaScript (ES6+)
* **后端框架**：FastAPI, SQLAlchemy, Pydantic, Emails
* **前端框架**：Vue 3, Vue Router, Axios, ECharts, Vite
* **数据库集群**：MySQL 8.0, PostgreSQL 13, SQL Server 2019
* **容器化引擎**：Docker, Docker Compose

---

### 7. 结语

本项目成功构建了一个具备高可用特性的现代化图书馆管理系统。通过自研 `SyncManager` 引擎，攻克了异构数据库应用层同步的技术难点；通过引入 JWT 深链接机制，解决了分布式系统中的数据冲突安全裁决问题。系统在功能完备性、架构合理性及代码规范性上均达到了工程级标准。