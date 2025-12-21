# Legacy 到现行代码的完整改动清单

**文档日期**: 2025-12-21  
**范围**: legacy/app 到 app/ 的所有改动  
**总体目标**: 从单层架构重构为模块化三层架构，完善核心业务逻辑，强化安全性和数据一致性

---

## 1. 架构与项目结构重构

### 1.1 分层设计（最大改动）

**Legacy 结构** （单文件型）
```
legacy/app/
├── crud.py              # CRUD 逻辑混在一起
├── models.py            # 所有 ORM 模型
├── permissions.py       # 权限逻辑
├── schemas.py           # Pydantic 模型
├── utils.py             # 工具函数
├── websocket_manager.py # WebSocket
└── routers/             # 所有路由混合
    ├── auth.py
    ├── forms.py
    ├── functions.py
    ├── messages.py
    ├── nonfunctions.py
    ├── files.py
    └── ws.py
```

**现行结构** （模块化三层）
```
app/
├── api/v1/                  # 第一层：路由层
│   ├── auth.py              # 认证路由
│   ├── forms.py             # 表单路由
│   ├── functions.py         # 函数路由
│   ├── nonfunctions.py      # 非函数路由
│   ├── messages.py          # 消息路由
│   ├── files.py             # 文件路由
│   ├── ws.py                # WebSocket 路由
│   └── deps.py              # 依赖注入
│
├── repositories/            # 第二层：数据访问层
│   ├── users.py             # 用户数据操作
│   ├── forms.py             # 表单数据操作
│   ├── functions.py         # 函数数据操作
│   ├── nonfunctions.py      # 非函数数据操作
│   ├── messages.py          # 消息数据操作
│   ├── blocks.py            # 块数据操作
│   ├── files.py             # 文件数据操作
│   ├── licenses.py          # License 数据操作
│   └── __init__.py
│
├── services/                # 第二层：业务逻辑层
│   ├── permissions.py       # 权限校验
│   ├── audit.py             # 审计日志
│   ├── reminders.py         # 提醒调度
│   ├── websocket_manager.py # WebSocket 管理
│   └── __init__.py
│
├── models/                  # 第一层：数据模型层
│   ├── base.py              # Base 类
│   ├── user.py              # User 模型
│   ├── form.py              # Form 模型
│   ├── function.py          # Function 模型
│   ├── nonfunction.py       # NonFunction 模型
│   ├── message.py           # Message 模型
│   ├── block.py             # Block 模型
│   ├── file.py              # File 模型
│   ├── audit_log.py         # AuditLog 模型
│   ├── license.py           # License 模型
│   └── __init__.py
│
├── schemas/                 # 第一层：数据序列化层
│   ├── auth.py              # Auth 模型
│   ├── common.py            # 公共模型
│   ├── forms.py             # Form 模型
│   ├── functions.py         # Function 模型
│   ├── nonfunctions.py      # NonFunction 模型
│   ├── files.py             # File 模型
│   ├── messages.py          # Message 模型
│   └── __init__.py
│
├── utils/                   # 工具层
│   ├── responses.py         # 统一响应格式
│   ├── security.py          # JWT 编解码、密码哈希
│   ├── email_client.py      # 邮件客户端
│   └── __init__.py
│
├── core/
│   ├── database.py          # 数据库连接
│   └── __init__.py
│
├── main.py                  # FastAPI 应用程序
└── __init__.py
```

**改动影响**：
- **可维护性**: 从单一文件降低为模块化组件，每个模块职责单一
- **可测试性**: 各层独立，便于单元测试和集成测试
- **可扩展性**: 新功能可在相应层添加，无需改动其他层
- **代码复用**: 业务逻辑（services）和数据访问（repositories）分离，便于复用

---

## 2. 数据模型层改动

### 2.1 Form 模型

**新增字段**：`approval_flags`
```python
# Legacy: 无此字段
# 现行: approval_flags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
# 用途: 1=developer同意, 2=client同意, 3=双方都同意 (位掩码)
# 场景: processing→end, rewrite→processing 需要双方同意的转换
```

**Schema 改进**：
- Legacy: 所有字段可选或混杂
- 现行: 区分 `FormCreate`、`FormUpdate`、`FormOut`，使用 `extra="forbid"` 防止非法字段

### 2.2 Block 模型

**新增字段**（支持邮件提醒）：
```python
# 现行新增:
# last_message_at: DateTime - 最后消息时间（用于邮件提醒计时）
# reminder_sent: Boolean - 是否已发送提醒（防重复）
```

