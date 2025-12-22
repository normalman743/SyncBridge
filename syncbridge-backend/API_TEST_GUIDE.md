# SyncBridge API 测试指南

**文档版本**: 1.0  
**最后更新**: 2025-12-21  
**范围**: 所有 REST API 端点的测试计划与实现指南

---

## 📋 目录

1. [测试框架与设置](#测试框架与设置)
2. [测试分类](#测试分类)
3. [API 端点测试清单](#api-端点测试清单)
4. [测试场景详解](#测试场景详解)
5. [测试数据与 Fixtures](#测试数据与-fixtures)
6. [运行测试](#运行测试)
7. [覆盖率目标](#覆盖率目标)

---

## 测试框架与设置

### 依赖

```bash
poetry add --group dev pytest pytest-cov pytest-asyncio httpx
```

已安装版本：
- pytest 9.0.2
- pytest-cov 7.0.0
- pytest-asyncio 1.3.0
- httpx 0.28.1

### 测试目录结构

```
tests/
├── __init__.py
├── conftest.py                    # 全局 fixtures 和配置
├── unit/
│   ├── __init__.py
│   ├── test_repositories/
│   │   ├── test_users.py
│   │   ├── test_forms.py
│   │   ├── test_licenses.py
│   │   └── test_messages.py
│   ├── test_services/
│   │   ├── test_permissions.py
│   │   ├── test_audit.py
│   │   └── test_reminders.py
│   └── test_utils/
│       ├── test_security.py
│       └── test_responses.py
└── integration/
    ├── __init__.py
    ├── test_auth_flow.py          # 认证完整流程
    ├── test_form_lifecycle.py     # 表单完整生命周期
    ├── test_subform_negotiation.py # 协商流程
    ├── test_messages_and_files.py # 消息和文件
    └── test_status_transitions.py # 状态转换
```

---

## 测试分类

### 单元测试 (Unit Tests)

**目标**: 测试独立的函数/类，不依赖外部资源

**范围**:
- Repositories: CRUD 操作
- Services: 业务逻辑（权限、审计、提醒）
- Utils: 工具函数（安全、响应格式化）

**预期覆盖率**: 80%+

---

### 集成测试 (Integration Tests)

**目标**: 测试 API 端点完整流程，涉及数据库和多个模块协作

**范围**:
- 完整的认证流程（注册→登录→重新激活）
- 表单完整生命周期（创建→更新→状态转换→删除）
- Subform 协商流程（创建→合并→拒绝）
- 消息和文件操作（创建→更新→删除）
- WebSocket 实时通信（需单独测试）

**预期覆盖率**: 70%+

---

## API 端点测试清单

### 1. 认证 API (Auth)

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/auth/register` | POST | 用户注册 | ✓ | ✓ | P0 |
| `/auth/login` | POST | 用户登录 | ✓ | ✓ | P0 |
| `/auth/me` | GET | 获取当前用户 | ✓ | ✓ | P1 |
| `/auth/reactivate` | POST | 重新激活 License | ✓ | ✓ | P1 |

**测试场景**:
```
注册:
  - ✓ 正常注册（有效 email, 强密码, 有效 license_key）
  - ✗ Email 已存在
  - ✗ 密码过弱（<8字符，缺字母/数字）
  - ✗ License 不存在
  - ✗ License 已过期
  - ✗ License 已被使用

登录:
  - ✓ 正常登录
  - ✗ Email 不存在
  - ✗ 密码错误
  - ✗ License 过期（自动禁用用户）
  - ✗ License 撤销（自动禁用用户）
  - ✗ 用户被禁用（is_active=0）

Me:
  - ✓ 返回当前用户信息
  - ✗ 无 Token
  - ✗ Token 过期

重新激活:
  - ✓ 切换到新 License
  - ✗ 旧 License 不存在
  - ✗ 新 License 无效
  - ✗ 无权限（不是自己的账户）
```

---

### 2. 表单 API (Forms)

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/forms` | GET | 列表表单 | ✓ | ✓ | P0 |
| `/form/{id}` | GET | 获取表单详情 | ✓ | ✓ | P0 |
| `/form` | POST | 创建表单 | ✓ | ✓ | P0 |
| `/form/{id}` | PUT | 更新表单 | ✓ | ✓ | P0 |
| `/form/{id}` | DELETE | 删除表单 | ✓ | ✓ | P1 |
| `/form/{id}/status` | PUT | 转换状态 | ✓ | ✓ | P0 |

**列表 GET /forms**:
```
权限过滤:
  - ✓ Client: 仅看自己的表单
  - ✓ Developer: available_only=true 看待接单，否则看已接单
  - ✗ 无权限用户返回 403

分页:
  - ✓ page=1, page_size=20
  - ✓ 超出范围返回空列表
  - ✗ page_size > 100（可选限制）

返回字段:
  - ✓ id, type, title, status, approval_flags, subform_id, created_at
  - ✓ 分页信息 (page, page_size, total)
```

**创建 POST /form**:
```
权限:
  - ✓ Client 可创建（仅 mainform）
  - ✗ Developer 无法创建
  - ✗ 无权限 403

字段校验:
  - ✓ title, message, budget, expected_time 均必填
  - ✗ title 为空
  - ✗ 超长字段

初始状态:
  - ✓ status=preview
  - ✓ 审计日志记录（action=create）
```

**更新 PUT /form/{id}**:
```
权限:
  - ✓ Client 可更新自己 preview/available 的表单
  - ✓ Developer 可更新已接单的表单（processing/rewrite 态）
  - ✗ Subform 仅 created_by 可改
  - ✗ 无权限 403

字段白名单 (extra=forbid):
  - ✓ 仅允许: title, message, budget, expected_time
  - ✗ 尝试改 developer_id → 422 错误

状态约束:
  - ✗ end/error 状态下无法编辑
  - ✓ 审计日志记录（action=update）
```

**删除 DELETE /form/{id}**:
```
Subform 删除:
  - ✓ set_error=false (默认): mainform.status = processing
  - ✓ set_error=true: mainform.status = error
  - ✓ 审计日志记录（action=delete）

权限:
  - ✓ Subform 仅 created_by 可删除
  - ✗ 其他用户 403
  - ✗ 无此表单 404
```

**状态转换 PUT /form/{id}/status**:
```
或转换（单角色直接执行）:
  Client:
    - ✓ preview → available
    - ✓ processing → rewrite (或)
    - ✓ rewrite → error (或)
    - ✗ 非法转换 409
  
  Developer:
    - ✓ available → processing (绑定自己)
    - ✓ processing → rewrite (或)
    - ✓ processing → error (或)
    - ✓ rewrite → error (或)
    - ✗ 非法转换 409

与转换（需双方同意）:
  processing → end:
    - ✓ Client 调用: approval_flags |= 2
    - ✓ Developer 调用: approval_flags |= 1
    - ✓ approval_flags == 3: 自动转换状态
    - ✓ approval_flags 重置为 0

  rewrite → processing:
    - ✓ 合并后自动触发
    - ✓ 同意机制（approval_flags）

权限:
  - ✓ 仅接单的 developer 或 client 可转换
  - ✗ 无权限 403
  - ✓ 审计日志记录（action=status_change）
```

---

### 3. Subform 协商 API

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/form/{id}/subform` | POST | 创建 Subform | ✓ | ✓ | P0 |
| `/form/{mainform_id}/subform/merge` | POST | 合并 Subform | ✓ | ✓ | P0 |

**创建 POST /form/{id}/subform**:
```
前置条件:
  - ✓ mainform 状态 in {available, processing, rewrite}
  - ✗ 已存在 subform（每个 mainform 仅一个）409
  - ✓ 无既有 subform 可创建

效果:
  - ✓ 创建 subform 副本
  - ✓ mainform.status → rewrite
  - ✓ approval_flags 重置为 0
  - ✓ 审计日志记录（action=create）

权限:
  - ✓ Client/Developer 均可创建
  - ✗ 无权限 403
```

**合并 POST /form/{mainform_id}/subform/merge**:
```
前置条件:
  - ✓ mainform.subform_id 非空
  - ✗ mainform 无 subform 404

效果（repo 层）:
  - ✓ 覆写 mainform 内容 (title, message, budget, expected_time)
  - ✓ 复制所有 functions/nonfunctions
  - ✓ 重置 is_changed = 0
  - ✓ 删除 subform 记录
  - ✓ mainform.status = processing
  - ✓ approval_flags = 0

权限:
  - ✓ Client（mainform.user_id）可合并
  - ✓ Developer（mainform.developer_id）可合并
  - ✗ 无权限 403

审计:
  - ✓ 审计日志记录（action=merge_subform）
  - ✓ old_data/new_data 记录内容变更
```

---

### 4. 函数 API (Functions)

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/functions` | GET | 列表函数 | ✓ | ✓ | P1 |
| `/function` | POST | 创建函数 | ✓ | ✓ | P1 |
| `/function/{id}` | PUT | 更新函数 | ✓ | ✓ | P1 |
| `/function/{id}` | DELETE | 删除函数 | ✓ | ✓ | P1 |

**创建 POST /function**:
```
字段:
  - ✓ form_id, name, choice, description 必填
  - ✓ is_changed 默认 false

权限:
  - ✓ Mainform 的 client/developer 可创建
  - ✓ Subform 仅 created_by 可创建
  - ✗ 无权限 403

约束（待实现）:
  - ⚠️ is_changed=1 仅 subform 可设（API 层校验待加）
  - ✗ mainform 下 is_changed=1 应返回 422

审计:
  - ✓ 审计日志记录（action=create）
```

**更新 PUT /function/{id}**:
```
权限:
  - ✓ 创建者可更新
  - ✓ Admin 可更新（若存在）
  - ✗ 其他用户 403

约束:
  - ✓ 字段白名单（extra=forbid）
  - ⚠️ is_changed 约束同上

审计:
  - ✓ 审计日志记录（action=update）
```

**删除 DELETE /function/{id}**:
```
权限:
  - ✓ 创建者可删除
  - ✓ Admin 可删除
  - ✗ 其他用户 403

级联:
  - ✓ 删除函数时删除关联的 block/message
  - ✓ 审计日志记录（action=delete）
```

---

### 5. 非函数 API (NonFunctions)

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/nonfunctions` | GET | 列表非函数 | ✓ | ✓ | P1 |
| `/nonfunction` | POST | 创建非函数 | ✓ | ✓ | P1 |
| `/nonfunction/{id}` | PUT | 更新非函数 | ✓ | ✓ | P1 |
| `/nonfunction/{id}` | DELETE | 删除非函数 | ✓ | ✓ | P1 |

**测试场景**: 与 Functions 类似

---

### 6. 消息 API (Messages)

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/messages` | GET | 列表消息 | ✓ | ✓ | P0 |
| `/message` | POST | 发送消息 | ✓ | ✓ | P0 |
| `/message/{id}` | PUT | 编辑消息 | ✓ | ✓ | P1 |
| `/message/{id}` | DELETE | 删除消息 | ✓ | ✓ | P1 |
| `/block/{id}/status` | PUT | 更新块状态 | ✓ | ✓ | P1 |

**GET /messages**:
```
参数:
  - ✓ form_id (必需)
  - ✓ function_id (可选)
  - ✓ nonfunction_id (可选)
  - ✓ page, page_size

权限:
  - ✓ 可访问对应 block 的用户可查询
  - ✗ 无权限 403

返回:
  - ✓ 消息列表 + 附件列表 (files 数组)
  - ✓ 按 created_at DESC 排序（最新在前）
  - ✓ 分页信息
```

**POST /message**:
```
字段:
  - ✓ form_id, content 必填
  - ✓ function_id/nonfunction_id (可选)

权限:
  - ✓ 可访问 form 的用户可发送
  - ✗ 无权限 403

效果:
  - ✓ 创建 message 记录
  - ✓ 自动创建或找到对应 block
  - ✓ 更新 block.last_message_at = now
  - ✓ 重置 block.reminder_sent = false
  - ✓ WebSocket 广播消息
  - ✓ 审计日志记录（action=create）

验证:
  - ✗ content 为空
  - ✗ form 不存在 404
```

**PUT /message/{id}**:
```
权限:
  - ✓ 消息发送者可编辑
  - ✗ 其他用户 403

约束:
  - ✓ 字段白名单
  - ✓ 审计日志记录（action=update）
```

**DELETE /message/{id}**:
```
权限:
  - ✓ 消息发送者可删除
  - ✓ Admin 可删除
  - ✗ 其他用户 403

效果:
  - ✓ 删除 message 记录
  - ✓ 审计日志记录（action=delete）
```

**PUT /block/{id}/status**:
```
字段:
  - ✓ status: urgent | normal

效果:
  - ✓ 更新 block.status
  - ✓ 重置 block.reminder_sent = false
  - ✓ 更新 block.last_message_at = now

权限:
  - ✓ 可访问 form 的用户可更新
  - ✗ 无权限 403
```

---

### 7. 文件 API (Files)

| 端点 | 方法 | 功能 | 单元 | 集成 | 优先级 |
|------|------|------|------|------|--------|
| `/file` | POST | 上传文件 | ✓ | ✓ | P0 |
| `/file/{id}` | GET | 下载文件 | ✓ | ✓ | P0 |
| `/file/{id}` | DELETE | 删除文件 | ✓ | ✓ | P1 |

**POST /file (上传)**:
```
大小限制:
  - ✓ <= 10MB
  - ✗ > 10MB 返回 413，提示压缩或提供外链

字段:
  - ✓ file (binary)
  - ✓ message_id, form_id

权限:
  - ✓ 可访问 message 所属 form 的用户可上传
  - ✗ 无权限 403

效果:
  - ✓ 存储到 /storage/files/{file_id}/{filename}
  - ✓ 提取文件扩展名 (file_ext)
  - ✓ 创建 File 记录
  - ✓ 审计日志记录（action=create）

验证:
  - ✗ 文件类型限制（可选）
  - ✗ 恶意文件检测（可选）
```

**GET /file/{id} (下载)**:
```
权限:
  - ✓ 消息发送者或可访问 block 用户可下载
  - ✗ 无权限 403
  - ✗ 文件不存在 404

返回:
  - ✓ FileResponse（流式返回）
  - ✓ 正确的 Content-Type
  - ✓ 文件名设置
```

**DELETE /file/{id}**:
```
权限:
  - ✓ 文件上传者可删除
  - ✓ Admin 可删除
  - ✗ 其他用户 403

效果:
  - ✓ 删除文件记录
  - ✓ 删除磁盘上的文件
  - ✓ 审计日志记录（action=delete）
```

---

## 测试场景详解

### 场景 1: 完整认证流程

```python
# 注册 → 激活 → 登录 → 获取用户信息 → 重新激活

def test_complete_auth_flow(client):
    # 1. 注册
    register_resp = client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "Password123",
        "license_key": "VALID_LICENSE_KEY",
        "display_name": "Test User"
    })
    assert register_resp.status_code == 200
    data = register_resp.json()
    token1 = data["data"]["access_token"]
    assert data["data"]["role"] in ["client", "developer"]
    
    # 2. 登录
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "Password123"
    })
    assert login_resp.status_code == 200
    token2 = login_resp.json()["data"]["access_token"]
    
    # 3. 获取用户信息
    headers = {"Authorization": f"Bearer {token2}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user = me_resp.json()["data"]
    assert user["email"] == "user@example.com"
    assert user["is_active"] == True
    
    # 4. 重新激活（使用新 License）
    reactivate_resp = client.post(
        "/api/v1/auth/reactivate",
        json={"new_license_key": "NEW_LICENSE_KEY"},
        headers=headers
    )
    assert reactivate_resp.status_code == 200
```

---

### 场景 2: 表单完整生命周期

```python
# 创建 → 更新 → 发布 → 接单 → 协商（Subform）→ 完成

def test_form_complete_lifecycle(client_token, developer_token, db):
    # 1. Client 创建表单 (status=preview)
    create_resp = client.post("/api/v1/form", json={
        "title": "New Feature Request",
        "message": "Please implement...",
        "budget": "$5000",
        "expected_time": "2 weeks"
    }, headers={"Authorization": f"Bearer {client_token}"})
    assert create_resp.status_code == 200
    form_id = create_resp.json()["data"]["id"]
    
    # 2. Client 更新表单
    update_resp = client.put(f"/api/v1/form/{form_id}", json={
        "title": "Updated Title",
        "message": "Updated message"
    }, headers={"Authorization": f"Bearer {client_token}"})
    assert update_resp.status_code == 200
    
    # 3. Client 发布 (preview → available)
    status_resp = client.put(f"/api/v1/form/{form_id}/status", json={
        "status": "available"
    }, headers={"Authorization": f"Bearer {client_token}"})
    assert status_resp.status_code == 200
    
    # 4. Developer 接单 (available → processing)
    pickup_resp = client.put(f"/api/v1/form/{form_id}/status", json={
        "status": "processing"
    }, headers={"Authorization": f"Bearer {developer_token}"})
    assert pickup_resp.status_code == 200
    form = pickup_resp.json()["data"]
    assert form["developer_id"] == developer_id
    
    # 5. Developer 创建 Subform 请求修改
    subform_resp = client.post(f"/api/v1/form/{form_id}/subform", 
        headers={"Authorization": f"Bearer {developer_token}"})
    assert subform_resp.status_code == 200
    subform_id = subform_resp.json()["data"]["id"]
    
    # 6. Client 编辑 Subform
    # ... 编辑 subform 的 functions/nonfunctions
    
    # 7. 双方合并 (rewrite → processing)
    merge_resp = client.post(
        f"/api/v1/form/{form_id}/subform/merge",
        headers={"Authorization": f"Bearer {client_token}"}
    )
    assert merge_resp.status_code == 200
    
    # 8. 双方同意完成 (processing → end)
    # Client 调用
    end_resp1 = client.put(f"/api/v1/form/{form_id}/status", json={
        "status": "end"
    }, headers={"Authorization": f"Bearer {client_token}"})
    form = end_resp1.json()["data"]
    assert form["approval_flags"] == 2  # 仅 client
    
    # Developer 调用
    end_resp2 = client.put(f"/api/v1/form/{form_id}/status", json={
        "status": "end"
    }, headers={"Authorization": f"Bearer {developer_token}"})
    form = end_resp2.json()["data"]
    assert form["status"] == "end"  # 自动转换
    assert form["approval_flags"] == 0  # 重置
```

---

### 场景 3: 权限检查

```python
# 验证权限隔离和 403 错误

def test_permission_isolation(client_token, other_client_token, developer_token):
    # 创建表单（属于 client）
    resp = client.post("/api/v1/form", json={...})
    form_id = resp.json()["data"]["id"]
    
    # 其他 client 无法查看
    view_resp = client.get(f"/api/v1/form/{form_id}", 
        headers={"Authorization": f"Bearer {other_client_token}"})
    assert view_resp.status_code == 403
    
    # 其他 client 无法编辑
    edit_resp = client.put(f"/api/v1/form/{form_id}", json={
        "title": "Hacked"
    }, headers={"Authorization": f"Bearer {other_client_token}"})
    assert edit_resp.status_code == 403
    
    # Developer 未接单时无法编辑
    dev_edit_resp = client.put(f"/api/v1/form/{form_id}", json={
        "title": "Edited"
    }, headers={"Authorization": f"Bearer {developer_token}"})
    assert dev_edit_resp.status_code == 403
```

---

## 测试数据与 Fixtures

### conftest.py

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.repositories import users as user_repo
from app.repositories import licenses as license_repo
from app.utils import create_access_token

# 使用内存 SQLite 用于测试
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine

@pytest.fixture(scope="function")
def db(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    def override_get_db():
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.rollback()  # 每个测试后回滚

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_license_key(db):
    """创建有效的测试 License"""
    from datetime import datetime, timedelta
    license = license_repo.create_license(
        db,
        license_key="TEST_LICENSE_12345",
        role="client",
        expires_at=datetime.now() + timedelta(days=365)
    )
    return license.license_key

@pytest.fixture
def client_user(db, test_license_key):
    """创建测试 Client 用户"""
    user = user_repo.create(
        db,
        email="client@example.com",
        password="Password123",
        display_name="Test Client"
    )
    license_repo.activate(db, test_license_key, user)
    return user

@pytest.fixture
def developer_user(db):
    """创建测试 Developer 用户"""
    license = license_repo.create_license(
        db,
        license_key="DEV_LICENSE_12345",
        role="developer"
    )
    user = user_repo.create(
        db,
        email="dev@example.com",
        password="Password123",
        display_name="Test Developer"
    )
    license_repo.activate(db, license.license_key, user)
    return user

@pytest.fixture
def client_token(client_user):
    """生成 Client Token"""
    return create_access_token({"sub": client_user.id, "role": client_user.role})

@pytest.fixture
def developer_token(developer_user):
    """生成 Developer Token"""
    return create_access_token({"sub": developer_user.id, "role": developer_user.role})
```

---

## 运行测试

### 命令

```bash
# 运行所有测试
poetry run pytest

# 运行指定文件
poetry run pytest tests/integration/test_auth_flow.py

# 运行指定测试函数
poetry run pytest tests/integration/test_auth_flow.py::test_complete_auth_flow -v

# 运行带覆盖率报告
poetry run pytest --cov=app --cov-report=html --cov-report=term-missing

# 运行并生成 JUnit XML（CI/CD）
poetry run pytest --junit-xml=test-results.xml

# 并行运行（需安装 pytest-xdist）
poetry run pytest -n auto
```

### GitHub Actions 集成（示例）

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install poetry
      - run: poetry install --with dev
      - run: poetry run pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## 覆盖率目标

| 模块 | 目标 | 优先级 |
|------|------|--------|
| app/repositories/ | 80%+ | P0 |
| app/services/ | 80%+ | P0 |
| app/api/v1/ | 70%+ | P1 |
| app/utils/ | 85%+ | P1 |
| app/models/ | 30%（主要验证关系） | P2 |
| app/schemas/ | 50%（Pydantic 自动验证） | P2 |

### 计算覆盖率

```bash
poetry run pytest --cov=app --cov-report=term-missing

# 输出示例
# Name                                  Stmts   Miss  Cover   Missing
# app/repositories/forms.py              180     15    92%     142-155
# app/services/permissions.py            120      8    93%     78-82
# ...
# TOTAL                                 1500    150    90%
```

---

## 检查清单

在编写测试时，确保涵盖：

- [ ] **正常流程** (Happy Path): 所有参数有效
- [ ] **参数验证** (Validation): 缺失必需字段、类型错误等
- [ ] **权限检查** (Authorization): 403 错误
- [ ] **资源存在性** (Not Found): 404 错误
- [ ] **业务逻辑** (Business Logic): 状态转换、约束检查
- [ ] **并发** (Concurrency): 竞争条件（可选）
- [ ] **审计日志** (Audit): 所有写操作都被记录
- [ ] **数据库事务** (Transactions): 失败时回滚

---

**测试框架准备完毕，可开始编写测试用例！**
