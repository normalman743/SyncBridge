# Legacy 与现实现有差异点

对比范围：`legacy/app` 下的 permissions.py、routers/forms.py、routers/messages.py 等与现行 `app/api/v1`、`app/services`、`app/repositories` 实现。

## 结论
- **未发现 legacy 中有已完成而现实现缺失的业务功能。** 状态机、子表单、消息、文件权限等核心逻辑保持一致，legacy 也没有实现合并子表单、状态机扩展、block 邮件、文件预览等能力。

## 细节对比
- 状态机：legacy `validate_status_transition` 与现行一致（preview→available→processing→{rewrite,end,error}；rewrite→{processing,error}）。未提供 processing→rewrite/end 的开放入口，也无协商失败自动设 error。
- 表单状态接口：legacy 仅允许 client preview→available 或设 error，developer available→processing 绑定接单人；与现行相同，未实现合并/拒绝协商。
- 子表单：legacy 仅支持创建/删除，删除时 mainform.status 设 processing，不恢复内容，也无 merge/reject 端点；与现行相同。
- Block status 与邮件：legacy 亦未使用 urgent/normal，也无邮件调度。
- 消息：legacy 用 `asyncio.create_task` 异步广播，现行用 `await`；功能等价。
- 文件/函数/非功：权限与路由形态相同，无额外特性。
- License/Admin：legacy 也保留 admin 分支，license 激活流程同样未覆盖登录时状态校验。

## 额外说明
- 若需查找现行缺失的功能，应参考规范差异文档 [spec-alignment.md](spec-alignment.md) 与 [spec-alignment-apis.md](spec-alignment-apis.md)；legacy 不提供额外可迁移的实现。

## 现行代码相对 legacy 的改进

### 1. 架构与模块化 (Commits: 17105c9, 712937e, 500db33, 97d897b, 3ffbb06, 9c29a79)
- **分层重构**：将单文件 `crud.py/models.py` 拆分为 `repositories/`、`services/`、`models/` 目录，职责清晰化（数据访问、业务逻辑、实体定义分离）。
- **API v1 路由隔离**：统一 `/api/v1/*` 路由前缀，便于版本控制与未来扩展。
- **统一 utils**：提取 `responses.py`（success/error 包装）、`security.py`（JWT 编解码）为独立工具模块。

### 2. 权限与安全强化 (Commits: 650157a, daf6933, 16dc1d7, 6433482)
- **未知角色 403**：`get_current_user` 与 `require_role` 对 `role=None` 或未知角色直接拒绝（commit 650157a），阻断未激活用户访问路径，legacy 中 admin 逻辑宽松允许通过。
- **JWT 强化**（commit 16dc1d7）：
  - 拒绝默认 `SECRET_KEY="your-secret-key-here"`，启动时抛出错误强制配置。
  - 捕获明确 JWT 异常（`JWTError`、`ExpiredSignatureError`、`InvalidTokenError`），替代 legacy 通用 `Exception` 捕获。
  - 要求 token payload 必须包含 `sub`，legacy 未强制检查。
- **License 激活流程**：注册时用户默认 `is_active=0`，仅在 license 激活成功后设为 1（commit 6433482），legacy 未区分激活状态。

### 3. 数据校验与字段控制 (Commits: 63a946f, a4a4510, daf6933)
- **Update Schema 白名单**（commit 63a946f）：
  - 新增 `FormUpdate`、`FunctionUpdate`、`NonFunctionUpdate`、`MessageUpdate` 专用模型，使用 `extra="forbid"` 阻止非法字段。
  - 接口对 `exclude_unset=True` 后空变更返回 400，防止"误传空 body 导致字段清空"。
  - Legacy 直接接受裸 `dict` 并全量更新，易误改敏感字段（如 `developer_id`、`user_id`）。
- **Schema 强化**（commit 6433482）：
  - 新增 `NonFunctionIn`/`NonFunctionOut` 独立模型（legacy 复用 Function schema）。
  - Form/Function/NonFunction 创建时强制必填字段，避免部分初始化。

### 4. 消息与实时通信改进 (Commits: 650157a, daf6933)
- **异步广播改为 await**：从 `asyncio.create_task(manager.broadcast(...))` 改为直接 `await manager.broadcast(...)`，避免协程未消费导致的泄漏/丢失警告。
- **消息排序**：`list_messages` 按 `created_at DESC` 降序（最新在前），legacy 为升序，不利于消息流展示。
- **WebSocket presence**：新增 join/leave 推送（见 [app/api/v1/ws.py](app/api/v1/ws.py)），前端可显示在线状态，legacy 未实现。

### 5. 数据库一致性 (Commit: f4bde4b)
- **Server 默认值对齐**（Alembic 迁移 ab4d1b5c2bd7）：
  - 为 `users.is_active` 设置 `server_default="0"`。
  - 为 `blocks.status` 设置 `server_default="normal"`。
  - 为 `blocks.type` 设置 `server_default="general"`。
  - 解决"模型层 `default` 与数据库无 `server_default`"不一致导致的插入空值问题，legacy 未修复此问题。