**改动理由**: Legacy 中 `status` 字段（urgent/normal）存在但未使用，新增字段支持完整的邮件提醒流程

### 2.3 License 模型

**现行完整实现**（Legacy 中存在但未接入业务）：
- `activate()` - 激活 license 并绑定用户
- `validate_active()` - 检查 license 是否有效（登录时调用）
- `activate_new_for_user()` - 用户切换 license

### 2.4 新增模型：AuditLog

**完全新增**：
```python
class AuditLog(Base):
    entity_type: Mapped[str]  # form/function/nonfunction/message/file
    entity_id: Mapped[int]
    action: Mapped[str]        # create/update/delete/status_change/merge_subform
    user_id: Mapped[int | None]
    old_data: Mapped[dict]     # JSON，旧值
    new_data: Mapped[dict]     # JSON，新值
    created_at: Mapped[datetime]
```

**改动理由**: 规范要求审计追踪，新增完整审计基础设施

---

## 3. 认证与权限（Auth & License）

### 3.1 注册流程强化

**Legacy 流程**：
```
1. 校验邮箱 → 创建用户（is_active=True）
2. 创建用户后尝试激活 license
3. 缺少: license_key 校验、激活失败回滚
```

**现行流程** `[提交 6433482]`：
```
1. 校验邮箱 + license_key
2. 创建用户（is_active=False）【关键变动】
3. 激活 license（成功才设 is_active=True）
4. 失败则回滚用户创建
```

**API 返回值变动**:
```python
# Legacy:
{"status": "success", "message": "User registered"}

# 现行:
{
    "status": "success",
    "data": {
        "access_token": "...",
        "role": "client|developer"  # 【新增】
    }
}
```

### 3.2 登录时 License 校验 `[提交 27d602a]`

**Legacy**: 仅校验用户存在和密码

**现行** `[提交 27d602a]`：
```python
def login(email, password):
    user = get_user_by_email(email)
    if not validate_password(password, user.password_hash):
        return 401
    
    # 【新增】检查 license 状态
    license = get_license_by_user(user.id)
    if license.status not in ["active", "unused"]:  # 过期或撤销
        user.is_active = 0  # 禁用用户
        return 403  # FORBIDDEN
    
    return generate_token(user)
```

**改动理由**: 确保登录用户的 license 有效，过期/撤销的 license 无法访问系统

### 3.3 新增重新激活端点 `[提交 27d602a]`

```
POST /api/v1/auth/reactivate
Body: { new_license_key: str }
逻辑: 
  1. 撤销旧 license
  2. 激活新 license_key
  3. 更新用户角色
```

**改动理由**: 允许用户在 license 过期后激活新 license 重新使用系统

---

## 4. 状态机与协商流程完善

### 4.1 基础状态转换完整化 `[提交 9552527]`

**Legacy 状态表**（permissions.py）：
```
preview → available → processing → {rewrite, end, error}
rewrite → {processing, error}
end/error: 终止，无出边
```

**现行扩展** `[提交 9552527-c21542c]`：
```
或转换（单角色可直接执行）:
- Client: preview→available, processing→rewrite(或), rewrite→error(或)
- Developer: available→processing(绑定), processing→rewrite(或), rewrite→error(或)

与转换（需双方同意）:
- processing→end (双方同意才转换)
- rewrite→processing (双方同意才转换)
```

**关键改动**: 使用 `approval_flags` 位掩码实现"与转换" `[提交 c21542c]`

```python
# 位掩码: 1=developer, 2=client, 3=both
if target_status == "end":
    if current_role == "client":
        form.approval_flags |= 2  # 设置 client 同意位
    else:  # developer
        form.approval_flags |= 1  # 设置 developer 同意位
    
    # 双方都同意才转换
    if form.approval_flags == 3:
        form.status = "end"
        form.approval_flags = 0
```

### 4.2 Subform 合并完整化 `[提交 d1cb0ce, 0c83ddd]`

**Legacy 操作**：
- 创建 subform: mainform.status = rewrite
- 删除 subform: mainform.status = processing（无合并逻辑）

**现行操作** `[提交 d1cb0ce]`：

**创建 Subform**：
```python
POST /form/{id}/subform
效果:
1. 创建 subform 副本（仅 mainform）
2. mainform.status = rewrite
3. subform.created_by = 当前用户
```

