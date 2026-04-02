---
name: test-development
short_description: 测试开发技能
long_description: |
  测试开发技能，编写单元测试、集成测试、API测试。基于 pytest + FastAPI TestClient 标准测试框架。

  触发场景：
  - 编写单元测试（工具类、枚举、模型）
  - 编写集成测试（Service、API、数据库）
  - Mock 外部依赖
  - 参数化测试
  - 测试数据构造
  - 测试覆盖率提升

  触发词：测试、单元测试、集成测试、pytest、unittest、mock、断言、test、测试用例、测试覆盖率、测试数据、TestClient、mock、patch、assert、测试类、测试方法、参数化测试、fixture、setup、teardown

  注意：本项目使用标准的 pytest + FastAPI TestClient，没有自定义测试基类。
---

# 测试开发规范

> **核心原则**：本项目使用标准的 pytest + FastAPI TestClient，根据测试场景选择是否启动完整应用！

## 测试分层策略

| 层次 | 测试类型 | 是否启动应用 | 特点 | 执行速度 |
|------|---------|-------------|------|----------|
| **单元测试** | 工具类/枚举/模型 | ❌ 否 | 纯 pytest，无依赖注入 | < 1s |
| **集成测试** | Service/API/数据库 | ✅ 是 | 使用 TestClient，完整请求链路 | 1-3s |

## 测试文件位置

| 类型 | 位置 | 示例 |
|------|------|------|
| 测试类 | `tests/` | `tests/test_utils.py` |
| 测试资源 | `tests/resources/` | 测试配置文件、测试数据等 |

## 核心依赖

| 依赖 | 用途 | 安装命令 |
|------|------|----------|
| **pytest** | 测试框架 | `pip install pytest` |
| **pytest-asyncio** | 异步测试支持 | `pip install pytest-asyncio` |
| **httpx** | HTTP 客户端（TestClient 依赖） | `pip install httpx` |
| **python-mock** | Mock 框架 | `pip install mock` |
| **pytest-cov** | 测试覆盖率 | `pip install pytest-cov` |

---

## 1. 单元测试（纯 pytest）

**适用场景：** 工具类、枚举类、模型、算法逻辑（无需应用容器）

**特点：** 不使用 TestClient，执行速度快，适合纯逻辑测试。

```python
import pytest
from utils.string_util import StringUtil
from module_admin.entity.enums import UserType


class TestStringUtils:
    """
    字符串工具类测试
    """

    def test_is_blank(self):
        """
        测试 is_blank 方法
        """
        assert StringUtil.is_blank(None) is True
        assert StringUtil.is_blank('') is True
        assert StringUtil.is_blank('   ') is True
        assert StringUtil.is_blank('test') is False

    def test_is_not_blank(self):
        """
        测试 is_not_blank 方法
        """
        assert StringUtil.is_not_blank('test') is True
        assert StringUtil.is_not_blank('') is False


class TestUserType:
    """
    用户类型枚举测试
    """

    def test_user_type_enum(self):
        """
        测试用户类型枚举
        """
        assert UserType.ADMIN.value == 'admin'
        assert UserType.USER.value == 'user'
        assert UserType.GUEST.value == 'guest'
```

**常用断言方法：**

```python
# 基本断言
assert True
assert 1 == 1
assert 'test' != 'test1'

# 类型断言
assert isinstance('test', str)
assert not isinstance(1, str)

# 集合断言
assert 1 in [1, 2, 3]
assert 'a' not in {'b': 1}

# 异常断言
with pytest.raises(ValueError):
    raise ValueError('测试异常')

# 近似值断言
assert abs(0.1 + 0.2 - 0.3) < 1e-9
```

---

## 2. 集成测试（TestClient）

**适用场景：** 需要应用容器的测试（Service、API、数据库）

**特点：** 使用 TestClient，启动完整应用，支持 HTTP 请求测试。