### 6. 业务逻辑优化 (Commits: 6433482)
- **Developer 列表过滤**：默认不展示 `available` 主单（需要 `available_only=true` 显式拉取），避免混入未接单表单；legacy 查询逻辑未严格区分。
- **注册响应统一**：返回 `access_token` + `role`，减少前端再次请求 `/me`；legacy 需要两步获取完整信息。

### 7. 代码质量提升
- **统一 `get_current_user`**：auth 路由复用 `services.permissions.get_current_user`，避免重复实现（commit daf6933）。
- **去除冗余依赖**：清理 potential_problem.txt 记录的数据模型不一致问题（commit 6433482）。
- **环境模板完善**：`.env.template` 新增 `SECRET_KEY` 配置说明与强制要求（commit 16dc1d7）。

### 改进总结（按提交时间线）
| Commit | 改进点 | 影响 |
|--------|--------|------|
| d216fae ~ 17105c9 | 模块化重构 | 可维护性↑ |
| a444d85 | Models 规范化、索引优化、迁移对齐 | 数据模型↑ |
| 3ffbb06 | 新增 WebSocket presence 推送 | 实时性↑ |
| 6433482 | Schema 对齐、License 激活、消息排序 | 数据完整性↑ |
| daf6933 | 异步消息、未知角色 403、Update 白名单 | 安全性↑ |
| 650157a | 异步 await、权限严管 | 稳定性↑ |
| 63a946f | Update Schema extra=forbid | 防御性↑ |
| 16dc1d7 | JWT 强制配置、明确异常 | 安全性↑ |
| f4bde4b | Server 默认值迁移 | DB 一致性↑ |

## 代码对比验证（Legacy vs 现行）

### ✅ 已验证改进点代码证据

1. **未知角色 403**（650157a）
   - Legacy: `permissions.py` 对非 client/developer 直接 `return`（允许通过）
   - 现行: 改为 `raise HTTPException(403, "Forbidden")`
   - 位置: `assert_can_view_form`, `assert_can_update_mainform`, `assert_can_access_block`

2. **异步消息 await**（650157a）
   - Legacy: `asyncio.create_task(manager.broadcast(...))`（fire-and-forget）
   - 现行: `async def post_message` + `await manager.broadcast(...)`
   - 位置: `app/api/v1/messages.py` POST/PUT/DELETE 路由

3. **JWT 强化**（16dc1d7）
   - Legacy: `SECRET_KEY = os.getenv("SECRET_KEY")` 无校验，通用 `except JWTError`
   - 现行: 拒绝 `"secret"` 默认值，捕获 `ExpiredSignatureError`，要求 `sub` 必填
   - 位置: `app/utils/security.py`

4. **Update Schema 白名单**（63a946f）
   - Legacy: 裸 `dict` 更新，无字段限制
   - 现行: `FormUpdate`/`FunctionUpdate` 等独立模型，`extra="forbid"`，空变更返回 400
   - 位置: `app/schemas/forms.py`, `app/api/v1/forms.py`

5. **用户激活流程**（6433482）
   - Legacy: `create_user` 时 `is_active=True`
   - 现行: `is_active=0`，仅在 `license.activate` 成功后设为 1
   - 位置: `app/repositories/users.py`, `app/repositories/licenses.py`

6. **Developer 列表过滤**（6433482）
   - Legacy: `or_(Form.developer_id == user.id, Form.status == "available")`（混入未接单）
   - 现行: 默认仅 `developer_id == user.id AND status in {processing,rewrite,end,error}`
   - 位置: `app/repositories/forms.py`

7. **消息排序**（6433482）
   - Legacy: `.order_by(Message.created_at)` 升序
   - 现行: `.order_by(Message.created_at.desc())` 降序（最新在前）
   - 位置: `app/repositories/messages.py`

8. **WebSocket presence**（3ffbb06）
   - Legacy: 无 presence 推送
   - 现行: connect 后广播 `{type:"presence", action:"join"}`，disconnect 广播 `action:"leave"`
   - 位置: `app/api/v1/ws.py`

9. **Server 默认值**（f4bde4b）
   - Legacy: 迁移仅改类型，无 `server_default`
   - 现行: Alembic 迁移 ab4d1b5c2bd7 为 `users.is_active`, `blocks.status`, `blocks.type` 设置 `server_default`
   - 位置: `alembic/versions/ab4d1b5c2bd7_.py`

10. **Models 规范化**（a444d85）
    - 新增 `models.md` 完整规范文档
    - 统一索引（`ix_forms_user_id`, `ix_blocks_form_id` 等）
    - 字段类型对齐（ENUM、nullable、server_default）
    - 位置: `app/models/*.py`, 迁移 10308d0fa5bb

### 🔍 未发现的新改进（扫描全部提交后）
- 无额外功能性改进被遗漏；所有核心改进已列入文档。