**合并 Subform** `[提交 d1cb0ce, 0c83ddd]`：
```python
POST /form/{mainform_id}/subform/merge
前置条件: mainform.subform_id 不为空
逻辑:
1. 覆写 mainform 内容 (title, message, budget, expected_time)
2. 复制所有 functions/nonfunctions，重置 is_changed=0
3. 删除 subform 记录
4. mainform.status = processing
5. mainform.approval_flags = 0 (重置同意标记)
```

**删除 Subform** `[提交 d1cb0ce]`：
```python
DELETE /form/{id}?set_error=false (默认)
效果: mainform.status = processing (继续工作)

DELETE /form/{id}?set_error=true
效果: mainform.status = error (协商失败)
```

**改动理由**: 完整的协商流程，支持"合并"和"拒绝"两个分支

---

## 5. 权限校验强化

### 5.1 未知角色直接 403 `[提交 650157a]`

**Legacy**：
```python
def assert_can_view_form(user, form):
    if user.role == "client" and form.user_id != user.id:
        raise FORBIDDEN
    if user.role == "developer" and form.developer_id != user.id:
        raise FORBIDDEN
    # 其他角色（如 admin）通过
    return  # 【问题】允许未知角色通过
```

**现行** `[提交 650157a]`：
```python
def assert_can_view_form(user, form):
    if user.role not in ["client", "developer"]:
        raise FORBIDDEN  # 【改动】未知角色直接拒绝
    
    if user.role == "client" and form.user_id != user.id:
        raise FORBIDDEN
    if user.role == "developer" and form.developer_id != user.id:
        raise FORBIDDEN
```

**改动理由**: 完全移除 admin 角色支持（规范未定义），提高安全性

### 5.2 未激活用户无法访问系统 `[提交 650157a, 6433482]`

**Legacy**：
```python
@app.get("/form/{id}")
async def get_form(id: int, current_user = Depends(get_current_user)):
    # current_user.is_active 未检查
    return form
```

**现行** `[提交 650157a]`：
```python
def get_current_user(token: str):
    user = decode_token(token)
    if user.is_active == 0:  # 【新增】
        raise UNAUTHORIZED  # license 过期等原因
    return user
```

**改动理由**: License 过期/撤销时用户应被禁用

---

## 6. 数据校验与安全加强

### 6.1 Update Schema 白名单 `[提交 63a946f]`

**Legacy**：
```python
@app.put("/form/{id}")
async def update_form(id: int, data: dict):
    db.update_form(id, **data)  # 【问题】任意字段可改
    # 前端可能修改 developer_id、user_id 等敏感字段
```

**现行** `[提交 63a946f]`：
```python
class FormUpdate(BaseModel):
    title: str | None = None
    message: str | None = None
    budget: str | None = None
    expected_time: str | None = None
    
    model_config = ConfigDict(extra="forbid")  # 【新增】禁止额外字段

@app.put("/form/{id}")
async def update_form(id: int, data: FormUpdate):
    db.update_form(id, **data.model_dump(exclude_unset=True))
    # 现在只能修改允许的字段
```

**改动理由**: 防止客户端修改敏感字段

### 6.2 JWT 强制配置 `[提交 16dc1d7]`

**Legacy**：
```python
# utils.py
SECRET_KEY = os.getenv("SECRET_KEY")  # 可能为 None
if not SECRET_KEY:
    SECRET_KEY = "your-secret-key-here"  # 【问题】默认值

def encode_token(user):
    return jwt.encode({"user_id": user.id}, SECRET_KEY)
```

**现行** `[提交 16dc1d7]`：
```python
# security.py
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "your-secret-key-here":
    raise RuntimeError(  # 【改动】启动时强制配置
        "SECRET_KEY 未配置或使用默认值，请设置 .env 中的 SECRET_KEY"
    )

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if "sub" not in payload:  # 【新增】强制检查
            raise UNAUTHORIZED
        return payload["sub"]
    except JWTError:
        raise UNAUTHORIZED
```

**改动理由**: 强制使用强密钥，提高 JWT 安全性

---

## 7. 数据库一致性改进

### 7.1 Server 默认值对齐 `[提交 f4bde4b]`

**Legacy**：
```python
# models.py
class User(Base):
    is_active = Column(Boolean, default=False)  # Python 默认
    # 【问题】未设 server_default，数据库插入时可能为 NULL

class Block(Base):
    status = Column(Enum(BlockStatus), default=BlockStatus.normal)  # Python 默认
    type = Column(Enum(BlockType), default=BlockType.general)
```

