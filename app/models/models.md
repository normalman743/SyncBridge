Api and Database

0. 系统整体介绍（给前后端看的）
0.1 角色 & License
系统有两类业务角色：


client：提交需求的用户


developer：接单并实现需求的开发者


用户注册时必须提供 license_key，license 中写明角色（client 或 developer），激活后才确定用户角色。


后续所有 API 都依赖角色进行权限控制（RBAC）。


0.2 核心数据对象
Form（需求表单）


type = mainform：主表单，client 原始需求 + 已达成一致版本。


type = subform：协商版本，用于 rewrite / 谈判。


一个 mainform 最多有一个 subform（mainform.subform_id 指向 subform）。


form 有状态：preview / available / processing / rewrite / end / error。


Function / NonFunction


挂在某个 form 上（一对多）。


subform 有自己独立的 functions / nonfunctions。


# 数据库模型定义（最优版）

本文件定义 SyncBridge 的数据库模型（MySQL 语义），与最终版 API 规范对齐，并标注优化点与原因。业务层（服务/路由）需配合实施权限与状态机校验。

## 概览
- 一致性: 字段集合、可空性、枚举取值与 API 对齐；时间戳统一使用 `server_default=now` 与 `onupdate=now`。
- 默认值: 更贴业务流（如 `users.is_active=0`，`blocks.status/type` 默认普通值）。
- 约束: `forms.subform_id` 唯一约束，保障“一主一协”；其余业务约束在服务层校验。
- 索引: 为高频外键列建索引（`user_id/developer_id/form_id/...`），提高分页/列表性能。

## 全局约定
- 时间戳: DATETIME（无时区）。推荐后端统一写入 UTC，序列化时转换。
- 枚举: 与 API 文档保持一致，保证合法状态流转。
- 外键行为: 级联删除由服务层控制；ORM 层通过关系与 `cascade` 管理。

## Users（用户）
- 表: `users`（见 [app/models/user.py](app/models/user.py)）
- 字段:
  - id: INT PK 自增
  - email: VARCHAR(128) NOT NULL UNIQUE
  - password_hash: VARCHAR(256) NOT NULL
  - display_name: VARCHAR(32) NOT NULL
  - role: ENUM('client','developer','admin') NULL
  - is_active: TINYINT NOT NULL 默认 0
  - created_at / updated_at: DATETIME（`server_default=now`, `onupdate=now`）
- 索引:
  - email 唯一索引（可选额外普通索引 `ix_users_email`）
- 优化与原因:
  - 默认未激活（0）贴合“注册→激活 license”的业务流；避免存储与业务不一致。
  - 使用 TINYINT（ORM SmallInteger）表达布尔值，兼容 MySQL。

## Licenses（许可证）
- 表: `licenses`（见 [app/models/license.py](app/models/license.py)）
- 字段:
  - id: INT PK
  - license_key: VARCHAR(128) NOT NULL UNIQUE
  - role: ENUM('client','developer') NOT NULL
  - status: ENUM('unused','active','expired','revoked') NOT NULL 默认 'unused'
  - user_id: INT FK(users.id) NULL
  - activated_at / expires_at: DATETIME NULL
- 索引:
  - `ix_licenses_user_id`（按用户查询绑定许可更快）
- 优化与原因:
  - 明确默认状态为 `unused`，避免脏数据。
  - 为绑定用户场景优化查询性能。

## Forms（表单：mainform/subform 共用）
- 表: `forms`（见 [app/models/form.py](app/models/form.py)）
- 字段:
  - id: INT PK
  - type: ENUM('mainform','subform') NOT NULL
  - user_id: INT FK(users.id) NOT NULL（需求提出者）
  - developer_id: INT FK(users.id) NULL（接单者）
  - created_by: INT FK(users.id) NOT NULL（创建人/发起方）
  - title: VARCHAR(128) NOT NULL
  - message: TEXT NOT NULL
  - budget: VARCHAR(64) NOT NULL
  - expected_time: VARCHAR(64) NOT NULL
  - status: ENUM('preview','available','processing','rewrite','end','error') NOT NULL 默认 'preview'
  - subform_id: INT FK(forms.id) NULL（mainform 指向当前 subform）
  - created_at / updated_at: DATETIME
