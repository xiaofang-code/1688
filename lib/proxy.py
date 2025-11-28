#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理 IP 池管理模块

使用青果代理 IP 服务
API 文档：https://share.proxy.qg.net
"""

import time
from typing import Optional, Dict, List
from dataclasses import dataclass
from urllib.parse import quote
import requests

from config.proxy_config import PROXY_API_KEY, PROXY_ENABLED, PROXY_USERNAME, PROXY_PASSWORD


@dataclass
class ProxyInfo:
    """代理 IP 信息"""
    proxy_ip: str       # 代理出口 IP
    server: str         # 代理服务器地址 (host:port)
    area: str           # 地区
    isp: str            # 运营商
    deadline: str       # 过期时间
    username: str = ""  # 认证用户名
    password: str = ""  # 认证密码
    
    @property
    def http_proxy(self) -> str:
        """HTTP 代理地址（URL 编码用户名密码）"""
        if self.username and self.password:
            # URL 编码用户名和密码，处理特殊字符
            encoded_user = quote(self.username, safe='')
            encoded_pass = quote(self.password, safe='')
            return f"http://{encoded_user}:{encoded_pass}@{self.server}"
        return f"http://{self.server}"
    
    @property
    def playwright_proxy(self) -> Dict:
        """Playwright 代理配置"""
        config = {"server": f"http://{self.server}"}
        if self.username and self.password:
            config["username"] = self.username
            config["password"] = self.password
        return config
    
    @property
    def requests_proxies(self) -> Dict:
        """Requests 代理配置"""
        return {
            "http": self.http_proxy,
            "https": self.http_proxy
        }


class ProxyPool:
    """代理 IP 池"""
    
    def __init__(self, api_key: str = PROXY_API_KEY, enabled: bool = PROXY_ENABLED):
        self.api_key = api_key
        self.enabled = enabled
        self.base_url = "https://share.proxy.qg.net/get"
        self._current_proxy: Optional[ProxyInfo] = None
        self._last_fetch_time: float = 0
        self._min_fetch_interval = 1.0  # 最小请求间隔（秒）
    
    def get_proxy(self, force_new: bool = False) -> Optional[ProxyInfo]:
        """
        获取代理 IP
        
        Args:
            force_new: 是否强制获取新 IP
            
        Returns:
            代理 IP 信息，获取失败或禁用时返回 None
        """
        # 如果代理被禁用，返回 None
        if not self.enabled:
            return None
        
        # 如果有缓存的代理且未过期，直接返回
        if not force_new and self._current_proxy:
            return self._current_proxy
        
        # 限制请求频率
        elapsed = time.time() - self._last_fetch_time
        if elapsed < self._min_fetch_interval:
            time.sleep(self._min_fetch_interval - elapsed)
        
        try:
            params = {
                "key": self.api_key,
                "num": 1,
                "format": "json",
                "distinct": "true"
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            self._last_fetch_time = time.time()
            
            data = response.json()
            
            if data.get("code") != "SUCCESS":
                print(f"获取代理失败: {data.get('code')} - {data}")
                return None
            
            ip_data = data.get("data", [])
            if not ip_data:
                print("获取代理失败: 无可用 IP")
                return None
            
            ip_info = ip_data[0]
            self._current_proxy = ProxyInfo(
                proxy_ip=ip_info.get("proxy_ip", ""),
                server=ip_info.get("server", ""),
                area=ip_info.get("area", ""),
                isp=ip_info.get("isp", ""),
                deadline=ip_info.get("deadline", ""),
                username=PROXY_USERNAME,
                password=PROXY_PASSWORD
            )
            
            print(f"✅ 获取代理 IP: {self._current_proxy.server} ({self._current_proxy.area})")
            return self._current_proxy
            
        except Exception as e:
            print(f"获取代理异常: {e}")
            return None
    
    def get_proxies(self, num: int) -> List[ProxyInfo]:
        """
        批量获取代理 IP（每个图片使用不同的 IP，避免重复超时）
        
        Args:
            num: 需要的代理数量
            
        Returns:
            代理 IP 列表
        """
        if not self.enabled:
            return []
        
        if num <= 0:
            return []
        
        # 限制请求频率
        elapsed = time.time() - self._last_fetch_time
        if elapsed < self._min_fetch_interval:
            time.sleep(self._min_fetch_interval - elapsed)
        
        try:
            params = {
                "key": self.api_key,
                "num": min(num, 50),  # 单次最多获取 50 个
                "format": "json",
                "distinct": "true"  # IP 去重
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            self._last_fetch_time = time.time()
            
            data = response.json()
            
            if data.get("code") != "SUCCESS":
                print(f"批量获取代理失败: {data.get('code')} - {data}")
                return []
            
            ip_data = data.get("data", [])
            if not ip_data:
                print("批量获取代理失败: 无可用 IP")
                return []
            
            proxies = []
            for ip_info in ip_data:
                proxy = ProxyInfo(
                    proxy_ip=ip_info.get("proxy_ip", ""),
                    server=ip_info.get("server", ""),
                    area=ip_info.get("area", ""),
                    isp=ip_info.get("isp", ""),
                    deadline=ip_info.get("deadline", ""),
                    username=PROXY_USERNAME,
                    password=PROXY_PASSWORD
                )
                proxies.append(proxy)
            
            print(f"✅ 批量获取 {len(proxies)} 个代理 IP")
            for i, p in enumerate(proxies):
                print(f"   [{i+1}] {p.server} ({p.area})")
            
            return proxies
            
        except Exception as e:
            print(f"批量获取代理异常: {e}")
            return []
    
    def clear_proxy(self):
        """清除当前代理（用于代理失效时）"""
        self._current_proxy = None
    
    def set_enabled(self, enabled: bool):
        """设置是否启用代理"""
        self.enabled = enabled


# 全局代理池实例
_proxy_pool: Optional[ProxyPool] = None


def get_proxy_pool() -> ProxyPool:
    """获取全局代理池实例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool


def get_proxy() -> Optional[ProxyInfo]:
    """便捷函数：获取代理 IP"""
    return get_proxy_pool().get_proxy()


def get_new_proxy() -> Optional[ProxyInfo]:
    """便捷函数：获取新的代理 IP"""
    return get_proxy_pool().get_proxy(force_new=True)


def get_proxies(num: int) -> List[ProxyInfo]:
    """便捷函数：批量获取代理 IP（每个图片用不同的 IP）"""
    return get_proxy_pool().get_proxies(num)


def is_proxy_enabled() -> bool:
    """检查代理是否启用"""
    return get_proxy_pool().enabled


def set_proxy_enabled(enabled: bool):
    """设置代理是否启用"""
    get_proxy_pool().set_enabled(enabled)