```python
import pytest
from fastapi.testclient import TestClient
from server import app


client = TestClient(app)


class TestApiIntegration:
    """
    API 集成测试
    """

    def test_root(self):
        """
        测试根路径
        """
        response = client.get('/')
        assert response.status_code == 200
        assert 'message' in response.json()

    def test_login(self):
        """
        测试登录接口
        """
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        assert response.status_code == 200
        assert 'token' in response.json()

    def test_protected_route(self):
        """
        测试受保护的路由
        """
        # 先登录获取 token
        login_response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        token = login_response.json()['token']

        # 使用 token 访问受保护的路由
        response = client.get('/user/getInfo', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 200
        assert 'user' in response.json()
```

---

## 3. Service 测试（pytest + 数据库）

**适用场景：** Service 层业务逻辑测试，需要数据库操作

**特点：** 使用 pytest + 数据库连接，可选择使用事务回滚避免污染数据库。

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import AsyncSessionLocal
from module_admin.service.user_service import UserService
from module_admin.entity.vo.user_vo import AddUserModel


class TestUserService:
    """
    用户服务测试
    """

    async def test_add_user(self):
        """
        测试添加用户
        """
        async with AsyncSessionLocal() as session:
            # 准备测试数据
            user_data = AddUserModel(
                userName='test_user',
                nickName='测试用户',
                password='123456',
                deptId=1
            )

            # 执行添加操作
            result = await UserService.add_user_services(session, user_data)

            # 验证结果
            assert result.is_success is True
            assert result.message == '新增成功'

    async def test_get_user_by_id(self):
        """
        测试根据 ID 获取用户
        """
        async with AsyncSessionLocal() as session:
            # 假设数据库中已有 ID 为 1 的用户
            user = await UserService.user_detail_services(session, 1)

            # 验证结果
            assert user is not None
            assert user.user_id == 1
```

**Mock 外部依赖示例：**

```python
import pytest
from unittest.mock import patch, MagicMock
from module_admin.service.user_service import UserService


class TestUserServiceWithMock:
    """
    使用 Mock 的用户服务测试
    """

    async def test_add_user_with_mock(self):
        """
        使用 Mock 测试添加用户
        """
        mock_session = MagicMock()
        user_data = AddUserModel(
            userName='test_user',
            nickName='测试用户',
            password='123456',
            deptId=1
        )

        # Mock 数据库操作
        with patch('module_admin.service.user_service.UserDao.add_user_dao') as mock_add:
            # 设置 Mock 返回值
            mock_add.return_value = MagicMock(user_id=100)

            # 执行添加操作
            result = await UserService.add_user_services(mock_session, user_data)

            # 验证结果
            assert result.is_success is True
            mock_add.assert_called_once()
```

---

## 4. API 测试（TestClient + Mock）

**适用场景：** HTTP 接口测试，完整请求链路

**特点：** 使用 TestClient + Mock，模拟 HTTP 请求，可选择性 Mock 外部依赖。

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from server import app


client = TestClient(app)


class TestUserApi:
    """
    用户 API 测试
    """

    def test_get_user_list(self):
        """
        测试获取用户列表
        """
        # Mock 认证
        with patch('module_admin.service.login_service.LoginService.get_current_user') as mock_current_user:
            # 设置 Mock 返回值
            mock_current_user.return_value = MagicMock(
                user=MagicMock(user_id=1),
                permissions=['system:user:list']
            )

            # 发送请求
            response = client.get('/user/list?page=1&size=10')

            # 验证结果
            assert response.status_code == 200
            assert 'data' in response.json()
            assert 'total' in response.json()

    def test_add_user(self):
        """
        测试添加用户
        """
        # Mock 认证
        with patch('module_admin.service.login_service.LoginService.get_current_user') as mock_current_user:
            mock_current_user.return_value = MagicMock(
                user=MagicMock(user_id=1),
                permissions=['system:user:add']
            )

            # Mock 用户服务
            with patch('module_admin.service.user_service.UserService.add_user_services') as mock_add:
                mock_add.return_value = MagicMock(
                    is_success=True,
                    message='新增成功'
                )

                # 发送请求
                response = client.post('/user/add', json={
                    'userName': 'test_user',
                    'nickName': '测试用户',
                    'password': '123456',
                    'deptId': 1
                })

                # 验证结果
                assert response.status_code == 200
                assert response.json()['message'] == '新增成功'
```