- 索引与约束:
  - `ix_forms_user_id`，`ix_forms_developer_id`
  - `uq_forms_subform_id`（允许多个 NULL；确保“一主一协”）
- 优化与原因:
  - 为列表/看板视图的过滤列建索引，显著降低扫描。
  - 唯一约束防止同一 subform 被多个 mainform 共享。

## Functions（功能需求）
- 表: `functions`（见 [app/models/function.py](app/models/function.py)）
- 字段:
  - id: INT PK
  - form_id: INT FK(forms.id) NOT NULL
  - name: VARCHAR(128) NOT NULL
  - choice: ENUM('lightweight','commercial','enterprise') NOT NULL
  - description: TEXT NOT NULL
  - status: ENUM('preview','available','processing','rewrite','end','error') NOT NULL 默认 'preview'
  - is_changed: TINYINT NOT NULL 默认 0
  - created_at / updated_at: DATETIME
- 索引:
  - `ix_functions_form_id`
- 优化与原因:
  - `is_changed` 用 TINYINT 与 MySQL 规范一致；服务层校验“仅 subform 可为 1”。
  - 按 form 分组检索更高效。

## NonFunctions（非功能需求）
- 表: `nonfunctions`（见 [app/models/nonfunction.py](app/models/nonfunction.py)）
- 字段:
  - 与 `functions` 同构，将 `choice` 改为 `level`（枚举值一致）
- 索引与优化:
  - `ix_nonfunctions_form_id`；其余与 `functions` 一致。

## Blocks（消息块，内部结构）
- 表: `blocks`（见 [app/models/block.py](app/models/block.py)）
- 字段:
  - id: INT PK
  - form_id: INT FK(forms.id) NOT NULL
  - status: ENUM('urgent','normal') NOT NULL 默认 'normal'
  - type: ENUM('general','function','nonfunction') NOT NULL 默认 'general'
  - target_id: INT NULL（general 为 NULL；其他类型为 function_id/nonfunction_id）
  - created_at: DATETIME
- 索引:
  - `ix_blocks_form_id`
- 优化与原因:
  - 典型默认值减少必填负担。
  - `type ↔ target_id` 的一致性在服务层校验，避免复杂触发器。

## Messages（消息）
- 表: `messages`（见 [app/models/message.py](app/models/message.py)）
- 字段:
  - id: INT PK
  - block_id: INT FK(blocks.id) NOT NULL
  - user_id: INT FK(users.id) NOT NULL
  - text_content: TEXT NOT NULL
  - created_at / updated_at: DATETIME
- 索引:
  - `ix_messages_block_id`，`ix_messages_user_id`
- 优化与原因:
  - 支撑按块与发送者过滤的分页性能。

## Files（附件）
- 表: `files`（见 [app/models/file.py](app/models/file.py)）
- 字段:
  - id: INT PK
  - message_id: INT FK(messages.id) NOT NULL
  - file_name: VARCHAR(128) NOT NULL
  - file_type: VARCHAR(32) NOT NULL
  - file_size: INT NOT NULL（业务层校验 ≤ 10MB）
  - storage_path: TEXT NOT NULL
  - created_at: DATETIME
- 索引:
  - `ix_files_message_id`
- 优化与原因:
  - 访问链路清晰，按消息检索附件更快；大小限制由上传逻辑校验。

## 接口层 Schema 映射（与 Pydantic）
- Auth:
  - RegisterIn/LoginIn/AuthMeOut 与 `users`/`licenses` 字段一致；`role` 为 NULL 直到 license 激活。
- Forms:
  - FormCreate → 写入 `forms` 业务字段；FormOut 映射 `forms` 的详情（`status/type/subform_id/...`）。
- Functions/NonFunctions:
  - FunctionIn/Out 与 `functions` 对齐；`is_changed` Schema 为布尔，DB 为 TINYINT，服务层做转换。
  - NonFunction 架构同构，字段名为 `level`。
- Messages:
  - MessageIn 通过 `form_id + function_id/nonfunction_id` 定位/创建 `blocks`，再写入 `messages`；MessageOut 映射消息详情。
- Files:
  - FileOut 映射 `files` 元数据；大小限制在业务层执行。

