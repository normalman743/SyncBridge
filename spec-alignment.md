# 规范与实现对齐说明

## 状态机与协商
- 规范：主单状态 preview/available/processing/rewrite/end/error，error 终止；典型流转：client preview→available，developer available→processing（接单）；processing→rewrite（配合 subform）；rewrite→processing（合并）；任意阶段协商失败可设 error；processing→end（见 Api and database.txt 2.2.6-2.2.7, models.md 660-707）。
- 现状：状态表在 [app/services/permissions.py](app/services/permissions.py#L107-L124) 固定 preview→available→processing→{rewrite,end,error}；rewrite 仅回 processing/error；end/error 无出边。状态接口在 [app/api/v1/forms.py](app/api/v1/forms.py#L66-L103) 仅放开 client 的 preview→available、任意设 error；developer 仅 available→processing 绑定接单人，未开放 processing→rewrite/end。
- 协商：规范要求一主一协；创建 subform 可将 mainform 置 rewrite；需“同意协商”合并（覆盖 mainform，删 subform，状态回 processing）或“取消/失败”（删 subform，通常回 processing 或设 error）；is_changed 仅 subform 可为 1。现状：在 [app/api/v1/forms.py](app/api/v1/forms.py) + [app/repositories/forms.py](app/repositories/forms.py) 仅支持创建 subform（并直接写 mainform.status=rewrite）与删除 subform（强制 mainform.status=processing），无合并/拒绝逻辑、无内容合并/恢复、无 is_changed 约束。
- 缺口：缺少 processing→rewrite、rewrite→processing/end/error 的角色校验；缺少合并/失败端点及数据操作；缺少 is_changed 限制与合并策略；error 虽终态但缺少“协商失败设 error”的明确入口。

## 角色、License、Admin
- 规范：注册需 license_key，激活 license 后写入角色，仅 client/developer 有效；admin 只在模型字段出现，业务未定义（见 Api and database.txt 0.1, models.md 60-75）。
- 现状：注册/登录未校验 license 或写入角色；权限代码仍保留 admin 兜底（如消息/文件/子表单编辑）。
- 缺口：接入 license 表校验与角色写入；若按规范去掉 admin，应清理 permissions 中 admin 分支并只依赖 license 决定角色。

## Block status（urgent/normal）与邮件
- 定义（规范）：urgent 超 5 分钟无回复发送提醒邮件；normal 超 48 小时无回复发送提醒邮件（见 Api and database.txt 1.6 blocks）。
- 现状：字段存在并默认 normal，见 [app/models/block.py](app/models/block.py)；创建时写死 normal，见 [app/repositories/blocks.py](app/repositories/blocks.py#L1-L36)；消息接口不读不改 status，见 [app/api/v1/messages.py](app/api/v1/messages.py)。未有任何调度/邮件逻辑。
- 缺口：无设定/更新 block.status 的接口；无 last_message_at/提醒标记；无 5 分钟/48 小时定时检查与邮件发送。

## 列表与详情输出
- 规范：
  - GET /forms 返回 id/type/title/status/subform_id/created_at + 分页；client 仅自己的 mainform；developer available_only=true 看 available，默认看自己负责 processing/rewrite/end/error。
  - GET /form/{id} 需权限过滤，示例仅主单字段；业务描述期望前端能获取 subform、functions、nonfunctions、blocks（可一次或多次请求）。
- 现状：列表实现与规范一致（见 [app/api/v1/forms.py](app/api/v1/forms.py) 与 [app/repositories/forms.py](app/repositories/forms.py)）；详情仅返回表单基本字段，未聚合子表单与子项，需要额外调用各列表接口。
- 缺口：若前端需要“一次返回全部”，需新增聚合查询/端点。

## 消息、文件、其他缺失
- 消息：权限与块自动创建符合；缺少 admin 去除后需要同步权限调整；未携带附件列表返回。
- 文件：10MB 校验符合规范；缺少预览接口、1GB 外链兜底方案。
- 审计/历史：无状态变更历史或进度/权重字段支持。
- 邮件：整体未实现事件/超时邮件通知。

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
