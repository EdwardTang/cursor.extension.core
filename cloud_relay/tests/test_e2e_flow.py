"""Cloud Relay服务的端到端测试。

测试端到端通信流程，确保PWA、Sidecar和Cloud Relay之间的消息传递正常工作。
"""
import asyncio
import json
import pytest
import uuid
import websockets
from websockets.exceptions import InvalidStatusCode

from .conftest import PWAClient, SidecarClient

pytestmark = pytest.mark.asyncio


async def test_happy_path_message_relay(relay_server, pwa_client, sidecar_client):
    """测试基本的消息中继：PWA -> Cloud Relay -> Sidecar和反向流程。"""
    # PWA -> Sidecar消息测试
    test_message = {
        "id": str(uuid.uuid4()),
        "type": "command",
        "data": {
            "action": "start_plan",
            "parameters": {
                "goal": "Test message relay"
            }
        }
    }
    
    # 从PWA发送消息
    await pwa_client.send(json.dumps(test_message))
    
    # Sidecar应该接收到相同的消息
    response = await sidecar_client.receive(timeout=2.0)
    assert response is not None, "Sidecar未收到来自PWA的消息"
    
    # 验证消息内容
    response_data = json.loads(response)
    assert response_data["id"] == test_message["id"], "消息ID不匹配"
    assert response_data["type"] == test_message["type"], "消息类型不匹配"
    assert response_data["data"]["action"] == test_message["data"]["action"], "消息动作不匹配"
    
    # Sidecar -> PWA消息测试
    response_message = {
        "id": str(uuid.uuid4()),
        "type": "status",
        "data": {
            "status": "success",
            "ref_id": test_message["id"],
            "result": {
                "message": "Plan started"
            }
        }
    }
    
    # 从Sidecar发送响应
    await sidecar_client.send(json.dumps(response_message))
    
    # PWA应该接收到响应
    pwa_response = await pwa_client.receive(timeout=2.0)
    assert pwa_response is not None, "PWA未收到来自Sidecar的消息"
    
    # 验证响应内容
    pwa_response_data = json.loads(pwa_response)
    assert pwa_response_data["id"] == response_message["id"], "响应ID不匹配"
    assert pwa_response_data["type"] == response_message["type"], "响应类型不匹配"
    assert pwa_response_data["data"]["ref_id"] == test_message["id"], "原始消息引用ID不匹配"


async def test_auth_failure(relay_server, pwa_client_expired_token):
    """测试过期令牌导致身份验证失败。"""
    # 尝试连接，应该失败
    with pytest.raises(InvalidStatusCode) as excinfo:
        await pwa_client_expired_token.connect()
    
    # 验证状态码为401 Unauthorized
    assert excinfo.value.status_code == 401, f"预期状态码401，实际得到{excinfo.value.status_code}"


async def test_connection_lifecycle(relay_server, valid_token):
    """测试连接生命周期：连接、断开连接、重新连接。"""
    # 创建并连接客户端
    client = PWAClient(relay_server.ws_url, valid_token)
    await client.connect()
    
    # 发送测试消息
    test_message = {"id": "test1", "type": "ping", "data": {}}
    await client.send(json.dumps(test_message))
    
    # 关闭连接
    await client.close()
    
    # 重新连接
    await client.connect()
    
    # 发送另一条测试消息
    test_message2 = {"id": "test2", "type": "ping", "data": {}}
    await client.send(json.dumps(test_message2))
    
    # 清理
    await client.close()


async def test_error_propagation(relay_server, pwa_client, sidecar_client, network_glitch):
    """测试错误传播：网络连接中断后恢复通信。"""
    # 为Sidecar客户端注入网络故障
    await network_glitch(sidecar_client.ws, after_n_messages=2, delay_seconds=1.0)
    
    # 发送第一条消息（不会触发故障）
    test_message1 = {
        "id": str(uuid.uuid4()),
        "type": "command",
        "data": {"action": "test1"}
    }
    await pwa_client.send(json.dumps(test_message1))
    
    # 确认Sidecar收到第一条消息
    response1 = await sidecar_client.receive(timeout=2.0)
    assert response1 is not None, "Sidecar未收到第一条消息"
    
    # 从Sidecar回复确认
    ack1 = {
        "id": str(uuid.uuid4()),
        "type": "ack",
        "data": {"ref_id": json.loads(response1)["id"]}
    }
    
    # 这条消息将触发网络故障
    await sidecar_client.send(json.dumps(ack1))
    
    # 等待一段时间，让网络"故障"发生
    await asyncio.sleep(2.0)
    
    # 创建新连接恢复通信
    sidecar_client2 = SidecarClient(relay_server.ws_url, valid_token)
    await sidecar_client2.connect()
    
    # 发送第二条消息验证恢复
    test_message2 = {
        "id": str(uuid.uuid4()),
        "type": "command",
        "data": {"action": "test2"}
    }
    await pwa_client.send(json.dumps(test_message2))
    
    # 确认新的Sidecar连接能收到消息
    response2 = await sidecar_client2.receive(timeout=2.0)
    assert response2 is not None, "恢复连接后Sidecar未收到消息"
    
    # 清理
    await sidecar_client2.close()


async def test_batch_processing(relay_server, pwa_client, sidecar_client):
    """测试批处理：发送多条消息，确保全部送达。"""
    # 创建一批消息
    batch_size = 10
    messages = []
    message_ids = []
    
    for i in range(batch_size):
        msg_id = str(uuid.uuid4())
        message_ids.append(msg_id)
        messages.append({
            "id": msg_id,
            "type": "command",
            "data": {
                "action": f"batch_test_{i}",
                "parameters": {"index": i}
            }
        })
    
    # 快速发送所有消息
    for msg in messages:
        await pwa_client.send(json.dumps(msg))
    
    # 验证所有消息都送达到Sidecar
    received_ids = set()
    for _ in range(batch_size):
        response = await sidecar_client.receive(timeout=5.0)
        assert response is not None, f"只收到{len(received_ids)}/{batch_size}个消息"
        
        response_data = json.loads(response)
        received_ids.add(response_data["id"])
    
    # 验证所有消息ID都被接收
    assert set(message_ids) == received_ids, "接收到的消息ID与发送的不匹配"


async def test_malformed_message_handling(relay_server, pwa_client):
    """测试处理格式错误消息。"""
    # 发送非JSON消息
    await pwa_client.send("这不是有效的JSON消息")
    
    # 发送结构不正确的JSON
    await pwa_client.send('{"type": "invalid"}')  # 缺少必需的id字段
    
    # 验证连接仍然有效（而不是关闭）
    test_message = {
        "id": str(uuid.uuid4()),
        "type": "command",
        "data": {"action": "test_after_malformed"}
    }
    await pwa_client.send(json.dumps(test_message))
    
    # 确认连接仍然工作（我们可以继续发送消息）
    assert pwa_client.ws.open, "格式错误的消息后WebSocket连接被关闭" 