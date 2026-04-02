---
name: utils-toolkit
description: |
  后端工具类使用指南。包含 StringUtil、ResponseUtil、PwdUtil、ExcelUtil、LogUtil、PageUtil 等核心工具类。

  触发场景：
  - 字符串处理
  - HTTP 响应封装
  - 密码加密验证
  - Excel 导入导出
  - 日志记录
  - 分页处理
  - 模板引擎
  - 时间格式化
  - 文件上传
  - 消息处理
  - 动态导入
  - 代码生成

  触发词：工具类、StringUtil、ResponseUtil、PwdUtil、ExcelUtil、LogUtil、PageUtil、TemplateUtil、TimeFormatUtil、UploadUtil、MessageUtil、ImportUtil、GenUtil、字符串处理、响应封装、密码加密、Excel、日志、分页、模板、时间格式化、文件上传

  注意：
  - 对象转换使用 Pydantic 的 model_dump() 方法
  - 本项目是 FastAPI + Python 后端项目
---

# 后端工具类大全

> 本项目是 CodeAI 后端框架（FastAPI + Python），本文档专注于 Python 后端工具类。

## 快速索引

| 功能 | 工具类 | 模块路径 | 常用方法 |
|------|--------|----------|---------|
| **字符串处理** | `StringUtil` | `utils.string_util` | `is_blank()`, `convert_to_camel_case()` |
| **HTTP 响应** | `ResponseUtil` | `utils.response_util` | `success()`, `failure()`, `error()` |
| **密码加密** | `PwdUtil` | `utils.pwd_util` | `verify_password()`, `get_password_hash()` |
| **Excel 操作** | `ExcelUtil` | `utils.excel_util` | `export_list2excel()`, `get_excel_template()` |
| **日志管理** | `Logger` | `utils.log_util` | `info()`, `error()`, `warning()` |
| **分页处理** | `PageUtil` | `utils.page_util` | `paginate()`, `get_page_obj()` |
| **模板引擎** | `TemplateUtils` | `utils.template_util` | `prepare_context()`, `get_template_list()` |
| **时间格式化** | `TimeFormatUtil` | `utils.time_format_util` | `format_time()`, `format_time_dict()` |
| **文件上传** | `UploadUtil` | `utils.upload_util` | `check_file_extension()`, `generate_file()` |
| **消息处理** | `message_service` | `utils.message_util` | `message_service()` |
| **动态导入** | `ImportUtil` | `utils.import_util` | `find_models()`, `is_valid_model()` |
| **代码生成** | `GenUtils` | `utils.gen_util` | `init_table()`, `init_column_field()` |

---

## 1. 字符串处理 - StringUtil

```python
from utils.string_util import StringUtil

# 判空
StringUtil.is_blank("  ")  # True (空字符串或全空格)
StringUtil.is_empty(None)   # True (None或空字符串)
StringUtil.is_not_empty("test")  # True

# HTTP链接判断
StringUtil.is_http("https://example.com")  # True

# 大小写忽略比较
StringUtil.contains_ignore_case("Hello World", "world")  # True
StringUtil.equals_ignore_case("TEST", "test")  # True

# 前缀判断
StringUtil.startswith_case("api/user", "api/")  # True

# 驼峰转换
StringUtil.convert_to_camel_case("user_name")  # "UserName"

# 字典键忽略大小写获取值
mapping = {"USER_ID": "123", "NAME": "测试"}
StringUtil.get_mapping_value_by_key_ignore_case(mapping, "user_id")  # "123"
```

---

## 2. HTTP 响应 - ResponseUtil

```python
from utils.response_util import ResponseUtil
from pydantic import BaseModel

# 成功响应
@router.get("/list")
async def get_list():
    data = ["item1", "item2"]
    return ResponseUtil.success(msg="获取成功", data=data)

# 失败响应
@router.post("/add")
async def add_item():
    return ResponseUtil.failure(msg="添加失败")

# 未认证响应
@router.get("/protected")
async def protected_resource():
    return ResponseUtil.unauthorized(msg="登录信息已过期")

# 未授权响应
@router.get("/admin")
async def admin_resource():
    return ResponseUtil.forbidden(msg="无权限访问")

# 错误响应
@router.get("/error")
async def error_example():
    return ResponseUtil.error(msg="接口异常")

# 带 Pydantic 模型的响应
class UserModel(BaseModel):
    id: int
    name: str

@router.get("/user")
async def get_user():
    user = UserModel(id=1, name="测试用户")
    return ResponseUtil.success(model_content=user)
```

---

## 3. 密码加密 - PwdUtil

