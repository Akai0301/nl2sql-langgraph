---
name: websocket-sse
description: |
  当需要实现实时通信、消息推送、在线状态管理时自动使用此 Skill。

  触发场景：
  - 需要实现服务端向客户端推送消息
  - 需要实现双向实时通信（聊天、协作）
  - 需要管理用户在线状态
  - 需要实现系统通知、订单状态变更等实时推送
  - 需要在多实例部署环境下同步消息

  触发词：WebSocket、SSE、实时推送、消息通知、在线状态、双向通信、Server-Sent Events、实时通信、消息推送
---

# 实时通信开发指南（WebSocket & SSE）

> **适用框架**：CodeAI（FastAPI + Python）

## 概述

本框架提供两种实时通信方案：

| 方案 | 通信方向 | 适用场景 |
|------|---------|---------|
| **WebSocket** | 双向通信 | 聊天、协作编辑、游戏 |
| **SSE** | 服务端→客户端 | 通知推送、状态更新、数据流 |

**共同特性**：
- ✅ FastAPI 原生支持
- ✅ Redis 发布订阅（多实例消息同步）
- ✅ JWT 认证集成
- ✅ 与项目现有架构无缝集成

---

## 技术选型指南

### 何时使用 WebSocket

```
✅ 需要双向通信（客户端也要发送消息）
✅ 即时聊天、协作编辑
✅ 游戏、实时交互应用
✅ 需要低延迟的场景
```

### 何时使用 SSE

```
✅ 只需服务端向客户端推送
✅ 系统通知、订单状态变更
✅ 数据仪表盘实时更新
✅ AI 流式响应（类似 ChatGPT）
✅ 需要简单实现、不需要双向通信
```

### 对比表

| 特性 | WebSocket | SSE |
|------|-----------|-----|
| 通信方向 | 双向 | 单向（服务端→客户端） |
| 协议 | ws:// / wss:// | HTTP |
| 浏览器支持 | 全部现代浏览器 | 全部现代浏览器 |
| 自动重连 | 需自行实现 | 浏览器原生支持 |
| 连接数限制 | 无 | 浏览器限制（6个/域名） |
| 防火墙穿透 | 可能被阻止 | 走 HTTP，穿透性好 |
| 实现复杂度 | 中等 | 简单 |

---

## 一、WebSocket 开发指南

### 1.1 基本实现

FastAPI 原生支持 WebSocket，下面是一个完整的实现示例：

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
from module_admin.service.login_service import LoginService
from module_admin.entity.vo.login_vo import CurrentUserModel

# WebSocket 连接管理器
class ConnectionManager:
    def __init__(self):
        # 存储活动连接：{user_id: websocket}
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

# 创建连接管理器实例
manager = ConnectionManager()

# 创建 WebSocket 路由器
websocketController = APIRouter(prefix='/ws')

@websocketController.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str
):
    # 验证 token
    try:
        current_user = await LoginService.verify_token(token)
        user_id = current_user.user.user_id
        
        # 连接 WebSocket
        await manager.connect(websocket, user_id)
        
        # 发送连接成功消息
        await manager.send_personal_message(
            json.dumps({"type": "CONNECTED", "message": "WebSocket 连接成功"}),
            user_id
        )
        
        # 处理消息
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            # 处理消息（示例：回显消息）
            await manager.send_personal_message(
                json.dumps({"type": "ECHO", "message": data}),
                user_id
            )
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        if 'user_id' in locals():
            manager.disconnect(user_id)
        await websocket.close()
```

### 1.2 集成到项目

将上述代码添加到 `module_admin/controller/` 目录，例如创建 `websocket_controller.py` 文件，然后在 `server.py` 中注册路由：

```python
# server.py 中添加
from module_admin.controller.websocket_controller import websocketController

# 在 controller_list 中添加
controller_list = [
    # ... 其他控制器
    {'router': websocketController, 'tags': ['WebSocket 模块']},
]
```

### 1.3 消息发送工具类

创建 `utils/websocket_util.py` 文件：

```python
from typing import List, Optional
import json
from config.get_redis import RedisUtil

