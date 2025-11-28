#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
1688 以图搜货 - 自动获取产品链接

使用 Playwright 无头浏览器获取动态渲染的产品数据
支持代理 IP 池，防止反爬
"""

from typing import List, Dict, Optional
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from lib.proxy import get_proxy, get_new_proxy, get_proxies, ProxyInfo


def get_search_url(image_id: str) -> str:
    """获取搜索结果页面 URL"""
    return f"https://s.1688.com/youyuan/index.htm?tab=imageSearch&imageId={image_id}&imageIdList={image_id}"


async def fetch_product_links_async(
    image_id: str, 
    limit: int = 5, 
    headless: bool = True, 
    timeout: int = 60000,
    use_proxy: bool = True,
    retry_count: int = 2,
    proxy_info: Optional[ProxyInfo] = None  # 可指定代理
) -> List[Dict]:
    """
    异步版本：使用 Playwright 获取产品链接（用于 FastAPI）
    
    Args:
        image_id: 上传图片后返回的 imageId
        limit: 返回产品数量限制，默认5个
        headless: 是否使用无头模式，默认 True
        timeout: 等待超时时间（毫秒），默认 60000
        use_proxy: 是否使用代理，默认 True
        retry_count: 失败重试次数，默认 2
        proxy_info: 指定的代理（用于批量处理时每个图片用不同 IP）
        
    Returns:
        产品列表 [{"title": "...", "url": "...", "offer_id": "..."}, ...]
    """
    search_url = get_search_url(image_id)
    products = []
    
    for attempt in range(retry_count + 1):
        # 获取代理：优先使用指定的代理
        proxy_config = None
        if use_proxy:
            current_proxy = proxy_info if (proxy_info and attempt == 0) else (get_new_proxy() if attempt > 0 else get_proxy())
            if current_proxy:
                proxy_config = current_proxy.playwright_proxy
                print(f"🌐 使用代理: {current_proxy.server}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                proxy=proxy_config
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=timeout)
                await page.wait_for_function(
                    "window.offerList && window.offerList.length > 0", 
                    timeout=timeout
                )
                
                products = await page.evaluate(f"""
                    () => {{
                        if (!window.offerList) return [];
                        return window.offerList.slice(0, {limit}).map(p => ({{
                            title: p.title || '',
                            url: `https://detail.1688.com/offer/${{p.offerId}}.html`,
                            offer_id: String(p.offerId || '')
                        }}));
                    }}
                """)
                
                await browser.close()
                return products
                
            except Exception as e:
                print(f"获取产品链接失败 (尝试 {attempt + 1}/{retry_count + 1}): {e}")
                await browser.close()
                
                if attempt < retry_count:
                    print("🔄 切换代理重试...")
                    continue
    
    return products


def fetch_product_links(
    image_id: str, 
    limit: int = 5, 
    headless: bool = True, 
    timeout: int = 60000,
    use_proxy: bool = True,
    retry_count: int = 2
) -> List[Dict]:
    """
    同步版本：使用 Playwright 获取产品链接（用于命令行）
    
    Args:
        image_id: 上传图片后返回的 imageId
        limit: 返回产品数量限制，默认5个
        headless: 是否使用无头模式，默认 True
        timeout: 等待超时时间（毫秒），默认 60000
        use_proxy: 是否使用代理，默认 True
        retry_count: 失败重试次数，默认 2
        
    Returns:
        产品列表 [{"title": "...", "url": "...", "offer_id": "..."}, ...]
    """
    search_url = get_search_url(image_id)
    products = []
    
    for attempt in range(retry_count + 1):
        # 获取代理
        proxy_config = None
        if use_proxy:
            proxy_info = get_new_proxy() if attempt > 0 else get_proxy()
            if proxy_info:
                proxy_config = proxy_info.playwright_proxy
                print(f"🌐 使用代理: {proxy_info.server}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-setuid-sandbox'],
                proxy=proxy_config
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=timeout)
                page.wait_for_function(
                    "window.offerList && window.offerList.length > 0", 
                    timeout=timeout
                )
                
                products = page.evaluate(f"""
                    () => {{
                        if (!window.offerList) return [];
                        return window.offerList.slice(0, {limit}).map(p => ({{
                            title: p.title || '',
                            url: `https://detail.1688.com/offer/${{p.offerId}}.html`,
                            offer_id: String(p.offerId || '')
                        }}));
                    }}
                """)
                
                browser.close()
                return products
                
            except Exception as e:
                print(f"获取产品链接失败 (尝试 {attempt + 1}/{retry_count + 1}): {e}")
                browser.close()
                
                if attempt < retry_count:
                    print("🔄 切换代理重试...")
                    continue
    
    return products


def print_product_links(products: List[Dict]) -> None:
    """打印产品链接"""
    print("\n" + "=" * 60)
    print(f"🔗 搜索结果 - 共 {len(products)} 个产品")
    print("=" * 60)
    
    for idx, p in enumerate(products, 1):
        print(f"\n【{idx}】{p['title']}")
        print(f"    🔗 {p['url']}")
    
    print("\n" + "=" * 60)