```python
from utils.pwd_util import PwdUtil

# 密码加密
password = "123456"
hashed_password = PwdUtil.get_password_hash(password)
print(hashed_password)  # $2b$12$...

# 密码验证
is_valid = PwdUtil.verify_password(password, hashed_password)
print(is_valid)  # True

# 登录验证示例
def verify_user(username: str, password: str):
    # 从数据库获取用户
    user = get_user_from_db(username)
    if not user:
        return False
    # 验证密码
    return PwdUtil.verify_password(password, user.hashed_password)
```

---

## 4. Excel 操作 - ExcelUtil

```python
from utils.excel_util import ExcelUtil
from fastapi import Response

# 导出数据到 Excel
@router.get("/export")
async def export_data():
    # 模拟数据
    data = [
        {"id": 1, "name": "测试1", "age": 20},
        {"id": 2, "name": "测试2", "age": 25}
    ]
    # 字段映射（英文键 -> 中文表头）
    mapping = {"id": "ID", "name": "姓名", "age": "年龄"}
    # 生成 Excel 二进制数据
    excel_data = ExcelUtil.export_list2excel(data, mapping)
    # 返回响应
    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=data.xlsx"}
    )

# 生成 Excel 模板
@router.get("/template")
async def get_template():
    # 表头列表
    headers = ["ID", "姓名", "年龄", "状态"]
    # 需要下拉选择的列
    selector_headers = ["状态"]
    # 下拉选项
    options = [{"状态": ["启用", "禁用"]}]
    # 生成模板
    template_data = ExcelUtil.get_excel_template(headers, selector_headers, options)
    # 返回响应
    return Response(
        content=template_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template.xlsx"}
    )
```

---

## 5. 日志管理 - LogUtil

```python
from utils.log_util import logger

# 初始化日志（在应用启动时执行）
# logger 已在模块中自动初始化

# 日志记录
def process_user(user_id: int):
    logger.info(f"开始处理用户: {user_id}")
    try:
        # 业务逻辑
        logger.debug(f"用户 {user_id} 的详细信息")
        logger.info(f"用户 {user_id} 处理成功")
    except Exception as e:
        logger.error(f"处理用户 {user_id} 时出错: {e}")
        raise

# 带上下文的日志
async def handle_request(request):
    logger.info(f"收到请求: {request.method} {request.url}")
    # 处理请求...
```

---

## 6. 分页处理 - PageUtil

```python
from utils.page_util import PageUtil, PageResponseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from module_admin.entity.do.user_do import SysUser

# 内存数据分页
def get_paginated_data():
    data = [f"item{i}" for i in range(100)]
    page_num = 2
    page_size = 10
    result = PageUtil.get_page_obj(data, page_num, page_size)
    print(result.model_dump())

# 数据库查询分页
async def get_user_list(db: AsyncSession, page_num: int, page_size: int):
    query = select(SysUser).where(SysUser.del_flag == "0")
    # 开启分页
    result = await PageUtil.paginate(db, query, page_num, page_size, is_page=True)
    # 不开启分页（返回全部数据）
    # result = await PageUtil.paginate(db, query, page_num, page_size, is_page=False)
    return result

# 分页响应模型示例
class UserPageQuery(BaseModel):
    page_num: int = 1
    page_size: int = 10

@router.get("/list")
async def get_list(
    db: AsyncSession = Depends(get_db),
    query: UserPageQuery = Depends()
):
    result = await get_user_list(db, query.page_num, query.page_size)
    return ResponseUtil.success(model_content=result)
```

---

## 7. 模板引擎 - TemplateUtils

```python
from utils.template_util import TemplateInitializer, TemplateUtils
from module_generator.entity.vo.gen_vo import GenTableModel

# 初始化模板引擎
env = TemplateInitializer.init_jinja2()

# 准备模板变量
gen_table = GenTableModel(
    table_name="sys_user",
    class_name="SysUser",
    module_name="admin",
    business_name="user",
    package_name="module_admin",
    tpl_category="crud",
    function_name="用户管理",
    function_author="admin"
)

context = TemplateUtils.prepare_context(gen_table)

# 获取模板列表
templates = TemplateUtils.get_template_list("crud", "element-plus")
print(templates)

# 生成文件名
for template in templates:
    file_name = TemplateUtils.get_file_name(template, gen_table)
    print(f"模板: {template} -> 文件名: {file_name}")

# 渲染模板
template = env.get_template("python/controller.py.jinja2")
content = template.render(**context)
print(content)
```

---

## 8. 时间格式化 - TimeFormatUtil