---

## 5. 参数化测试

**适用场景：** 需要用多组数据测试同一个方法

**特点：** 使用 `@pytest.mark.parametrize` 装饰器，提供多组测试数据。

```python
import pytest
from utils.string_util import StringUtil


class TestStringUtilsParametrize:
    """
    字符串工具类参数化测试
    """

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            (None, True),
            ("", True),
            ("   ", True),
            ("test", False),
            ("  test  ", False)
        ]
    )
    def test_is_blank(self, input_str, expected):
        """
        测试 is_blank 方法
        """
        assert StringUtil.is_blank(input_str) == expected

    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("test", True),
            ("  test  ", True),
            (None, False),
            ("", False),
            ("   ", False)
        ]
    )
    def test_is_not_blank(self, input_str, expected):
        """
        测试 is_not_blank 方法
        """
        assert StringUtil.is_not_blank(input_str) == expected
```

**更复杂的参数化测试：**

```python
import pytest
from module_admin.service.user_service import UserService


class TestUserServiceParametrize:
    """
    用户服务参数化测试
    """

    @pytest.mark.parametrize(
        "user_name, password, expected",
        [
            ("admin", "admin123", True),
            ("user", "user123", True),
            ("admin", "wrong_pass", False),
            ("non_existent", "123456", False)
        ]
    )
    async def test_authenticate_user(self, user_name, password, expected):
        """
        测试用户认证
        """
        # 这里需要根据实际实现调整
        # 示例代码，实际实现可能不同
        result = await UserService.authenticate_user(user_name, password)
        assert (result is not None) == expected
```

---

## 6. 测试 Fixture

**适用场景：** 需要在测试前准备数据，测试后清理数据

**特点：** 使用 `@pytest.fixture` 装饰器，提供测试依赖。

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import AsyncSessionLocal


@pytest.fixture
async def db_session():
    """
    数据库会话 fixture
    """
    async with AsyncSessionLocal() as session:
        yield session
        # 测试结束后可以在这里添加清理逻辑


@pytest.fixture
async def test_user(db_session):
    """
    测试用户 fixture
    """
    # 这里可以添加创建测试用户的逻辑
    # 示例代码
    from module_admin.service.user_service import UserService
    from module_admin.entity.vo.user_vo import AddUserModel
    
    user_data = AddUserModel(
        userName='test_fixture_user',
        nickName='测试Fixture用户',
        password='123456',
        deptId=1
    )
    
    result = await UserService.add_user_services(db_session, user_data)
    # 假设返回的是用户对象或包含用户ID的对象
    # 这里需要根据实际实现调整
    return result


class TestUserServiceWithFixture:
    """
    使用 fixture 的用户服务测试
    """

    async def test_get_user(self, db_session, test_user):
        """
        测试获取用户
        """
        from module_admin.service.user_service import UserService
        
        # 假设 test_user 包含用户 ID
        user_id = test_user.user_id
        user = await UserService.user_detail_services(db_session, user_id)
        
        assert user is not None
        assert user.user_name == 'test_fixture_user'
```

---

## 7. 异步测试

**适用场景：** 测试异步方法

**特点：** 使用 `pytest-asyncio` 插件，支持异步测试方法。

```python
import pytest
from unittest.mock import MagicMock
from module_admin.service.user_service import UserService


class TestAsyncUserService:
    """
    异步用户服务测试
    """

    @pytest.mark.asyncio
    async def test_async_method(self):
        """
        测试异步方法
        """
        # 模拟异步会话
        mock_session = MagicMock()
        
        # 执行异步方法
        result = await UserService.some_async_method(mock_session, 1)
        
        # 验证结果
        assert result is not None

    @pytest.mark.asyncio
    async def test_async_with_timeout(self):
        """
        测试带超时的异步方法
        """
        import asyncio
        
        # 模拟一个会超时的方法
        async def slow_method():
            await asyncio.sleep(2)
            return "done"
        
        # 测试超时
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_method(), timeout=1)
```

---

## 8. 测试标签和分组

**适用场景：** 需要对测试进行分组，选择性运行某些测试

**特点：** 使用 `@pytest.mark` 装饰器标记测试，可以按标记过滤执行。

```python
import pytest