## 业务层强约束（不在 DB 层）
- RBAC：按 `client/developer` 权限控制资源访问与操作。
- Subform：仅 `created_by` 可改/删；mainform 仅允许一个 subform（DB 唯一约束确保指向唯一）。
- is_changed：仅在 `type=subform` 的表单上允许为 1；mainform 必为 0。
- 状态机：`preview → available → processing → rewrite/end/error` 的合法流转校验。
- 消息块：API 层只暴露 `form_id + function_id/nonfunction_id`；后端内部映射/创建 `blocks` 并分页 `messages`。
created_at
DATETIME


updated_at
DATETIME



1.4 functions
字段
类型
说明
id
INT PK


form_id
INT FK(forms.id)
所属 form（可以是 mainform 或 subform）
name
VARCHAR(128)
功能名
choice
ENUM('lightweight','commercial','enterprise')
等级
description
TEXT
描述
status
ENUM('preview','available','processing','rewrite','end','error')
状态
is_changed
TINYINT
0=mainform 或未改动，1=subform 修改过
created_at
DATETIME


updated_at
DATETIME



1.5 nonfunctions
字段
类型
说明
id
INT PK


form_id
INT FK(forms.id)
所属 form
name
VARCHAR(128)
非功能需求名
level
ENUM('lightweight','commercial','enterprise')
等级
description
TEXT
描述
status
ENUM('preview','available','processing','rewrite','end','error')
状态
is_changed
TINYINT
同 functions
created_at
DATETIME


updated_at
DATETIME



1.6 blocks（消息块，内部结构，API 不直接暴露）
字段
类型
说明
id
INT PK


form_id
INT FK(forms.id)
对应的 form 或 subform
Status
ENUM(‘urgent’,’normal’)
控制发送邮件
type
ENUM('general','function','nonfunction')
块类型
target_id
INT NULL
function_id / nonfunction_id，general 时为 NULL
created_at
DATETIME




1.7 messages
字段
类型
说明
id
INT PK


block_id
INT FK(blocks.id)
所属块
user_id
INT FK(users.id)
发送者
text_content
TEXT
文本内容
created_at
DATETIME


updated_at
DATETIME



1.8 files
字段
类型
说明
id
INT PK


message_id
INT FK(messages.id)
所属消息
file_name
VARCHAR(128)
文件名
file_type
VARCHAR(32)
MIME 或扩展名
file_size
INT
字节数（10MB 校验在业务层）
storage_path
TEXT
存储路径/URL
created_at
DATETIME





2. API 设计（对齐数据库 & 区分 client / developer）
所有返回统一格式：
成功
{
  "status": "success",
  "message": "OK",
  "data": { ... }
}

失败
{
  "status": "error",
  "message": "Invalid status transition",
  "code": "CONFLICT"
}

常用 code：
UNAUTHORIZED：未登录 / token 无效


FORBIDDEN：角色 / 权限不足


NOT_FOUND：资源不存在或无权限看


VALIDATION_ERROR：参数不合法


CONFLICT：状态流转不合法、已存在 subform 等


INTERNAL_ERROR：服务器错误



2.1 Auth
2.1.1 POST /api/v1/auth/register
前置条件：未登录


角色：无差异（所有人都一样）


Body
{
  "email": "user@example.com",
  "password": "123456",
  "display_name": "Steven",
  "license_key": "ABC-123-XYZ"
}

成功
{
  "status": "success",
  "message": "User registered and activated",
  "data": {
    "user_id": 12,
    "role": "client"
  }
}

失败
邮箱存在：CONFLICT


license 无效/已用/过期：FORBIDDEN



2.1.2 POST /api/v1/auth/login
Body
{
  "email": "user@example.com",
  "password": "123456"
}

成功
{
  "status": "success",
  "message": "Login success",
  "data": {
    "access_token": "xxx.yyy.zzz",
    "role": "client"
  }
}

失败
账号或密码错误：UNAUTHORIZED



2.1.3 GET /api/v1/auth/me
Headers
Authorization: Bearer <token>


成功
{
  "status": "success",
  "message": "OK",
  "data": {
    "user_id": 12,
    "email": "user@example.com",
    "display_name": "Steven",
    "role": "developer"
  }
}

失败
token 无效/过期：UNAUTHORIZED



2.2 Forms & Subforms
2.2.1 GET /api/v1/forms
Query
page（默认 1）


page_size（默认 20）


available_only（默认 false，developer 专用）


