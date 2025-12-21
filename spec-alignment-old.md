# 规范与实现对齐说明

## 状态机与协商
- 规范：主单状态 preview/available/processing/rewrite/end/error，error 终止；典型流转：client preview→available，developer available→processing（接单）；processing→rewrite（配合 subform）；rewrite→processing（合并）；任意阶段协商失败可设 error；processing→end（见 Api and database.txt 2.2.6-2.2.7, models.md 660-707）。
- 现状：状态表在 [app/services/permissions.py](app/services/permissions.py#L107-L124) 固定 preview→available→processing→{rewrite,end,error}；rewrite 仅回 processing/error；end/error 无出边。状态接口在 [app/api/v1/forms.py](app/api/v1/forms.py#L66-L103) 仅放开 client 的 preview→available、任意设 error；developer 仅 available→processing 绑定接单人，未开放 processing→rewrite/end。
- 协商：规范要求一主一协；创建 subform 可将 mainform 置 rewrite；需“同意协商”合并（覆盖 mainform，删 subform，状态回 processing）或“取消/失败”（删 subform，通常回 processing 或设 error）；is_changed 仅 subform 可为 1。现状：在 [app/api/v1/forms.py](app/api/v1/forms.py) + [app/repositories/forms.py](app/repositories/forms.py) 仅支持创建 subform（并直接写 mainform.status=rewrite）与删除 subform（强制 mainform.status=processing），无合并/拒绝逻辑、无内容合并/恢复、无 is_changed 约束。
- 缺口：缺少 processing→rewrite、rewrite→processing/end/error 的角色校验；缺少合并/失败端点及数据操作；缺少 is_changed 限制与合并策略；error 虽终态但缺少“协商失败设 error”的明确入口。

## 角色、License、Admin
- 规范：注册需 license_key，激活 license 后写入角色，仅 client/developer 有效；admin 只在模型字段出现，业务未定义（见 Api and database.txt 0.1, models.md 60-75）。
- """✅ 已完成 License 与角色管理"""：
  - """✅ [auth.py#L28-L35](app/api/v1/auth.py#L28-L35) 注册时验证 license_key 并激活 license，失败则回滚用户创建"""
  - """✅ [auth.py#L56-L61](app/api/v1/auth.py#L56-L61) 登录时验证 license 有效性（validate_active），过期/失效则设置 user.is_active=0 并返回 403"""
  - """✅ [auth.py#L88-L113](app/api/v1/auth.py#L88-L113) POST /auth/reactivate 端点：吊销旧 license，激活新 license_key，更新用户角色"""
  - """✅ [licenses.py](app/repositories/licenses.py) 实现 activate、validate_active、activate_new_for_user 完整 license 生命周期管理"""
- 现状：权限代码仍保留 admin 兜底分支（如消息/文件/子表单编辑），但实际业务仅依赖 client/developer 角色。
- 剩余缺口：若严格按规范去除 admin 角色，需清理 [permissions.py](app/services/permissions.py) 中的 admin 判断分支（当前保留作为未来扩展可能）。

## Block status（urgent/normal）与邮件
- 定义（规范）：urgent 超 5 分钟无回复发送提醒邮件；normal 超 48 小时无回复发送提醒邮件（见 Api and database.txt 1.6 blocks）。
- 现状：字段存在并默认 normal，见 [app/models/block.py](app/models/block.py)；创建时写死 normal，见 [app/repositories/blocks.py](app/repositories/blocks.py#L1-L36)；消息接口不读不改 status，见 [app/api/v1/messages.py](app/api/v1/messages.py)。未有任何调度/邮件逻辑。
- 缺口：无设定/更新 block.status 的接口；无 last_message_at/提醒标记；无 5 分钟/48 小时定时检查与邮件发送。

## 列表与详情输出
- 规范：
  - GET /forms 返回 id/type/title/status/subform_id/created_at + 分页；client 仅自己的 mainform；developer available_only=true 看 available，默认看自己负责 processing/rewrite/end/error。
  - GET /form/{id} 需权限过滤，示例仅主单字段；业务描述期望前端能获取 subform、functions、nonfunctions、blocks（可一次或多次请求）。
- """✅ 列表实现与规范完全一致"""：
  - """✅ [forms.py#L23-L37](app/api/v1/forms.py#L23-L37) GET /forms 返回正确字段（id/type/title/status/subform_id/created_at）"""
  - """✅ [repositories/forms.py](app/repositories/forms.py) list_for_user 实现 client/developer 角色过滤与 available_only 逻辑"""
- """✅ 详情接口已实现权限过滤"""：
  - """✅ [forms.py#L39-L58](app/api/v1/forms.py#L39-L58) GET /form/{id} 返回表单基本字段，包含权限校验（client 仅自己，developer 仅接单/available）"""
- 剩余缺口：详情未聚合子表单与子项，需前端额外调用 GET /functions、GET /nonfunctions、GET /messages；若需要"一次返回全部"，需新增聚合端点（如 GET /form/{id}/full）。

## 消息、文件、审计
- 消息：
  - """✅ [messages.py#L50-L69](app/api/v1/messages.py#L50-L69) GET /messages 已返回附件列表，每条消息包含 files 数组（含 id/file_name/file_size）"""
  - """✅ [messages.py](app/api/v1/messages.py) 权限与块自动创建符合规范"""
  - 剩余：WebSocket 广播不包含附件信息（仅返回消息本身）
- 文件：
  - """✅ [files.py#L43-L58](app/api/v1/files.py#L43-L58) GET /file/{id} 已改为 FileResponse 流式返回，支持文件下载"""
  - """✅ [files.py#L32-L37](app/api/v1/files.py#L32-L37) >10MB 错误提示已改进："compress under 10MB or provide external link (Drive/GitHub)" """
  - """✅ 10MB 上传校验符合规范"""
  - 剩余：缺少 GET /file/{id}/preview 预览接口、1GB 外链兜底方案
- 审计/历史：
  - """✅ 已实现完整审计基础设施"""：
    - """✅ [alembic/versions/c94f7b4dbc99](alembic/versions/c94f7b4dbc99_add_audit_logs_table.py) 审计表迁移（audit_logs，包含 entity_type/action 枚举、JSON 字段、索引）"""
    - """✅ [models/audit_log.py](app/models/audit_log.py) AuditLog 模型定义"""
    - """✅ [services/audit.py](app/services/audit.py) 隔离审计服务，带 AUDIT_ENABLED 环境变量开关，失败不影响主流程（try-except）"""
    - """✅ 审计钩子覆盖所有 CRUD：[forms.py](app/api/v1/forms.py) 状态变更/更新/合并，[functions.py](app/api/v1/functions.py)/[nonfunctions.py](app/api/v1/nonfunctions.py) 创建/更新/删除，[messages.py](app/api/v1/messages.py) 删除，[files.py](app/api/v1/files.py) 删除"""
  - 剩余：无进度/权重字段支持（future enhancement）
- 邮件：整体未实现事件/超时邮件通知（见下方 Email & Block Reminder Plan）。

## 文件预览与大文件兜底计划 (NEW)
- 现状：上传校验 10MB；GET /file/{id} 仅返回 metadata/storage_path，不流式文件；无列表附件端点，无预览接口，无 >1GB 外链兜底。
- 理想：
  - GET /file/{id}/preview：若 file_size ≤ 1GB（阈值可配置）直接流式返回并设置 Content-Type；若超阈值返回 JSON 包含 external_url（可用 storage_path 或签名外链）。
  - GET /files?message_id=...：列出某消息附件，含 id/name/size/type/external_url（如有）。
  - 权限沿用现有文件访问规则（发送者/可访问该 block 的用户）。
- 实现思路：
  - 仓库层增加 file_size 阈值判断与 external_url 字段（可新增列或复用 storage_path 作为直链）。
  - 路由新增 /file/{id}/preview、/files 列表；小文件用 FileResponse，超大文件仅返回链接。
  - 文档更新返回格式，前端根据 external_url/流式响应选择展示/下载。

## Email & Block Reminder Plan (NEW)
- 新增字段：blocks.last_message_at（消息创建时更新，初始可回填 created_at）；blocks.reminder_sent（布尔标记防重复提醒，发送后置 true）。
- 新增接口/行为：
  - Block status 更新端点（normal/urgent 切换）；重置 reminder_sent=false 并可刷新 last_message_at。
  - 消息创建时同时写 block.last_message_at=now、reminder_sent=false。
- 调度策略：后台定时扫描 blocks。
  - urgent：last_message_at 超 5 分钟未更新则发送一次提醒，随后 reminder_sent=true。
  - normal：last_message_at 超 48 小时未更新则发送一次提醒，随后 reminder_sent=true。
- 邮件发送：Resend，env 读取 RESEND_API_KEY，From 使用 bridge-no-reply@icu.584743.xyz，收件人按 form 关联的 client/developer。
- 范围：新增内容不改动现有段落，便于团队识别新增计划。