**现行** `[提交 f4bde4b]`：
```python
# models/user.py (Alembic 迁移)
is_active: Mapped[bool] = mapped_column(
    Boolean, 
    nullable=False, 
    server_default="0"  # 【新增】
)

# models/block.py
status: Mapped[str] = mapped_column(
    Enum("urgent", "normal"),
    nullable=False,
    server_default="normal"  # 【新增】
)
```

**改动理由**: Python 默认值仅在 ORM 层生效，数据库直接插入时可能绕过，导致不一致

---

## 8. 消息与实时通信改进

### 8.1 异步操作改为 await `[提交 650157a]`

**Legacy**：
```python
@app.post("/message")
async def create_message(msg: MessageCreate, user = Depends(get_current_user)):
    message = db.create_message(msg)
    
    # 【问题】fire-and-forget，消息可能丢失
    asyncio.create_task(manager.broadcast(...))
    
    return message
```

**现行** `[提交 650157a]`：
```python
@app.post("/message")
async def create_message(msg: MessageCreate, user = Depends(get_current_user)):
    message = db.create_message(msg)
    
    # 【改动】确保广播完成
    await manager.broadcast(...)
    
    return message
```

**改动理由**: `create_task` 为 fire-and-forget，可能导致消息未及时广播或协程泄漏

### 8.2 消息排序改为降序 `[提交 6433482]`

**Legacy**：
```python
# repositories/messages.py
def list_messages(form_id):
    return db.query(Message).filter(Message.form_id == form_id)\
              .order_by(Message.created_at).all()  # 升序
```

**现行** `[提交 6433482]`：
```python
def list_messages(form_id):
    return db.query(Message).filter(Message.form_id == form_id)\
              .order_by(Message.created_at.desc()).all()  # 降序
```

**改动理由**: 降序（最新消息在前）更符合 UI 展示习惯

### 8.3 WebSocket Presence 推送 `[提交 3ffbb06]`

**Legacy**：
```python
# ws.py
@app.websocket("/ws/messages")
async def websocket_endpoint(form_id, token):
    manager.connect(form_id, websocket)
    # 【缺失】无用户上线/离线通知
    await manager.broadcast(message)
```

**现行** `[提交 3ffbb06]`：
```python
async def websocket_endpoint(form_id, token):
    manager.connect(form_id, websocket)
    
    # 【新增】广播用户上线
    await manager.broadcast({
        "type": "presence",
        "user_id": user.id,
        "action": "join"
    })
    
    # 【新增】广播用户离线
    await manager.broadcast({
        "type": "presence",
        "user_id": user.id,
        "action": "leave"
    })
```

**改动理由**: 前端可显示在线用户，改善用户体验

---

## 9. 邮件提醒调度系统（完全新增）

### 9.1 数据库字段 `[提交 da446e9, 21fe2ee]`

```python
# Block 模型新增
last_message_at: Mapped[datetime]     # 最后消息时间
reminder_sent: Mapped[bool] = False   # 是否已发送提醒
```

### 9.2 调度器启动 `[提交 8c24d6d]`

```python
# main.py
@app.on_event("startup")
async def startup():
    # 【新增】启动两个后台任务
    asyncio.create_task(reminders.start_urgent_scheduler())
    asyncio.create_task(reminders.start_normal_scheduler())
```

### 9.3 调度逻辑 `[提交 6b11691, 8c24d6d]`

```python
# services/reminders.py
async def start_urgent_scheduler():
    while True:
        # 每 5 分钟扫描一次
        blocks = get_blocks_urgent_without_reminder()
        for block in blocks:
            if (now - block.last_message_at) > 5min:
                await send_email_reminder(block)
                block.reminder_sent = True

async def start_normal_scheduler():
    while True:
        # 每 1 小时扫描一次
        blocks = get_blocks_normal_without_reminder()
        for block in blocks:
            if (now - block.last_message_at) > 48h:
                await send_email_reminder(block)
                block.reminder_sent = True
```

**改动理由**: 规范要求的自动邮件提醒，支持 urgent (5分钟) 和 normal (48小时) 两种

---

## 10. 审计日志系统（完全新增）

### 10.1 数据库表 `[提交 ea5521a]`