class TestTaggedTests:
    """
    带标签的测试
    """

    @pytest.mark.dev
    def test_dev_only(self):
        """
        仅开发环境运行的测试
        """
        assert True

    @pytest.mark.prod
    def test_prod_only(self):
        """
        仅生产环境运行的测试
        """
        assert True

    @pytest.mark.slow
    def test_slow_test(self):
        """
        慢测试
        """
        import time
        time.sleep(2)
        assert True
```

**运行指定标签的测试：**

```bash
# 运行带 dev 标签的测试
pytest -m dev

# 运行不带 slow 标签的测试
pytest -k "not slow"

# 运行带 dev 或 prod 标签的测试
pytest -m "dev or prod"
```

---

## 9. 异常测试

**适用场景：** 测试方法是否正确抛出异常

```python
import pytest
from module_admin.service.user_service import UserService
from exceptions.exception import ServiceException


class TestExceptionHandling:
    """
    异常处理测试
    """

    def test_invalid_input(self):
        """
        测试无效输入
        """
        with pytest.raises(ValueError):
            # 这里应该调用一个会抛出 ValueError 的方法
            raise ValueError("无效输入")

    async def test_service_exception(self):
        """
        测试服务异常
        """
        from unittest.mock import MagicMock
        
        mock_session = MagicMock()
        
        # 假设 UserService 的某个方法会抛出 ServiceException
        from module_admin.entity.vo.user_vo import AddUserModel
        user_data = AddUserModel(
            userName='',  # 空用户名，应该触发异常
            nickName='测试用户',
            password='123456',
            deptId=1
        )
        
        with pytest.raises(ServiceException) as excinfo:
            await UserService.add_user_services(mock_session, user_data)
        
        assert "用户名不能为空" in str(excinfo.value)
```

---

## 10. 测试覆盖率

**适用场景：** 检查测试覆盖情况

**特点：** 使用 `pytest-cov` 插件，生成测试覆盖率报告。

**安装：**

```bash
pip install pytest-cov
```

**运行测试并生成覆盖率报告：**

```bash
# 运行所有测试并生成覆盖率报告
pytest --cov=module_admin tests/

# 生成 HTML 格式的覆盖率报告
pytest --cov=module_admin --cov-report=html tests/

