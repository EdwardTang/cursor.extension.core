#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
认证模块测试
"""

import os
import time
import unittest
import pytest
from datetime import datetime, timedelta

try:
    from cloud_relay.auth import create_token, create_tokens, decode_token, refresh_access_token, TokenResponse, TokenData
except ImportError:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from auth import create_token, create_tokens, decode_token, refresh_access_token, TokenResponse, TokenData

class TestAuth(unittest.TestCase):
    """认证模块测试类"""
    
    def setUp(self):
        """测试初始化"""
        self.session_id = "test-session-123"
        self.user_id = "test-user-123"
        self.device_id = "test-device-123"
        self.scopes = ["default", "admin"]
        
    def test_create_token(self):
        """测试创建令牌"""
        token = create_token(
            session_id=self.session_id,
            user_id=self.user_id,
            device_id=self.device_id,
            scopes=self.scopes
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # 解码并验证令牌
        payload = decode_token(token)
        assert payload["sub"] == self.session_id
        assert payload["user_id"] == self.user_id
        assert payload["device_id"] == self.device_id
        assert payload["scopes"] == self.scopes
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > time.time()
        
    def test_create_tokens(self):
        """测试创建访问令牌和刷新令牌"""
        tokens = create_tokens(
            session_id=self.session_id,
            user_id=self.user_id,
            device_id=self.device_id,
            scopes=self.scopes
        )
        
        assert isinstance(tokens, TokenResponse)
        assert isinstance(tokens.access_token, str)
        assert isinstance(tokens.refresh_token, str)
        assert isinstance(tokens.expires_at, datetime)
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0
        
        # 解码并验证访问令牌
        access_payload = decode_token(tokens.access_token)
        assert access_payload["sub"] == self.session_id
        assert access_payload["type"] == "access"
        
        # 解码并验证刷新令牌
        refresh_payload = decode_token(tokens.refresh_token)
        assert refresh_payload["sub"] == self.session_id
        assert refresh_payload["type"] == "refresh"
        assert refresh_payload["exp"] > access_payload["exp"]
        
    def test_refresh_access_token(self):
        """测试刷新访问令牌"""
        # 创建一个刷新令牌
        refresh_token = create_token(
            session_id=self.session_id,
            user_id=self.user_id,
            device_id=self.device_id,
            scopes=self.scopes,
            token_type="refresh"
        )
        
        # 使用刷新令牌获取新访问令牌
        token_response = refresh_access_token(refresh_token)
        
        assert isinstance(token_response, TokenResponse)
        assert isinstance(token_response.access_token, str)
        assert token_response.refresh_token == refresh_token
        
        # 解码并验证新访问令牌
        new_access_payload = decode_token(token_response.access_token)
        assert new_access_payload["sub"] == self.session_id
        assert new_access_payload["user_id"] == self.user_id
        assert new_access_payload["device_id"] == self.device_id
        assert new_access_payload["type"] == "access"
        
if __name__ == "__main__":
    unittest.main() 