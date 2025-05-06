"""测试配置和共享fixtures。"""
import asyncio
import os
import pytest
import pytest_asyncio
import random
import socket
import time
import jwt
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import uvicorn
from uvicorn.config import Config
import websockets
from jose import JWTError, jwt as jose_jwt

from cloud_relay import app as relay_app

# 用于测试的JWT密钥
TEST_JWT_SECRET = "test_secret_key_for_testing_purposes_only"
TEST_JWT_ALGORITHM = "HS256"
TEST_JWT_EXPIRE_MINUTES = 30


@pytest.fixture
def valid_token():
    """提供有效的JWT令牌用于测试。"""
    payload = {
        "sub": "test_user",
        "device_id": "test_device_123",
        "exp": datetime.utcnow() + timedelta(minutes=TEST_JWT_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "scope": "sidecar pwa"
    }
    token = jose_jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)
    return token


@pytest.fixture
def expired_token():
    """提供已过期的JWT令牌用于测试。"""
    payload = {
        "sub": "test_user",
        "device_id": "test_device_123",
        "exp": datetime.utcnow() - timedelta(minutes=5),  # 5分钟前过期
        "iat": datetime.utcnow() - timedelta(minutes=35),
        "scope": "sidecar pwa"
    }
    token = jose_jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)
    return token


class RelayServer:
    """在测试期间运行的Cloud Relay服务器。"""
    
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = self._get_free_port()
        self.base_url = f"http://{self.host}:{self.port}"
        self.ws_url = f"ws://{self.host}:{self.port}"
        self.ready_event = asyncio.Event()
        self.server = None
        self.server_task = None
        
        # 配置应用
        self.app = FastAPI()
        # 从主应用复制路由
        self.app.include_router(relay_app.app.router)
        # 覆盖配置以使用测试JWT密钥
        os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET
        os.environ["JWT_ALGORITHM"] = TEST_JWT_ALGORITHM
    
    @staticmethod
    def _get_free_port():
        """获取一个可用的随机端口。"""
        # 尝试找一个未使用的端口
        while True:
            port = random.randint(10000, 65535)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    
    async def start(self):
        """启动测试服务器。"""
        config = Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="error",
            workers=1
        )
        
        server = uvicorn.Server(config)
        
        # 修改run方法以设置就绪事件
        original_run = server.run
        
        async def patched_run():
            self.ready_event.set()
            await original_run()
        
        server.run = patched_run
        self.server = server
        
        # 在单独的任务中启动服务器
        self.server_task = asyncio.create_task(server.serve())
        
        # 等待服务器就绪
        await self.ready_event.wait()
        
        # 给服务器一点时间完全初始化
        await asyncio.sleep(0.5)
    
    async def stop(self):
        """停止测试服务器。"""
        if self.server:
            self.server.should_exit = True
            await self.server_task
            self.server = None
            self.server_task = None


@pytest_asyncio.fixture
async def relay_server():
    """提供一个运行中的Cloud Relay服务器，用于端到端测试。"""
    server = RelayServer()
    await server.start()
    
    yield server
    
    await server.stop()


class PWAClient:
    """模拟PWA客户端与Cloud Relay的WebSocket连接。"""
    
    def __init__(self, ws_url, token):
        self.ws_url = ws_url
        self.token = token
        self.ws = None
        self.received_messages = asyncio.Queue()
    
    async def connect(self):
        """连接到Cloud Relay服务器。"""
        headers = {"Authorization": f"Bearer {self.token}"}
        self.ws = await websockets.connect(
            f"{self.ws_url}/ws/pwa",
            extra_headers=headers
        )
        # 启动接收消息的后台任务
        asyncio.create_task(self._receive_messages())
    
    async def _receive_messages(self):
        """接收并存储所有传入消息。"""
        while True:
            try:
                message = await self.ws.recv()
                await self.received_messages.put(message)
            except websockets.exceptions.ConnectionClosed:
                break
    
    async def send(self, message):
        """发送消息到服务器。"""
        await self.ws.send(message)
    
    async def receive(self, timeout=1.0):
        """从队列接收消息，可选超时。"""
        try:
            return await asyncio.wait_for(self.received_messages.get(), timeout)
        except asyncio.TimeoutError:
            return None
    
    async def close(self):
        """关闭连接。"""
        if self.ws:
            await self.ws.close()
            self.ws = None


class SidecarClient:
    """模拟Sidecar客户端与Cloud Relay的WebSocket连接。"""
    
    def __init__(self, ws_url, token):
        self.ws_url = ws_url
        self.token = token
        self.ws = None
        self.received_messages = asyncio.Queue()
    
    async def connect(self):
        """连接到Cloud Relay服务器。"""
        headers = {"Authorization": f"Bearer {self.token}"}
        self.ws = await websockets.connect(
            f"{self.ws_url}/ws/sidecar",
            extra_headers=headers
        )
        # 启动接收消息的后台任务
        asyncio.create_task(self._receive_messages())
    
    async def _receive_messages(self):
        """接收并存储所有传入消息。"""
        while True:
            try:
                message = await self.ws.recv()
                await self.received_messages.put(message)
            except websockets.exceptions.ConnectionClosed:
                break
    
    async def send(self, message):
        """发送消息到服务器。"""
        await self.ws.send(message)
    
    async def receive(self, timeout=1.0):
        """从队列接收消息，可选超时。"""
        try:
            return await asyncio.wait_for(self.received_messages.get(), timeout)
        except asyncio.TimeoutError:
            return None
    
    async def close(self):
        """关闭连接。"""
        if self.ws:
            await self.ws.close()
            self.ws = None


@pytest_asyncio.fixture
async def pwa_client(relay_server, valid_token):
    """提供已连接的PWA客户端。"""
    client = PWAClient(relay_server.ws_url, valid_token)
    await client.connect()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def sidecar_client(relay_server, valid_token):
    """提供已连接的Sidecar客户端。"""
    client = SidecarClient(relay_server.ws_url, valid_token)
    await client.connect()
    yield client
    await client.close()


@pytest_asyncio.fixture
async def pwa_client_expired_token(relay_server, expired_token):
    """提供带过期令牌的PWA客户端。"""
    client = PWAClient(relay_server.ws_url, expired_token)
    yield client  # 注意：这里不预先连接，因为我们期望连接失败


@pytest_asyncio.fixture
async def sidecar_client_expired_token(relay_server, expired_token):
    """提供带过期令牌的Sidecar客户端。"""
    client = SidecarClient(relay_server.ws_url, expired_token)
    yield client  # 注意：这里不预先连接，因为我们期望连接失败


@pytest.fixture
def network_glitch():
    """提供一个帮助函数来模拟网络故障。"""
    async def _inject_glitch(ws, after_n_messages=1, delay_seconds=0.5):
        """
        在发送/接收N条消息后模拟网络故障。
        
        参数:
            ws: WebSocket连接对象
            after_n_messages: 发送多少条消息后触发故障
            delay_seconds: 故障持续时间
        """
        # 保存原始方法
        original_send = ws.send
        original_recv = ws.recv
        message_count = 0
        
        # 替换为会计数和中断的版本
        async def counting_send(message):
            nonlocal message_count
            message_count += 1
            await original_send(message)
            if message_count >= after_n_messages:
                await asyncio.sleep(delay_seconds)
                raise ConnectionResetError("Simulated network glitch")
        
        ws.send = counting_send
        
        return ws
    
    return _inject_glitch 