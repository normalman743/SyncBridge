# 状态机增强更新日志

**分支**: `fix/state-machine-enhancement`  
**提交**: d1cb0ce

## 实施的功能

### 1. 扩展 Developer 状态转换权限
- **文件**: [app/api/v1/forms.py](app/api/v1/forms.py#L110-L145)
- **更改**: 修改 `update_status` 端点
- **新增转换**:
  - `processing → rewrite` (developer 请求客户修改)
  - `processing → end` (developer 完成工作)
  - `processing → error` (developer 标记错误)
  - `rewrite → processing` (developer 继续处理)
  - `rewrite → error` (developer 标记错误)
- **权限控制**: developer 必须绑定到表单 (developer_id 匹配)

### 2. 添加 Subform 合并功能
- **Repository 函数**: [app/repositories/forms.py](app/repositories/forms.py#L115-L162)
  - `merge_subform(db, mainform, subform)` - 合并 subform 内容到 mainform
  - 覆写 mainform 的 title, message, budget, expected_time
  - 复制所有 functions 和 nonfunctions，重置 `is_changed=0`
  - 删除 subform，设置 mainform.status = "processing"
  
- **API 端点**: [app/api/v1/forms.py](app/api/v1/forms.py#L112-L139)
  - `POST /form/{mainform_id}/subform/merge` - 完成协商
  - Client 可以合并自己的表单
  - Developer 可以合并已绑定的表单
  - Admin 可以合并任何表单

### 3. 增强 Subform 删除功能
- **文件**: [app/api/v1/forms.py](app/api/v1/forms.py#L83-L97)
- **更改**: `DELETE /form/{id}` 添加 `set_error` 参数
- **行为**:
  - `set_error=false` (默认): mainform.status = "processing"
  - `set_error=true`: mainform.status = "error"
- **用途**: 协商失败时可以将 mainform 标记为 error 状态

### 4. 加强 Subform 创建权限
- **文件**: [app/services/permissions.py](app/services/permissions.py#L96-L106)
- **更改**: `assert_can_create_subform` 增加角色验证
- **新增检查**: Developer 必须已绑定到 mainform (developer_id 匹配)
- **目的**: 防止未授权的 developer 创建 subform

## 状态机完整流程

### Client 流程
1. 创建 mainform (status=preview)
2. 发布 → `preview → available`
3. Developer 接单后协商或等待结果
4. 可以随时设置 `error` 状态

### Developer 流程
1. 接单 → `available → processing` (自动绑定 developer_id)
2. 工作期间可选:
   - 创建 subform 请求修改 → mainform: `processing → rewrite`
   - 直接完成 → `processing → end`
   - 标记错误 → `processing → error`
3. Rewrite 状态下可选:
   - 继续处理 → `rewrite → processing`
   - 标记错误 → `rewrite → error`

### 协商流程 (Subform)
1. Developer 创建 subform → mainform.status = "rewrite"
2. 双方协商修改 subform
3. 达成一致:
   - `POST /form/{mainform_id}/subform/merge` → mainform.status = "processing"
4. 协商失败:
   - `DELETE /form/{subform_id}?set_error=true` → mainform.status = "error"
   - `DELETE /form/{subform_id}` → mainform.status = "processing" (继续工作)

## API 变更摘要

| 端点 | 方法 | 更改 |
|------|------|------|
| `/form/{id}/status` | PUT | 扩展 developer 允许的转换 |
| `/form/{mainform_id}/subform/merge` | POST | **新增** - 合并 subform |
| `/form/{id}` | DELETE | 添加 `set_error` 查询参数 |

## 测试建议

1. **Developer 状态转换**:
   - 测试 processing→end (完成工作)
   - 测试 processing→rewrite (请求修改)
   - 测试 rewrite→processing (继续工作)

2. **Subform 合并**:
   - 验证内容覆写正确
   - 验证 functions/nonfunctions 复制和 is_changed 重置
   - 验证 subform 删除和 mainform 状态更新

3. **权限验证**:
   - 未绑定 developer 不能创建 subform
   - 未绑定 developer 不能更改状态
   - Client 和 developer 都能合并各自的 subform

## 对齐规范

此更新解决了 spec-alignment.md 中记录的以下问题:
- ✅ 状态机转换不完整 (processing→rewrite/end 现在可用)
- ✅ 缺少 merge/reject subform 端点
- ✅ Developer 无法通过状态变更完成工作
- ✅ 协商失败路径不协调

## 下一步

建议的后续改进 (见 spec-alignment.md):
- [ ] 实施 License 激活和验证
- [ ] 添加 Block email 字段
- [ ] 实现 Form detail 聚合端点
- [ ] 标准化 admin 角色权限
- [ ] 添加 Function/NonFunction is_changed 强制更新