前置条件
必须登录


行为差异
client：


只看到：user_id = 自己 且 type='mainform' 的 forms


developer：


available_only = true → 返回所有 status='available' 的 mainform（抢单列表）


available_only = false → 返回自己作为 developer_id 的 mainform，状态 ∈ {processing,rewrite,end,error}


成功
{
  "status": "success",
  "message": "OK",
  "data": {
    "forms": [
      {
        "id": 1,
        "type": "mainform",
        "title": "Online Shop",
        "status": "processing",
        "subform_id": 10,
        "created_at": "..."
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 5
  }
}


2.2.2 GET /api/v1/form/{id}
前置条件
client：只能访问自己 user_id 的 mainform 和其 subform


developer：只能访问：


自己作为 developer_id 的 mainform / subform


或 status='available' 的 mainform（可接单）


成功 data 示例
{
  "status": "success",
  "message": "OK",
  "data": {
    "id": 1,
    "type": "mainform",
    "title": "...",
    "message": "...",
    "budget": "...",
    "expected_time": "...",
    "status": "processing",
    "user_id": 3,
    "developer_id": 8,
    "subform_id": 10,
    "created_at": "...",
    "updated_at": "..."
  }
}

失败
无权限访问该 form：FORBIDDEN


不存在：NOT_FOUND



2.2.3 POST /api/v1/form （创建 mainform）
前置条件
只有 client 可以创建 mainform


Body
{
  "title": "New Project",
  "message": "I need a payment system...",
  "budget": "5000 USD",
  "expected_time": "2 months"
}

行为
创建 type='mainform'


status='preview'


user_id = 当前 client


created_by = 当前 client


成功
{
  "status": "success",
  "message": "Form created",
  "data": {
    "form_id": 1
  }
}


2.2.4 PUT /api/v1/form/{id} （修改表单内容）
前置条件 + 差异
mainform：


client：只能修改自己的 mainform，且 status ∈ {preview, available}


developer：只能在自己负责且 status ∈ {processing, rewrite} 时修改业务字段


subform：


只有 created_by（发起方）可以修改（C4）


Body（任意字段可选）
{
  "title": "Updated title",
  "message": "Updated requirement",
  "budget": "6000 USD",
  "expected_time": "3 months"
}

成功
{"status":"success","message":"Form updated","data":null}

失败
无权限：FORBIDDEN


状态不允许修改：CONFLICT



2.2.5 DELETE /api/v1/form/{id}
规则
删除 mainform：


仅 client，且 status='preview' 


删除 subform：


仅 created_by，删除后：


mainform 恢复原内容


mainform.subform_id = NULL


mainform.status 通常设为 processing（错误逻辑留扩展）


成功
{"status":"success","message":"Form deleted","data":null}


2.2.6 POST /api/v1/form/{id}/subform （创建 subform）
前置条件
{id} 必须是 mainform


mainform.subform_id 为空（一个 mainform 只允许一个 subform）


status ∈ {available, processing, rewrite}（具体可在后端限制）


Body
{
  "title": "Negotiated Proposal",
  "message": "Updated requirements ...",
  "budget": "5500 USD",
  "expected_time": "2.5 months"
}

行为
创建 type='subform' 的 form，created_by = 当前用户


更新 mainform 的 subform_id 指向新 subform


同时（可选）把 mainform.status 改为 rewrite


成功
{
  "status": "success",
  "message": "Subform created",
  "data": {
    "subform_id": 10
  }
}

失败
已有 subform：CONFLICT


无权限：FORBIDDEN



2.2.7 PUT /api/v1/form/{id}/status （状态变更）
Body
{
  "status": "processing"
}

部分状态规则（示例）
client：


preview → available


存在 subform 且协商失败 → 可以设 status='error'


developer：


available → processing（接单）


processing → rewrite（可配合创建 subform）


processing → end


任意阶段根据协商结果设为 error


成功
{"status":"success","message":"Status updated","data":null}

失败
不合法状态流转：CONFLICT


无权限：FORBIDDEN


注：具体状态机实现可以在后端单独定义函数进行校验。

2.3 Functions
2.3.1 GET /api/v1/functions
Query
form_id（必填）


行为
client：只能看 form.user_id=自己 的 functions


developer：只能看：


自己作为 developer 的 form


或 status='available' 时的 mainform（若允许）


成功
{
  "status": "success",
  "message": "OK",
  "data": {
    "functions": [
      {
        "id": 1,
        "form_id": 1,
        "name": "Login",
        "choice": "commercial",
        "description": "...",
        "status": "processing",
        "is_changed": 0
      }
    ]
  }
}


2.3.2 POST /api/v1/function
Body
{
  "form_id": 1,
  "name": "Login",
  "choice": "commercial",
  "description": "User can login with email",
  "status": "available",
  "is_changed": 1
}

权限
mainform：


client & developer 都可添加（根据你们业务可再细化）


subform：


只有 subform 的 created_by 可以添加（C4）


成功
{
  "status": "success",
  "message": "Function created",
  "data": {
    "id": 1
  }
}

PUT / DELETE 类似（根据 id 修改 / 删除），失败时返回 FORBIDDEN 或 CONFLICT。

2.4 Nonfunctions
与 functions 完全同构，只是字段名不同。
2.4.1 GET /api/v1/nonfunctions?form_id=...
同上。
2.4.2 POST /api/v1/nonfunction
{
  "form_id": 1,
  "name": "Security",
  "level": "enterprise",
  "description": "HTTPS, RBAC, logging",
  "status": "available",
  "is_changed": 1
}

返回 / 权限 同 functions。

2.5 Messages
2.5.1 GET /api/v1/messages
Query
form_id（必填）


function_id（可选）


nonfunction_id（可选）


page（默认 1）


page_size（默认 20）


行为
仅 form_id → general block（该 form 的通用讨论区）


form_id + function_id → 对应 function 的讨论区


form_id + nonfunction_id → 对应 nonfunction 的讨论区


后端内部会：
根据 form_id + function_id/nonfunction_id 定位 / 创建对应 block


然后按时间降序分页


成功
{
  "status": "success",
  "message": "OK",
  "data": {
    "messages": [
      {
        "id": 100,
        "user_id": 8,
        "text_content": "We should adjust the budget.",
        "created_at": "..."
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 35
  }
}


2.5.2 POST /api/v1/message
Body
{
  "form_id": 1,
  "function_id": null,
  "nonfunction_id": null,
  "text_content": "Let's start with login module."
}

后端会：
根据传入参数找到/创建对应 block


插入 message


成功
{"status":"success","message":"Message sent","data":{"message_id":100}}

失败
无权访问该 form / function / nonfunction：FORBIDDEN


PUT / DELETE /api/v1/message/{id} 同理（一般只允许发送者或 admin 修改/删除）。

2.6 Files
2.6.1 POST /api/v1/file
Request
multipart/form-data：


message_id


file（二进制）


行为
校验 message 是否属于当前用户有权访问的 block


校验文件大小（<=10MB）


存储文件，记录 files 表


成功
{"status":"success","message":"File uploaded","data":{"file_id":200}}

失败
超过大小：VALIDATION_ERROR


无权限：FORBIDDEN


2.6.2 GET /api/v1/file/{id}
返回 metadata + 文件下载（前端可以直接用 URL）。
2.6.3 DELETE /api/v1/file/{id}
一般只能由：
附件所在消息的发送者


或 admin


成功：
{"status":"success","message":"File deleted","data":null}


3. 提示给前后端负责人的话（你可以直接转述）
后端重点：


严格按角色（client/developer）和 form 的状态控制权限，尤其是：


mainform vs subform 的增删改


status 的合法流转（preview/available/processing/rewrite/end/error）


subform 只能一个、只能由 created_by 修改 / 删除。


内部用 blocks 表管理消息区，API 层只暴露 form_id + function_id/nonfunction_id。


function/nonfunction 的 is_changed 字段只对 subform 有意义。


前端重点：


登录后使用 /auth/me 获取当前 role 和基本信息，初始化 UI。


client/developer 同用一套 API，但 UI 必须根据 role 和 form.status 控制按钮是否可见（例如：client 不显示接单按钮）。


subform 相关页面需要提供：


“发起协商”（创建 subform）


“同意协商”（合并 subform）


“取消协商”（删除 subform）


“无法达成一致”（将 mainform 设为 error）


消息列表默认加载最近 20 条，向上滚动时请求上一页（page++ 或 cursor）。







Websock 之后要作为获取最新消息