# 生成 XML 格式的覆盖率报告（用于 CI/CD）
pytest --cov=module_admin --cov-report=xml tests/
```

**覆盖率报告解读：**

| 指标 | 说明 | 目标值 |
|------|------|--------|
| **语句覆盖率** | 执行了多少代码语句 | ≥ 80% |
| **分支覆盖率** | 执行了多少代码分支 | ≥ 70% |
| **函数覆盖率** | 执行了多少函数 | ≥ 85% |
| **行覆盖率** | 执行了多少代码行 | ≥ 80% |

---

## 开发检查清单

### 测试文件规范

- [ ] **测试文件命名**：`test_{模块名}.py`（如 `test_utils.py`、`test_user_service.py`）
- [ ] **测试文件位置**：`tests/` 目录下，目录结构与源码一致
- [ ] **测试类命名**：`Test{被测试类名}`（如 `TestStringUtils`、`TestUserService`）
- [ ] **测试方法命名**：`test_{功能}`（如 `test_is_blank`、`test_add_user`）
- [ ] **添加文档字符串**：为测试类和方法添加中文描述

### 测试类型选择

- [ ] **纯单元测试**：不使用 TestClient，适合工具类/枚举/模型
- [ ] **集成测试**：使用 TestClient，适合 Service/API/数据库
- [ ] **数据库测试**：使用异步会话，注意事务管理
- [ ] **API 测试**：使用 TestClient，模拟 HTTP 请求

### 断言规范

- [ ] **使用标准断言**：`assert` 语句
- [ ] **异常断言**：`with pytest.raises(Exception):`
- [ ] **近似值断言**：`assert abs(a - b) < 1e-9`
- [ ] **详细断言消息**：`assert condition, "断言失败时的消息"`

### Mock 规范

- [ ] **使用 unittest.mock**：`from unittest.mock import patch, MagicMock`
- [ ] **Mock 外部依赖**：避免测试依赖外部服务
- [ ] **验证调用**：`mock.assert_called_once()`、`mock.assert_called_with()`
- [ ] **Mock 上下文管理**：使用 `with patch(...)` 确保 Mock 正确清理

### 测试数据规范

- [ ] **使用测试数据**：避免硬编码
- [ ] **清理测试数据**：测试结束后清理生成的数据
- [ ] **使用 fixture**：复用测试数据和环境准备
- [ ] **参数化测试**：使用多组数据测试同一个方法

---

## 常见错误

| 错误写法 | 正确写法 | 原因 |
|---------|---------|------|
| 测试类在 `src/` 目录 | 测试类在 `tests/` 目录 | 测试代码不应打包到生产环境 |
| `def test()` | `def test_specific_function()` | 测试方法名应描述测试功能 |
| 缺少文档字符串 | 添加中文文档字符串 | 提高测试可读性和可维护性 |
| 直接测试私有方法 | 通过公共方法间接测试 | 私有方法是实现细节，不应直接测试 |
| 测试方法相互依赖 | 每个测试方法独立 | 测试应独立可并行执行 |
| 硬编码测试数据 | 使用变量或常量 | 提高可维护性 |
| 不使用 Mock | 适当使用 Mock 外部依赖 | 减少测试依赖，提高执行速度 |
| 不检查测试覆盖率 | 定期检查测试覆盖率 | 确保测试覆盖关键代码路径 |

---

## 运行测试

### 基本命令

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest tests/test_utils.py

# 运行指定测试类
pytest tests/test_user_service.py::TestUserService

# 运行指定测试方法
pytest tests/test_user_service.py::TestUserService::test_add_user

# 运行带指定标签的测试
pytest -m dev

# 运行测试并生成覆盖率报告
pytest --cov=module_admin tests/
```

### IDE 中运行

**PyCharm：**
1. 右键 `tests/` 目录 → Run 'pytest in tests'
2. 右键测试文件 → Run 'test_file_name'
3. 右键测试方法 → Run 'test_method_name'

**VS Code：**
1. 安装 Python 扩展
2. 打开测试文件
3. 点击测试方法旁边的运行按钮
4. 或使用命令面板 → Python: Run All Tests

---

## FAQ

### Q1: 什么时候使用 TestClient？

**A:**
- **不使用 TestClient**：工具类、枚举、模型（纯逻辑测试，不需要应用容器）
- **使用 TestClient**：API、Service（需要依赖注入和完整请求链路）

### Q2: 测试会污染数据库吗？

**A:** 这取决于测试实现。可以：
- 使用测试数据库
- 在测试结束后手动清理数据
- 使用事务管理，测试结束后回滚事务

### Q3: 如何测试私有方法？

**A:**
- 不要直接测试私有方法
- 通过公共方法间接测试
- 如果私有方法太复杂，考虑提取为独立类

### Q4: Mock 和真实测试如何选择？

**A:**
- **单元测试**: 优先 Mock 外部依赖（快速、隔离）
- **集成测试**: 使用真实依赖（准确、完整）
- **平衡**: 既要有单元测试（快），也要有集成测试（准确）

### Q5: 如何测试异步代码？

**A:**
- 安装 `pytest-asyncio` 插件
- 使用 `@pytest.mark.asyncio` 装饰器标记异步测试方法
- 使用 `await` 调用异步方法

### Q6: 如何跳过测试执行？