```python
from utils.time_format_util import TimeFormatUtil, format_datetime_dict_list
from datetime import datetime

# 格式化时间
time_str = "2026-01-24 15:30:00"
dt = datetime.now()

# 格式化字符串时间
formatted1 = TimeFormatUtil.format_time(time_str)
print(formatted1)  # 2026-01-24 15:30:00

# 格式化 datetime 对象
formatted2 = TimeFormatUtil.format_time(dt, format="%Y-%m-%d")
print(formatted2)  # 2026-01-24

# 解析日期
 date_obj = TimeFormatUtil.parse_date(time_str)
print(date_obj)  # 2026-01-24

# 格式化字典中的时间
data = {
    "id": 1,
    "name": "测试",
    "create_time": datetime.now(),
    "update_time": datetime.now()
}
formatted_dict = TimeFormatUtil.format_time_dict(data)
print(formatted_dict)

# 格式化列表中的时间字典
list_data = [
    {"id": 1, "create_time": datetime.now()},
    {"id": 2, "create_time": datetime.now()}
]
formatted_list = format_datetime_dict_list(list_data)
print(formatted_list)
```

---

## 9. 文件上传 - UploadUtil

```python
from utils.upload_util import UploadUtil
from fastapi import UploadFile, File
import os

# 检查文件扩展名
async def check_file(file: UploadFile = File(...)):
    is_valid = UploadUtil.check_file_extension(file)
    if not is_valid:
        return {"error": "文件类型不允许"}
    return {"success": True}

# 生成随机数
random_code = UploadUtil.generate_random_number()
print(random_code)  # 三位随机数，如 "045"

# 检查文件是否存在
file_path = "uploads/test.txt"
exists = UploadUtil.check_file_exists(file_path)
print(exists)

# 生成文件二进制数据
if exists:
    file_data = UploadUtil.generate_file(file_path)
    # 用于 StreamingResponse
    from fastapi.responses import StreamingResponse
    return StreamingResponse(file_data, media_type="text/plain")

# 删除文件
if exists:
    UploadUtil.delete_file(file_path)
    print("文件已删除")
```

---

## 10. 消息处理 - MessageUtil

```python
from utils.message_util import message_service

# 记录短信验证码
def send_verification_code(phone: str):
    import random
    sms_code = str(random.randint(100000, 999999))
    message_service(sms_code)
    # 这里可以集成实际的短信发送服务
    return {"code": sms_code, "message": "验证码已发送"}
```

---

## 11. 动态导入 - ImportUtil

```python
from utils.import_util import ImportUtil
from config.database import Base

# 查找项目根目录
root_path = ImportUtil.find_project_root()
print(f"项目根目录: {root_path}")

# 查找所有有效的 SQLAlchemy 模型
models = ImportUtil.find_models(Base)
print(f"找到 {len(models)} 个有效模型")
for model in models:
    print(f"- {model.__name__} (表: {model.__tablename__})")

# 验证模型
from module_admin.entity.do.user_do import SysUser
is_valid = ImportUtil.is_valid_model(SysUser, Base)
print(f"SysUser 是有效模型: {is_valid}")
```

---

## 12. 代码生成 - GenUtils

```python
from utils.gen_util import GenUtils
from module_generator.entity.vo.gen_vo import GenTableModel, GenTableColumnModel

# 初始化表信息
gen_table = GenTableModel(
    table_name="sys_test",
    table_comment="测试表",
    table_id=1
)
GenUtils.init_table(gen_table, "admin")
print(f"类名: {gen_table.class_name}")
print(f"模块名: {gen_table.module_name}")
print(f"业务名: {gen_table.business_name}")

# 初始化列信息
column = GenTableColumnModel(
    column_name="user_name",
    column_type="varchar(50)",
    column_comment="用户名",
    pk=False
)
GenUtils.init_column_field(column, gen_table)
print(f"字段名: {column.column_name}")
print(f"Python字段: {column.python_field}")
print(f"Python类型: {column.python_type}")
print(f"HTML类型: {column.html_type}")

# 其他工具方法
class_name = GenUtils.convert_class_name("sys_user")
print(f"表名转类名: {class_name}")

camel_case = GenUtils.to_camel_case("user_name")
print(f"下划线转驼峰: {camel_case}")
```

---

## 工具类选择速查