```python
# models/audit_log.py
class AuditLog(Base):
    entity_type: str        # form/function/nonfunction/message/file
    entity_id: int
    action: str             # create/update/delete/status_change/merge_subform
    user_id: int | None     # 执行者
    old_data: dict          # JSON，修改前
    new_data: dict          # JSON，修改后
    created_at: datetime
```

### 10.2 写入点 `[提交 ea5521a]`

```python
# 所有主要 CRUD 操作都添加审计钩子
- 表单: 创建、更新、状态变更、合并 subform
- 函数/非函数: 创建、更新、删除
- 消息: 创建、删除
- 文件: 创建、删除

# 示例
@app.put("/form/{id}")
async def update_form(id: int, data: FormUpdate):
    old = db.get_form(id)
    db.update_form(id, **data)
    audit.insert_log(
        entity_type="form",
        entity_id=id,
        action="update",
        user_id=current_user.id,
        old_data=old.to_dict(),
        new_data=db.get_form(id).to_dict()
    )
```

**改动理由**: 规范要求审计追踪，便于问题追踪和合规性检查

---

## 11. 文件处理改进

### 11.1 文件扩展名存储 `[提交 d4355f5]`

**Legacy**：
```python
# models.py
class File(Base):
    file_name = Column(String)
    storage_path = Column(String)
    file_size = Column(Integer)
    # 【缺失】无扩展名记录
```

**现行** `[提交 d4355f5]`：
```python
# models/file.py
class File(Base):
    file_name: Mapped[str]
    file_ext: Mapped[str]       # 【新增】扩展名
    storage_path: Mapped[str]
    file_size: Mapped[int]
```

**改动理由**: 用于文件预览功能的类型判断

### 11.2 文件下载流式返回 `[提交 947c9cf]`

**Legacy**：
```python
@app.get("/file/{id}")
async def get_file(id: int):
    file = db.get_file(id)
    return {  # 【缺陷】仅返回元数据
        "id": file.id,
        "name": file.file_name,
        "size": file.file_size
    }
```

**现行** `[提交 947c9cf]`：
```python
@app.get("/file/{id}")
async def get_file(id: int):
    file = db.get_file(id)
    return FileResponse(  # 【改动】流式返回文件
        path=file.storage_path,
        filename=file.file_name,
        media_type="application/octet-stream"
    )
```

**改动理由**: 允许前端直接下载文件

---

## 12. Error Code 规范化 `[提交 2218a66]`

**Legacy**：
```python
# 错误码混杂，无统一标准
raise HTTPException(status_code=400, detail="Invalid request")
raise HTTPException(status_code=403, detail="Permission denied")
```

**现行** `[提交 2218a66]`：
```python
# utils/responses.py
ERROR_CODES = {
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "CONFLICT": 409,
    "LICENSE_EXPIRED": 403,
    "LICENSE_REVOKED": 403,
}

# 统一返回格式
def error_response(code: str, message: str):
    return {
        "status": "error",
        "code": code,
        "message": message,
        "data": None
    }
```

**改动理由**: 前端可根据统一的 error code 处理不同场景

---

## 13. 开发工具与配置改进

### 13.1 .env.template 完善 `[提交 e16a640, 27d602a]`

**新增配置项**：
```bash
# License 和认证
LICENSE_GRACE_PERIOD_DAYS=7

# 提醒配置
REMINDER_URGENT_MINUTES=5
REMINDER_NORMAL_HOURS=48

# Resend 邮件配置
RESEND_API_KEY=...
RESEND_SENDER_EMAIL=bridge-no-reply@icu.584743.xyz

# JWT 密钥（强制配置）
SECRET_KEY=...
```

**改动理由**: 完整的环境变量管理，便于本地开发和生产部署

### 13.2 密码强度校验 `[提交 27d602a]`

**Legacy**：
```python
# 无密码强度要求
def create_user(email, password):
    password_hash = hash_password(password)  # 接受任意密码
```

**现行** `[提交 27d602a]`：
```python
def create_user(email, password):
    if len(password) < 8:
        raise ValidationError("密码至少 8 个字符")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("密码必须包含大写字母")
    if not re.search(r"[0-9]", password):
        raise ValidationError("密码必须包含数字")
    
    password_hash = hash_password(password)
```

**改动理由**: 提高用户密码安全性

---

## 14. 列表与详情接口优化

### 14.1 表单列表 - 角色过滤改进 `[提交 6433482]`

