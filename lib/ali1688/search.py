#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
1688 以图搜货 - 自动获取产品链接

使用 Playwright 无头浏览器获取动态渲染的产品数据
支持 Docker/Ubuntu 部署
"""

from typing import List, Dict
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import asyncio


def get_search_url(image_id: str) -> str:
    """获取搜索结果页面 URL"""
    return f"https://s.1688.com/youyuan/index.htm?tab=imageSearch&imageId={image_id}&imageIdList={image_id}"


async def fetch_product_links_async(image_id: str, limit: int = 5, headless: bool = True, timeout: int = 60000) -> List[Dict]:
    """
    异步版本：使用 Playwright 获取产品链接（用于 FastAPI）
    
    Args:
        image_id: 上传图片后返回的 imageId
        limit: 返回产品数量限制，默认5个
        headless: 是否使用无头模式，默认 True
        timeout: 等待超时时间（毫秒），默认 60000
        
    Returns:
        产品列表 [{"title": "...", "url": "...", "offer_id": "..."}, ...]
    """
    search_url = get_search_url(image_id)
    products = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
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
            
        except Exception as e:
            print(f"获取产品链接失败: {e}")
            products = []
        finally:
            await browser.close()
    
    return products


def fetch_product_links(image_id: str, limit: int = 5, headless: bool = True, timeout: int = 60000) -> List[Dict]:
    """
    同步版本：使用 Playwright 获取产品链接（用于命令行）
    
    Args:
        image_id: 上传图片后返回的 imageId
        limit: 返回产品数量限制，默认5个
        headless: 是否使用无头模式，默认 True
        timeout: 等待超时时间（毫秒），默认 60000
        
    Returns:
        产品列表 [{"title": "...", "url": "...", "offer_id": "..."}, ...]
    """
    search_url = get_search_url(image_id)
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
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
            
        except Exception as e:
            print(f"获取产品链接失败: {e}")
            products = []
        finally:
            browser.close()
    
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