**A:**
- **单个测试**：使用 `@pytest.mark.skip(reason="跳过原因")` 装饰器
- **条件跳过**：使用 `@pytest.mark.skipif(condition, reason="跳过原因")` 装饰器
- **运行时跳过**：在测试方法中使用 `pytest.skip("跳过原因")`

### Q7: 如何设置测试环境变量？

**A:**
- 使用 `.env.test` 文件
- 在测试前设置环境变量：`import os; os.environ["TEST_VAR"] = "value"`
- 使用 pytest 的 `monkeypatch` fixture：`monkeypatch.setenv("TEST_VAR", "value")`

### Q8: 如何测试文件上传？

**A:**
- 使用 `TestClient` 的 `files` 参数
- 示例：
  ```python
  response = client.post("/upload", files={
      "file": ("test.txt", b"test content")
  })
  ```

---

## 测试示例

### 1. 工具类测试

```python
# tests/test_utils.py
import pytest
from utils.string_util import StringUtil
from utils.pwd_util import PwdUtil


class TestStringUtils:
    """
    字符串工具类测试
    """

    def test_is_blank(self):
        """
        测试 is_blank 方法
        """
        assert StringUtil.is_blank(None) is True
        assert StringUtil.is_blank('') is True
        assert StringUtil.is_blank('   ') is True
        assert StringUtil.is_blank('test') is False

    def test_is_not_blank(self):
        """
        测试 is_not_blank 方法
        """
        assert StringUtil.is_not_blank('test') is True
        assert StringUtil.is_not_blank('') is False


class TestPwdUtil:
    """
    密码工具类测试
    """

    def test_password_hash(self):
        """
        测试密码加密
        """
        password = "test123"
        hashed = PwdUtil.get_password_hash(password)
        assert hashed != password
        assert PwdUtil.verify_password(password, hashed) is True
        assert PwdUtil.verify_password("wrong", hashed) is False
```

### 2. API 测试

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from server import app


client = TestClient(app)


class TestAuthApi:
    """
    认证 API 测试
    """

    def test_login_success(self):
        """
        测试登录成功
        """
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        })
        assert response.status_code == 200
        assert 'token' in response.json()

    def test_login_failure(self):
        """
        测试登录失败
        """
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'wrong_password'
        })
        assert response.status_code == 401
        assert 'detail' in response.json()


class TestUserApi:
    """
    用户 API 测试
    """

    def test_get_user_list(self):
        """
        测试获取用户列表
        """
        # Mock 认证
        with patch('module_admin.service.login_service.LoginService.get_current_user') as mock_current_user:
            mock_current_user.return_value = MagicMock(
                user=MagicMock(user_id=1),
                permissions=['system:user:list']
            )

            response = client.get('/user/list?page=1&size=10')
            assert response.status_code == 200
            assert 'data' in response.json()
```

### 3. 数据库测试

```python
# tests/test_database.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import AsyncSessionLocal
from module_admin.service.user_service import UserService
from module_admin.entity.vo.user_vo import AddUserModel


@pytest.mark.asyncio
async def test_database_operation():
    """
    测试数据库操作
    """
    async with AsyncSessionLocal() as session:
        # 添加用户
        user_data = AddUserModel(
            userName='test_db_user',
            nickName='测试数据库用户',
            password='123456',
            deptId=1
        )
        
        result = await UserService.add_user_services(session, user_data)
        assert result.is_success is True
        
        # 这里可以添加更多数据库操作测试
        # 注意：测试结束后数据会保留在数据库中
        # 实际测试中应该考虑清理测试数据
```

---

## 总结

测试是保证代码质量的重要手段，本项目推荐使用：

1. **pytest**：Python 标准测试框架
2. **FastAPI TestClient**：API 测试工具
3. **unittest.mock**：Mock 外部依赖
4. **pytest-asyncio**：异步测试支持
5. **pytest-cov**：测试覆盖率分析

通过编写高质量的测试，可以：
- 提高代码质量和可靠性
- 减少 bug 和回归问题
- 便于代码重构和维护
- 提供代码文档和使用示例

希望本指南能帮助你编写更好的测试代码！