**Legacy**：
```python
@app.get("/forms")
async def list_forms(user = Depends(get_current_user)):
    if user.role == "client":
        return db.query(Form).filter(Form.user_id == user.id).all()
    elif user.role == "developer":
        # 【问题】混入所有 available 和已接单
        return db.query(Form).filter(
            or_(Form.developer_id == user.id, Form.status == "available")
        ).all()
```

**现行** `[提交 6433482]`：
```python
@app.get("/forms")
async def list_forms(user = Depends(get_current_user), available_only: bool = False):
    if user.role == "client":
        return db.query(Form).filter(Form.user_id == user.id).all()
    elif user.role == "developer":
        if available_only:
            # 【改动】显式拉取 available（待接单）
            return db.query(Form).filter(Form.status == "available").all()
        else:
            # 默认显示已接单和已处理
            return db.query(Form).filter(Form.developer_id == user.id).all()
```

**改动理由**: 更清晰的查询语义，避免新 developer 意外看到大量待接单表单

### 14.2 表单详情 - 权限校验 `[提交 6433482]`

**新增权限细分**：
```python
def assert_can_view_form_detail(user, form):
    if user.role == "client":
        # Client 仅能看自己的
        if form.user_id != user.id:
            raise FORBIDDEN
    elif user.role == "developer":
        # Developer 仅能看已接单或 available（可接单）的
        if form.developer_id != user.id and form.status != "available":
            raise FORBIDDEN
```

**改动理由**: 防止 developer 查看其他人已接单的表单

---

## 15. 总体改动统计

| 维度 | Legacy | 现行 | 变化 |
|------|--------|------|------|
| 文件数 | ~20 | ~50+ | +150% |
| 代码行数 | ~3000 | ~8000+ | +170% |
| 提交数 | - | 40+ | - |
| 数据表 | 8 | 10+ | +2 |
| API 端点 | ~30 | ~40+ | +30% |
| 单元测试 | 0 | (规划中) | - |
| 文档页数 | - | 5+ | - |

---

## 16. 核心改动在代码中的体现

### 数据层（Repository Pattern）
- `app/repositories/` - 所有数据访问操作集中
- 便于数据库迁移（如从 MySQL 迁移到 PostgreSQL）

### 业务逻辑层（Service Pattern）
- `app/services/permissions.py` - 权限校验（复杂逻辑）
- `app/services/audit.py` - 审计日志（新增）
- `app/services/reminders.py` - 邮件提醒（新增）
- `app/services/websocket_manager.py` - WebSocket 管理

### API 层（Routes）
- `app/api/v1/` - 统一的 v1 API
- 各路由专注于请求验证和响应格式化
- 业务逻辑委托给 services

### 数据模型层（Models）
- `app/models/` - ORM 模型，对应数据表
- 使用新的 SQLAlchemy 2.0 Mapped 风格

### 数据序列化层（Schemas）
- `app/schemas/` - Pydantic 模型，请求/响应验证
- 与 API 端点强耦合，便于文档化

---

## 17. 迁移建议（供未来参考）

如果需要进一步完善：

1. **完全移除 admin 角色** ✅ 已完成 `[提交 a9fe7bf]`
   - 清理 permissions.py 中的 admin 分支
   - 验证所有端点都遵循 client/developer 权限

2. **添加单元测试** ⏳ 建议
   - tests/unit/repositories/ - 数据访问测试
   - tests/unit/services/ - 业务逻辑测试
   - tests/integration/api/ - API 端点测试

3. **性能优化** 📊 建议
   - 添加数据库查询索引（已添加部分）
   - 实现分页和缓存
   - 监控慢查询

4. **安全加固** 🔒 建议
   - 添加 CORS 配置
   - 实现 Rate Limiting
   - 添加 SQL 注入防护（SQLAlchemy ORM 已防护）

5. **文件预览** 📄 建议
   - 实现 GET /file/{id}/preview
   - 支持大文件外链（>1GB）

---

## 总结

从 Legacy 到现行的改动是一个**大规模架构重构**：

- ✅ **从单层到三层**: 分离了路由、业务逻辑、数据访问
- ✅ **安全性**: 强化了 JWT、密码、权限校验
- ✅ **完整性**: 实现了 License 生命周期、审计日志、邮件提醒
- ✅ **一致性**: 数据库、ORM、Schema 统一对齐
- ✅ **可维护性**: 模块化设计便于扩展和维护

预计这次重构为后续的功能开发和维护打下了坚实的基础。