| 需求 | 推荐工具 | 说明 |
|------|---------|------|
| 字符串判空 | `StringUtil.is_blank()` | 检查字符串是否为空白 |
| 字符串转换 | `StringUtil.convert_to_camel_case()` | 下划线转驼峰命名 |
| HTTP 响应 | `ResponseUtil.success()` | 统一成功响应格式 |
| 密码加密 | `PwdUtil.get_password_hash()` | 使用 bcrypt 加密 |
| 密码验证 | `PwdUtil.verify_password()` | 验证密码是否正确 |
| Excel 导出 | `ExcelUtil.export_list2excel()` | 导出数据到 Excel |
| 日志记录 | `logger.info()` | 带 trace_id 的日志 |
| 数据库分页 | `PageUtil.paginate()` | 异步数据库分页查询 |
| 内存分页 | `PageUtil.get_page_obj()` | 内存数据分页 |
| 时间格式化 | `TimeFormatUtil.format_time()` | 格式化时间字符串 |
| 文件上传 | `UploadUtil.check_file_extension()` | 检查文件类型 |
| 代码生成 | `GenUtils.init_table()` | 初始化代码生成配置 |
| 模型查找 | `ImportUtil.find_models()` | 查找所有 SQLAlchemy 模型 |

---

## 最佳实践

### 1. 响应处理
```python
# ✅ 推荐：使用 ResponseUtil
return ResponseUtil.success(data=result, msg="操作成功")

# ❌ 不推荐：直接返回字典
return {"code": 200, "msg": "成功", "data": result}
```

### 2. 密码处理
```python
# ✅ 推荐：使用 PwdUtil
hashed_password = PwdUtil.get_password_hash(password)

# ❌ 不推荐：明文存储密码
user.password = password  # 禁止！
```

### 3. 分页查询
```python
# ✅ 推荐：使用 PageUtil.paginate()
result = await PageUtil.paginate(db, query, page_num, page_size, is_page=True)

# ❌ 不推荐：手动分页
items = await db.execute(query).scalars().all()
start = (page_num - 1) * page_size
end = page_num * page_size
paginated = items[start:end]  # 效率低
```

### 4. 日志记录
```python
# ✅ 推荐：使用 logger
logger.info(f"用户 {user_id} 登录成功")
logger.error(f"操作失败: {e}")

# ❌ 不推荐：使用 print
print(f"用户 {user_id} 登录成功")  # 生产环境不推荐
```

### 5. 字符串处理
```python
# ✅ 推荐：使用 StringUtil
if StringUtil.is_blank(user_input):
    return ResponseUtil.failure(msg="输入不能为空")

# ❌ 不推荐：手动判断
if not user_input or user_input.strip() == "":
    return {"code": 400, "msg": "输入不能为空"}
```

---

## 项目结构

工具类模块位于 `utils/` 目录下：

```
utils/
├── string_util.py        # 字符串处理工具
├── response_util.py      # HTTP 响应工具
├── pwd_util.py           # 密码加密工具
├── excel_util.py         # Excel 操作工具
├── log_util.py           # 日志管理工具
├── page_util.py          # 分页处理工具
├── template_util.py      # 模板引擎工具
├── time_format_util.py   # 时间格式化工具
├── upload_util.py        # 文件上传工具
├── message_util.py       # 消息处理工具
├── import_util.py        # 动态导入工具
├── gen_util.py           # 代码生成工具
└── common_util.py        # 通用工具
```

---

## 依赖说明

| 工具类 | 核心依赖 | 用途 |
|--------|----------|------|
| StringUtil | 标准库 | 字符串处理 |
| ResponseUtil | FastAPI | HTTP 响应处理 |
| PwdUtil | passlib | 密码加密 |
| ExcelUtil | pandas, openpyxl | Excel 操作 |
| LogUtil | loguru | 日志管理 |
| PageUtil | SQLAlchemy, pydantic | 数据库分页 |
| TemplateUtil | jinja2 | 模板引擎 |
| TimeFormatUtil | dateutil | 时间处理 |
| UploadUtil | FastAPI | 文件上传 |
| MessageUtil | log_util | 消息处理 |
| ImportUtil | SQLAlchemy | 动态导入 |
| GenUtil | 标准库 | 代码生成 |

---

## 总结

本项目提供了丰富的 Python 工具类，涵盖了后端开发中的常见需求：

- **基础工具**：字符串处理、时间格式化、密码加密
- **Web 相关**：HTTP 响应封装、文件上传
- **数据处理**：Excel 操作、分页查询
- **开发辅助**：日志管理、模板引擎、代码生成
- **动态功能**：动态导入、消息处理

所有工具类均采用 `@classmethod` 装饰器实现静态方法，使用方式统一，便于在项目中各处调用。

使用这些工具类可以：
1. 提高代码复用性
2. 保持代码风格一致
3. 减少重复代码
4. 提高开发效率
5. 确保功能的正确性和安全性

建议在开发过程中优先使用这些工具类，而不是重复实现相同的功能。
