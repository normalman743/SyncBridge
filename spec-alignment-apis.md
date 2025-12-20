# API-by-API 对规范差异审查

## Auth
- [app/api/v1/auth.py](app/api/v1/auth.py): 注册仅校验 email 并直接创建用户，再激活 license；未校验用户激活状态后写入 role 是否与 license 一致；缺少密码复杂度与重复注册的规范描述；未返回 license 信息。登录未检查 is_active，token 不包含 license 状态。
- 规范要求注册必须提供 `license_key`、校验未用/未过期后写入角色（Api and database.txt 2.1.1）；现有激活逻辑依赖 `license_repo.activate`，但未展示错误码细分（无 EXPIRED/REVOKED 区分）。

## Forms & Subforms
- 列表：实现与规范基本一致，client 仅看自己主单；developer available_only=true 看 available，默认看自己负责 processing/rewrite/end/error，见 [app/api/v1/forms.py](app/api/v1/forms.py#L1-L48) 与 [app/repositories/forms.py](app/repositories/forms.py#L1-L50)。未支持 admin 过滤（规范未要求）。
- 详情：仅返回单表字段，未聚合 subform/functions/nonfunctions/blocks（规范期望前端能看到 subform 及子项），见 [app/api/v1/forms.py](app/api/v1/forms.py#L13-L43)。
- 创建 mainform：仅 client，可创建即 status=preview，符合规范。
- 更新表单：mainform 限制 client 预览/可接单态、developer 处理/rewrite 态，符合示例；subform 仅 created_by（或 admin）可改；缺少 is_changed 约束。
- 删除表单：删除 subform 时直接将 mainform.status 设 processing，未区分“协商失败设 error”的场景，也未恢复 mainform 内容（规范要求回到原内容），见 [app/api/v1/forms.py](app/api/v1/forms.py#L49-L87)。
- 创建 subform：检查唯一且状态 in {available,processing,rewrite}，创建时直接将 mainform.status 改为 rewrite，见 [app/api/v1/forms.py](app/api/v1/forms.py#L89-L111)；缺少权限差异（规范允许任一方发起？现逻辑未限制）。
- 状态更新：
  - 状态表在 [app/services/permissions.py](app/services/permissions.py#L107-L124) 为 preview→available→processing→{rewrite,end,error}; rewrite→{processing,error}; end/error 终止。
  - 接口限制：client 仅 preview→available 或任意设 error；developer 仅 available→processing 并绑定 developer_id，未开放 processing→rewrite/end 或 rewrite→processing/end/error（规范要求处理→rewrite、处理→end、协商失败设 error）。见 [app/api/v1/forms.py](app/api/v1/forms.py#L113-L156)。
  - 缺少协商失败自动入口（subform 存在且拒绝）设 error。

## Functions / Nonfunctions
- CRUD 权限复用函数权限：mainform client 仅自有且 preview/available；developer 需被分配且不限状态；subform 仅 created_by。见 [app/api/v1/functions.py](app/api/v1/functions.py) 与 [app/api/v1/nonfunctions.py](app/api/v1/nonfunctions.py).
- 不对齐：
  - is_changed 业务未限制仅 subform 可设 1；无校验 mainform 必为 0。
  - 状态字段未限制编辑态（规范示例使用 status 可选，需与表单状态机联动）。
  - 无权重/进度字段（规范有权重/进度在 SRS，但简化版未含）。

## Messages / Blocks / WebSocket
- 消息列表/创建/更新/删除符合基本流程，自动创建 block。见 [app/api/v1/messages.py](app/api/v1/messages.py).
- Block status（urgent/normal）存在字段但：
  - 创建时写死 normal，见 [app/repositories/blocks.py](app/repositories/blocks.py#L1-L34)。
  - 无 API 设为 urgent/normal；无 last_message_at/提醒标记；无 5 分钟/48 小时邮件调度（规范 1.6、邮件逻辑要求）。
- WebSocket：仅校验 token、表单访问权限，未按 block status 触发任何通知，见 [app/api/v1/ws.py](app/api/v1/ws.py).
- 消息返回不含附件列表，未区分 subform 上下文；缺少分页排序保障（使用 message_repo.list_messages 需确认是按时间倒序）。

## Files
- 上传/下载/删除符合 10MB 限制；权限基于消息块访问，见 [app/api/v1/files.py](app/api/v1/files.py)。
- 缺失：文件预览接口、1GB 大文件外链兜底（规范扩展要求）；下载接口仅返回元数据，未提供实际文件流/URL。

## License / Admin
- license 表存在并在注册时调用 activate，但未覆盖登录/鉴权时对 license 状态（expired/revoked）的检查；未在 token 或权限中使用。
- admin 角色在 permissions 中保留兜底，但规范业务未定义 admin；若遵循规范，应移除 admin 分支并以 license 决定角色。

## 统一响应/错误码
- 大部分接口返回 success/error 模板，但错误码细分不足：
  - 状态机冲突统一用 CONFLICT，但未区分资源不存在/权限不足/状态非法的规范枚举；
  - auth 登录/注册未区分 license 过期/撤销等。

## 需要补充的主要缺口
1) 状态机：开放并校验 processing→rewrite/end，rewrite→processing/end/error；处理协商失败→error 入口；完善角色条件。
2) 子表单协商：新增合并/拒绝端点，覆盖 mainform 内容、删除 subform、恢复/设定状态；限制 is_changed 仅 subform 可为 1。
3) Block 邮件：提供设置 urgent/normal 的接口，记录最后消息时间，添加调度器发送 5 分钟/48 小时提醒。
4) 详情聚合：可选新增聚合接口返回 mainform + subform + functions/nonfunctions + blocks，减少前端多请求。
5) Files：增加预览/大文件兜底。
6) License 校验：登录时校验 license 状态，权限依赖 license.role；清理 admin 分支或定义其权限。
7) 错误码：统一与规范列出的 UNAUTHORIZED/FORBIDDEN/NOT_FOUND/VALIDATION_ERROR/CONFLICT。