class WebSocketUtil:
    """
    WebSocket 工具类
    """
    
    # Redis 主题
    WEB_SOCKET_TOPIC = "global:websocket"
    
    @classmethod
    async def send_message(cls, user_id: int, message: str, redis=None):
        """
        向指定用户发送消息（当前实例）
        """
        from module_admin.controller.websocket_controller import manager
        await manager.send_personal_message(message, user_id)
    
    @classmethod
    async def broadcast(cls, message: str, redis=None):
        """
        向所有在线用户广播消息（当前实例）
        """
        from module_admin.controller.websocket_controller import manager
        await manager.broadcast(message)
    
    @classmethod
    async def publish_message(cls, user_ids: List[int], message: str):
        """
        向指定用户发送消息（支持多实例）
        """
        # 1. 先发送给当前实例的用户
        from module_admin.controller.websocket_controller import manager
        for user_id in user_ids:
            if user_id in manager.active_connections:
                await manager.send_personal_message(message, user_id)
        
        # 2. 通过 Redis 发布给其他实例
        redis = await RedisUtil.get_redis()
        await redis.publish(
            cls.WEB_SOCKET_TOPIC,
            json.dumps({"user_ids": user_ids, "message": message})
        )
    
    @classmethod
    async def publish_all(cls, message: str):
        """
        向所有实例的所有用户广播消息
        """
        # 1. 先广播给当前实例
        from module_admin.controller.websocket_controller import manager
        await manager.broadcast(message)
        
        # 2. 通过 Redis 广播给其他实例
        redis = await RedisUtil.get_redis()
        await redis.publish(
            cls.WEB_SOCKET_TOPIC,
            json.dumps({"user_ids": [], "message": message})
        )
```

### 1.4 Redis 消息订阅

在 `config/get_redis.py` 中添加 Redis 订阅处理：

```python
import json
from utils.websocket_util import WebSocketUtil

async def handle_websocket_message(message):
    """
    处理从 Redis 接收到的 WebSocket 消息
    """
    try:
        data = json.loads(message['data'])
        user_ids = data.get('user_ids', [])
        message_content = data.get('message', '')
        
        from module_admin.controller.websocket_controller import manager
        
        if not user_ids:
            # 广播消息
            await manager.broadcast(message_content)
        else:
            # 发送给指定用户
            for user_id in user_ids:
                if user_id in manager.active_connections:
                    await manager.send_personal_message(message_content, user_id)
    except Exception as e:
        from utils.log_util import logger
        logger.error(f"处理 WebSocket 消息失败: {e}")

# 在创建 Redis 连接池后添加订阅
async def init_redis_subscription():
    redis = await RedisUtil.get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(
        **{WebSocketUtil.WEB_SOCKET_TOPIC: handle_websocket_message}
    )
    # 启动订阅循环
    import asyncio
    asyncio.create_task(pubsub.run_in_thread(sleep=0.01))
```

### 1.5 业务集成示例

#### 示例1：订单状态变更通知

```python
from utils.websocket_util import WebSocketUtil
import json
from datetime import datetime

