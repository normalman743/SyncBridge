# SyncBridge Backend

FastAPI backend for **SyncBridge** — a web-based platform for structured requirement submission, negotiation (subforms), real-time messaging (WebSocket), file upload/preview, email notifications (urgent/normal blocks), and role-based access control (client/developer). And automatic CI and CD.

## 📚 快速导航

> **新手入门**: 首先阅读 [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)  
> **项目进度**: 查看 [CODE_AND_DOCUMENTATION_ALIGNMENT.md](CODE_AND_DOCUMENTATION_ALIGNMENT.md)（92% 对齐）  
> **架构变更**: 查看 [LEGACY_TO_CURRENT_MIGRATION.md](LEGACY_TO_CURRENT_MIGRATION.md)（从单层到三层）  
> **规范检验**: 查看 [API_AND_DATABASE_ALIGNMENT.md](API_AND_DATABASE_ALIGNMENT.md)（92.6% 对齐）

## Python Version
Python 3.10.13

## Tech Stack
- FastAPI (REST + WebSocket)
- SQLAlchemy 2.0 + MySQL 8.0
- JWT Authentication + License Management
- Local file storage (`/storage/files/{file_id}/{filename}`)
- Resend API (email notifications)
- Alembic (database migrations)

## Key Features
- ✅ **Mainform + Subform negotiation** (双方同意机制, approval_flags)
- ✅ **Functions / NonFunctions** (需求项管理, is_changed 标记)
- ✅ **Block-based messaging** (按类型分类: general/function/nonfunction)
- ✅ **Real-time WebSocket** (消息实时推送 + 在线状态)
- ✅ **Email reminders** (urgent: 5分钟, normal: 48小时)
- ✅ **File management** (10MB 上传限制, 流式下载)
- ✅ **Audit logging** (完整操作审计)
- ✅ **License management** (用户激活、过期管理)
- ✅ **Role-based access** (client/developer 权限)

## 📊 项目对齐度评分

| 维度 | 评分 | 级别 |
|------|------|------|
| 功能完整性 | 95% | A |
| 代码质量 | 90% | A- |
| 安全合规 | 85% | B+ |
| 文档覆盖 | 95% | A |
| **整体** | **92%** | **A-** |

详见: [CODE_AND_DOCUMENTATION_ALIGNMENT.md](CODE_AND_DOCUMENTATION_ALIGNMENT.md)

## 🎯 快速开始

### 安装依赖
```bash
poetry install
```

### 数据库迁移
```bash
alembic upgrade head
```

### 启动服务
```bash
python -m uvicorn app.main:app --reload
```

## 📖 核心文档（4个总结性文档）

1. **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - 📌 建议首先阅读
   - 文档索引和快速导航
   - 使用场景快查表
   - 常见问题

2. **[LEGACY_TO_CURRENT_MIGRATION.md](LEGACY_TO_CURRENT_MIGRATION.md)** - 架构演变
   - Legacy 到现行的 17 个改动方向
   - 40+ 提交的完整说明
   - 从单层到三层的重构细节

3. **[API_AND_DATABASE_ALIGNMENT.md](API_AND_DATABASE_ALIGNMENT.md)** - 规范对齐
   - API 设计与规范的对齐分析
   - 数据模型完整性检查
   - 业务流程验证
   - 92.6% 对齐度评估

4. **[CODE_AND_DOCUMENTATION_ALIGNMENT.md](CODE_AND_DOCUMENTATION_ALIGNMENT.md)** - 整体评估
   - 代码与文档的综合对齐
   - 功能完整性矩阵
   - 缺口分析和优先级排序
   - 后续迭代计划和时间估算

## 📋 主要缺口（优先级排序）

### 🔴 高优先级（立即补充，2-3小时）
- [ ] is_changed 强制校验（subform 专属）
- [ ] 错误码完整定义

### 🟡 中优先级（1-2周，6-8小时）
- [ ] 文件预览接口 (`GET /file/{id}/preview`)
- [ ] 表单聚合接口 (`GET /form/{id}/full`)
- [ ] CORS 配置
- [ ] Rate Limiting

### 🟢 低优先级（1个月，25-35小时）
- [ ] 单元测试覆盖
- [ ] 审计日志查询 API
- [ ] 系统监控接口

详见 [CODE_AND_DOCUMENTATION_ALIGNMENT.md](CODE_AND_DOCUMENTATION_ALIGNMENT.md) 第 6-7 章

## 🔗 原始参考文档

- [Api and database.txt](Api and database.txt) - API 和数据库规范
- [System Design Document .txt](System Design Document .txt) - 系统架构设计
- [SRSExample-webapp.txt](SRSExample-webapp.txt) - 软件需求规范

## ✅ 实现检查清单

### 核心功能（100% 完成）
- [x] 用户认证与授权
- [x] 表单生命周期管理
- [x] Subform 协商流程（merge/reject）
- [x] 消息和文件管理
- [x] 邮件提醒调度（5分钟/48小时）
- [x] 审计日志系统
- [x] License 生命周期管理
- [x] WebSocket 实时通信

### 可选增强（40-70% 完成）
- [ ] 文件预览
- [ ] 大文件外链
- [ ] 表单聚合
- [ ] 单元测试
- [ ] 审计查询接口

---

**最后更新**: 2025-12-21  
**项目对齐度**: 92% (A-)  
**建议**: 从 DOCUMENTATION_INDEX.md 开始阅读