class OrderService:
    @classmethod
    async def update_order_status(cls, order_id: int, status: str):
        # 1. 更新订单状态
        # ... 业务逻辑 ...
        
        # 2. 构建消息
        message = json.dumps({
            "type": "ORDER_STATUS",
            "orderId": order_id,
            "status": status,
            "message": f"您的订单状态已更新为：{status}",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 3. 发送给指定用户
        # 假设 order 中有 user_id
        user_id = 1  # 从订单中获取
        await WebSocketUtil.publish_message([user_id], message)
```

#### 示例2：系统广播通知

```python
from utils.websocket_util import WebSocketUtil
import json
from datetime import datetime

class NoticeService:
    @classmethod
    async def broadcast_notice(cls, title: str, content: str):
        # 构建消息
        message = json.dumps({
            "type": "SYSTEM_NOTICE",
            "title": title,
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 广播给所有用户
        await WebSocketUtil.publish_all(message)
```

### 1.6 前端连接示例

```javascript
// 建立 WebSocket 连接
const token = localStorage.getItem('token');
const ws = new WebSocket(`ws://localhost:8000/ws/connect?token=${token}`);

ws.onopen = () => {
    console.log('WebSocket 连接成功');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('收到消息:', data);
    
    // 根据消息类型处理
    switch (data.type) {
        case 'ORDER_STATUS':
            showOrderStatusNotification(data);
            break;
        case 'SYSTEM_NOTICE':
            showSystemNotification(data.title, data.content);
            break;
        case 'CONNECTED':
            console.log('连接成功:', data.message);
            break;
        case 'ECHO':
            console.log('回显消息:', data.message);
            break;
    }
};

ws.onclose = () => {
    console.log('WebSocket 连接关闭');
    // 实现自动重连
    setTimeout(() => {
        console.log('尝试重连...');
        // 重新连接逻辑
    }, 3000);
};

ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

// 发送消息
function sendMessage(message) {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(message);
    }
}
```

---

## 二、SSE 开发指南

### 2.1 基本实现

FastAPI 中实现 SSE（Server-Sent Events）：

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, List, Optional
import asyncio
import json
from module_admin.service.login_service import LoginService
from module_admin.entity.vo.login_vo import CurrentUserModel

# SSE 连接管理器
class SseConnectionManager:
    def __init__(self):
        # 存储连接：{user_id: [queue1, queue2, ...]}
        self.connections: Dict[int, List[asyncio.Queue]] = {}

    async def connect(self, user_id: int) -> asyncio.Queue:
        """
        创建新的 SSE 连接
        """
        queue = asyncio.Queue()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(queue)
        return queue

    def disconnect(self, user_id: int, queue: asyncio.Queue):
        """
        断开 SSE 连接
        """
        if user_id in self.connections:
            if queue in self.connections[user_id]:
                self.connections[user_id].remove(queue)
            if not self.connections[user_id]:
                del self.connections[user_id]

    async def send_message(self, message: str, user_id: int):
        """
        向指定用户发送消息
        """
        if user_id in self.connections:
            for queue in self.connections[user_id]:
                await queue.put(message)

    async def broadcast(self, message: str):
        """
        向所有用户广播消息
        """
        for user_id, queues in self.connections.items():
            for queue in queues:
                await queue.put(message)

# 创建连接管理器实例
sse_manager = SseConnectionManager()

# 创建 SSE 路由器
sseController = APIRouter(prefix='/sse')

async def event_generator(user_id: int, queue: asyncio.Queue):
    """
    SSE 事件生成器
    """
    try:
        while True:
            # 等待消息
            message = await queue.get()
            # 发送 SSE 事件
            yield f"data: {message}\n\n"
    finally:
        # 断开连接
        sse_manager.disconnect(user_id, queue)

@sseController.get("/connect")
async def sse_endpoint(
    token: str
):
    # 验证 token
    try:
        current_user = await LoginService.verify_token(token)
        user_id = current_user.user.user_id
        
        # 创建 SSE 连接
        queue = await sse_manager.connect(user_id)
        
        # 返回 StreamingResponse
        return StreamingResponse(
            event_generator(user_id, queue),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="无效的 token")
```

### 2.2 集成到项目

将上述代码添加到 `module_admin/controller/` 目录，例如创建 `sse_controller.py` 文件，然后在 `server.py` 中注册路由：

```python
# server.py 中添加
from module_admin.controller.sse_controller import sseController

# 在 controller_list 中添加
controller_list = [
    # ... 其他控制器
    {'router': sseController, 'tags': ['SSE 模块']},
]
```

### 2.3 SSE 消息发送工具类

创建 `utils/sse_util.py` 文件：

```python
from typing import List
import json
from config.get_redis import RedisUtil

class SseUtil:
    """
    SSE 工具类
    """
    
    # Redis 主题
    SSE_TOPIC = "global:sse"
    
    @classmethod
    async def send_message(cls, user_id: int, message: str):
        """
        向指定用户发送消息（当前实例）
        """
        from module_admin.controller.sse_controller import sse_manager
        await sse_manager.send_message(message, user_id)
    
    @classmethod
    async def broadcast(cls, message: str):
        """
        向所有在线用户广播消息（当前实例）
        """
        from module_admin.controller.sse_controller import sse_manager
        await sse_manager.broadcast(message)
    
    @classmethod
    async def publish_message(cls, user_ids: List[int], message: str):
        """
        向指定用户发送消息（支持多实例）
        """
        # 1. 先发送给当前实例的用户
        from module_admin.controller.sse_controller import sse_manager
        for user_id in user_ids:
            await sse_manager.send_message(message, user_id)
        
        # 2. 通过 Redis 发布给其他实例
        redis = await RedisUtil.get_redis()
        await redis.publish(
            cls.SSE_TOPIC,
            json.dumps({"user_ids": user_ids, "message": message})
        )
    
    @classmethod
    async def publish_all(cls, message: str):
        """
        向所有实例的所有用户广播消息
        """
        # 1. 先广播给当前实例
        from module_admin.controller.sse_controller import sse_manager
        await sse_manager.broadcast(message)
        
        # 2. 通过 Redis 广播给其他实例
        redis = await RedisUtil.get_redis()
        await redis.publish(
            cls.SSE_TOPIC,
            json.dumps({"user_ids": [], "message": message})
        )
```

### 2.4 Redis 消息订阅

在 `config/get_redis.py` 中添加 SSE 订阅处理：

```python
from utils.sse_util import SseUtil

async def handle_sse_message(message):
    """
    处理从 Redis 接收到的 SSE 消息
    """
    try:
        data = json.loads(message['data'])
        user_ids = data.get('user_ids', [])
        message_content = data.get('message', '')
        
        from module_admin.controller.sse_controller import sse_manager
        
        if not user_ids:
            # 广播消息
            await sse_manager.broadcast(message_content)
        else:
            # 发送给指定用户
            for user_id in user_ids:
                await sse_manager.send_message(message_content, user_id)
    except Exception as e:
        from utils.log_util import logger
        logger.error(f"处理 SSE 消息失败: {e}")

# 在 init_redis_subscription 函数中添加 SSE 订阅
async def init_redis_subscription():
    redis = await RedisUtil.get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(
        **{
            WebSocketUtil.WEB_SOCKET_TOPIC: handle_websocket_message,
            SseUtil.SSE_TOPIC: handle_sse_message
        }
    )
    # 启动订阅循环
    import asyncio
    asyncio.create_task(pubsub.run_in_thread(sleep=0.01))
```

### 2.5 业务集成示例

#### 示例1：审批流程通知

```python
from utils.sse_util import SseUtil
import json
from datetime import datetime

class ApprovalService:
    @classmethod
    async def approve(cls, task_id: int, approved: bool, comment: str, applicant_id: int):
        # 1. 处理审批逻辑
        # ... 业务逻辑 ...
        
        # 2. 构建消息
        message = json.dumps({
            "type": "APPROVAL_RESULT",
            "taskId": task_id,
            "approved": approved,
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 3. 通知申请人
        await SseUtil.publish_message([applicant_id], message)
```

#### 示例2：数据变更实时推送

```python
from utils.sse_util import SseUtil
import json
from datetime import datetime

class DashboardService:
    @classmethod
    async def push_dashboard_update(cls, user_id: int, dashboard_data: dict):
        # 构建消息
        message = json.dumps({
            "type": "DASHBOARD_UPDATE",
            "data": dashboard_data,
            "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 发送给指定用户
        await SseUtil.publish_message([user_id], message)
    
    @classmethod
    async def broadcast_to_admins(cls, admin_ids: List[int], content: str):
        # 构建消息
        message = json.dumps({
            "type": "ADMIN_NOTIFICATION",
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 发送给管理员
        await SseUtil.publish_message(admin_ids, message)
```

### 2.6 前端连接示例

```javascript
// 建立 SSE 连接
const token = localStorage.getItem('token');
const eventSource = new EventSource(`/sse/connect?token=${token}`);

eventSource.onopen = () => {
    console.log('SSE 连接成功');
};

// 监听消息事件
eventSource.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        console.log('收到消息:', data);
        
        // 根据消息类型处理
        switch (data.type) {
            case 'APPROVAL_RESULT':
                showApprovalResult(data);
                break;
            case 'DASHBOARD_UPDATE':
                updateDashboard(data.data);
                break;
            case 'ADMIN_NOTIFICATION':
                showAdminNotification(data.content);
                break;
        }
    } catch (error) {
        console.error('解析消息失败:', error);
    }
};

eventSource.onerror = (error) => {
    console.error('SSE 错误:', error);
    // 浏览器会自动尝试重连
};

// 主动关闭连接
function closeSseConnection() {
    eventSource.close();
    console.log('SSE 连接已关闭');
}

// 页面卸载时关闭连接
window.addEventListener('beforeunload', () => {
    closeSseConnection();
});
```

---

## 三、多实例部署与消息同步

### 3.1 架构原理

```
┌─────────────────────────────────────────────────────────────┐
│                        Redis Pub/Sub                        │
│                                                             │
│   Topic: global:websocket    Topic: global:sse             │
└─────────────────────────────────────────────────────────────┘
         ▲         │                  ▲         │
         │         ▼                  │         ▼
    ┌────┴────┐  ┌────┴────┐    ┌────┴────┐  ┌────┴────┐
    │ 实例 1  │  │ 实例 2  │    │ 实例 1  │  │ 实例 2  │
    │ WS连接  │  │ WS连接  │    │ SSE连接 │  │ SSE连接 │
    └─────────┘  └─────────┘    └─────────┘  └─────────┘
         │              │              │              │
    ┌────┴────┐    ┌────┴────┐  ┌────┴────┐    ┌────┴────┐
    │ 用户 A  │    │ 用户 B  │  │ 用户 C  │    │ 用户 D  │
    └─────────┘    └─────────┘  └─────────┘    └─────────┘
```

### 3.2 消息同步机制

**WebSocket 消息发送流程**：
1. 调用 `WebSocketUtil.publish_message(user_ids, message)`
2. 先检查目标用户是否在当前实例，在则直接发送
3. 不在当前实例的用户，通过 Redis 发布到 `global:websocket` 主题
4. 其他实例的订阅处理器接收并转发给本地用户

**SSE 消息发送流程**：
1. 调用 `SseUtil.publish_message(user_ids, message)`
2. 通过 Redis 发布到 `global:sse` 主题
3. 所有实例的订阅处理器接收并检查本地用户
4. 匹配到的用户通过 SSE 连接推送消息

### 3.3 配置与依赖

**依赖项**：
- FastAPI（已集成）
- Redis（已集成）
- asyncio（Python 标准库）

**Redis 配置**：
```python
# config/env.py 中的 Redis 配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
```

---

## 四、常见场景实战

### 4.1 场景：系统通知推送

```python
from utils.sse_util import SseUtil
import json
from datetime import datetime

class SystemNoticeService:
    @classmethod
    async def send_notice(cls, user_id: int, title: str, content: str):
        """
        发送系统通知（SSE 方式）
        """
        message = json.dumps({
            "type": "SYSTEM_NOTICE",
            "title": title,
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        await SseUtil.publish_message([user_id], message)

    @classmethod
    async def broadcast_announcement(cls, title: str, content: str):
        """
        广播系统公告
        """
        message = json.dumps({
            "type": "ANNOUNCEMENT",
            "title": title,
            "content": content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        await SseUtil.publish_all(message)
```

### 4.2 场景：在线用户统计

```python
class OnlineUserService:
    @classmethod
    def get_online_count(cls):
        """
        获取当前实例在线用户数（WebSocket）
        """
        from module_admin.controller.websocket_controller import manager
        return len(manager.active_connections)

    @classmethod
    def is_online(cls, user_id: int):
        """
        检查用户是否在线（当前实例）
        """
        from module_admin.controller.websocket_controller import manager
        return user_id in manager.active_connections

    @classmethod
    def get_online_users(cls):
        """
        获取在线用户列表（当前实例）
        """
        from module_admin.controller.websocket_controller import manager
        return list(manager.active_connections.keys())
```

### 4.3 场景：订单状态实时更新

```python
from utils.websocket_util import WebSocketUtil
from utils.sse_util import SseUtil
import json
from datetime import datetime

class OrderNotifyService:
    @classmethod
    async def notify_order_status_change(cls, order: dict):
        """
        订单状态变更通知
        """
        # 1. 构建消息
        message = json.dumps({
            "type": "ORDER_STATUS_CHANGE",
            "orderId": order.get("id"),
            "orderNo": order.get("order_no"),
            "oldStatus": order.get("old_status"),
            "newStatus": order.get("status"),
            "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        buyer_id = order.get("user_id")
        seller_id = order.get("seller_id")

        # 2. 通知买家（SSE）
        if buyer_id:
            await SseUtil.publish_message([buyer_id], message)

        # 3. 通知卖家（WebSocket，如果需要双向通信）
        if seller_id:
            await WebSocketUtil.publish_message([seller_id], message)
```

---

## 五、常见错误与最佳实践

### ❌ 错误1：未处理连接关闭

```python
# ❌ 错误：未处理 WebSocket 断开连接
@sse_controller.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(data)

# ✅ 正确：处理 WebSocket 断开连接
@sse_controller.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        # 验证 token
        current_user = await LoginService.verify_token(token)
        user_id = current_user.user.user_id
        
        # 连接 WebSocket
        await manager.connect(websocket, user_id)
        
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(data, user_id)
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        if 'user_id' in locals():
            manager.disconnect(user_id)
        await websocket.close()
```

### ❌ 错误2：消息格式不统一

```python
# ❌ 错误：直接发送字符串，前端难以解析
await WebSocketUtil.send_message(user_id, "订单已更新")

# ✅ 正确：使用 JSON 格式，包含类型字段
message = json.dumps({
    "type": "ORDER_UPDATE",  # 消息类型，便于前端路由处理
    "data": order_data,
    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
})
await WebSocketUtil.send_message(user_id, message)
```

### ❌ 错误3：在循环中逐个发送消息

```python
# ❌ 错误：效率低
for user_id in user_ids:
    message = json.dumps({"type": "NOTIFICATION", "content": "新消息"})
    await WebSocketUtil.publish_message([user_id], message)  # 每次都发布到 Redis

# ✅ 正确：批量发送
message = json.dumps({"type": "NOTIFICATION", "content": "新消息"})
await WebSocketUtil.publish_message(user_ids, message)  # 只发布一次
```

### ❌ 错误4：未使用 Redis 进行多实例同步

```python
# ❌ 错误：只在当前实例发送
await manager.send_personal_message(message, user_id)

# ✅ 正确：使用工具类进行多实例同步
await WebSocketUtil.publish_message([user_id], message)
```

### ❌ 错误5：SSE 连接泄漏

```python
# ❌ 错误：未处理 SSE 连接关闭
async def event_generator():
    while True:
        message = await queue.get()
        yield f"data: {message}\n\n"

# ✅ 正确：处理 SSE 连接关闭
async def event_generator(user_id: int, queue: asyncio.Queue):
    try:
        while True:
            message = await queue.get()
            yield f"data: {message}\n\n"
    finally:
        # 断开连接
        sse_manager.disconnect(user_id, queue)
```

---

## 六、API 速查表

### WebSocket API

| 方法 | 说明 | 适用场景 |
|------|------|---------|
| `WebSocketUtil.send_message(user_id, message)` | 发送给指定用户（当前实例） | 单实例部署 |
| `WebSocketUtil.broadcast(message)` | 广播给当前实例所有用户 | 单实例广播 |
| `WebSocketUtil.publish_message(user_ids, message)` | 发送给指定用户（多实例） | 多实例部署 |
| `WebSocketUtil.publish_all(message)` | 广播给所有实例所有用户 | 系统广播 |

### SSE API

| 方法 | 说明 | 适用场景 |
|------|------|---------|
| `SseUtil.send_message(user_id, message)` | 发送给指定用户（当前实例） | 单实例部署 |
| `SseUtil.broadcast(message)` | 广播给当前实例所有用户 | 单实例广播 |
| `SseUtil.publish_message(user_ids, message)` | 发送给指定用户（多实例） | 多实例部署 |
| `SseUtil.publish_all(message)` | 广播给所有实例所有用户 | 系统广播 |

---

## 七、项目集成步骤

### 1. 创建 WebSocket 控制器
- 文件：`module_admin/controller/websocket_controller.py`
- 实现 WebSocket 连接管理和消息处理

### 2. 创建 SSE 控制器
- 文件：`module_admin/controller/sse_controller.py`
- 实现 SSE 连接管理和消息推送

### 3. 创建工具类
- 文件：`utils/websocket_util.py` - WebSocket 消息发送工具
- 文件：`utils/sse_util.py` - SSE 消息发送工具

### 4. 配置 Redis 订阅
- 修改：`config/get_redis.py`
- 添加 WebSocket 和 SSE 消息订阅处理

### 5. 注册路由
- 修改：`server.py`
- 添加 WebSocket 和 SSE 控制器路由

### 6. 初始化 Redis 订阅
- 修改：`server.py`
- 在应用启动时初始化 Redis 订阅

---

## 八、总结

本指南提供了基于 FastAPI 的 WebSocket 和 SSE 实现方案，具有以下特点：

1. **与项目架构集成**：完全基于 FastAPI + Python 架构，与现有代码无缝集成
2. **支持多实例部署**：通过 Redis 发布订阅实现多实例消息同步
3. **JWT 认证**：集成了项目现有的 JWT 认证机制
4. **完整的示例**：提供了详细的代码示例和使用场景
5. **最佳实践**：包含了常见错误和最佳实践指南

通过本指南，您可以在 CodeAI 项目中快速实现：
- 实时消息推送
- 双向通信（聊天、协作）
- 系统通知
- 订单状态更新
- 在线状态管理
- 数据仪表盘实时更新

选择合适的实时通信方案：
- **WebSocket**：适合需要双向通信的场景
- **SSE**：适合只需服务端推送的场景，实现更简单
