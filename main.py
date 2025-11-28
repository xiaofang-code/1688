#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
1688 以图搜货 - 支持自动获取产品链接
可部署为 API 服务
"""

from typing import List, Dict
from lib import alibaba, yiwugo
from lib.ali1688 import ali1688
from lib.ali1688.search import fetch_product_links, print_product_links, get_search_url
from lib.world_taobao.world_taobao import WorldTaobao


def search_1688_by_image(image_path: str, limit: int = 5) -> Dict:
    """
    1688 以图搜货 - 获取产品链接
    
    Args:
        image_path: 图片文件路径
        limit: 返回产品数量限制，默认5个
        
    Returns:
        {
            "success": bool,
            "image_id": str,
            "search_url": str,
            "products": [{"title": "...", "url": "...", "offer_id": "..."}, ...]
        }
    """
    result = {
        "success": False,
        "image_id": "",
        "search_url": "",
        "products": []
    }
    
    # 1. 上传图片
    upload = ali1688.Ali1688Upload()
    res = upload.upload(filename=image_path)
    data = res.json()
    
    if data.get("ret", [""])[0] != "SUCCESS::调用成功":
        result["error"] = f"上传失败: {data}"
        return result
    
    image_id = data.get("data", {}).get("imageId", "")
    if not image_id:
        result["error"] = "未获取到 imageId"
        return result
    
    result["image_id"] = image_id
    result["search_url"] = get_search_url(image_id)
    
    # 2. 获取产品链接
    products = fetch_product_links(image_id, limit=limit, headless=True)
    result["products"] = products
    result["success"] = True
    
    return result


def demo_1688_image_search(path: str, limit: int = 5):
    """1688 以图搜货示例（带产品链接）"""
    print("\n" + "=" * 60)
    print("📸 1688 以图搜货")
    print("=" * 60)
    
    result = search_1688_by_image(path, limit=limit)
    
    if not result["success"]:
        print(f"❌ 失败: {result.get('error', '未知错误')}")
        return None
    
    print(f"✅ 图片上传成功! imageId: {result['image_id']}")
    print(f"🔗 搜索链接: {result['search_url']}")
    
    if result["products"]:
        print_product_links(result["products"])
    else:
        print("⚠️ 未获取到产品链接")
    
    return result


def demo_taobao_image_search(path: str):
    """淘宝以图搜货示例"""
    print("\n" + "=" * 60)
    print("📸 淘宝以图搜货")
    print("=" * 60)
    
    taobao_upload = WorldTaobao()
    res = taobao_upload.upload(filename=path)
    
    if res.json().get("data"):
        print("✅ 淘宝图片上传成功!")
    else:
        print("❌ 淘宝图片上传失败")


def demo_alibaba_image_search(path: str):
    """阿里巴巴国际站以图搜货示例"""
    print("\n" + "=" * 60)
    print("📸 阿里巴巴国际站以图搜货")
    print("=" * 60)
    
    upload_handler = alibaba.Upload()
    image_key = upload_handler.upload(filename=path)
    print(f"✅ 图片上传成功! image_key: {image_key}")
    
    image_search = alibaba.ImageSearch()
    req = image_search.search(image_key=image_key)
    print(f"🔗 搜索链接: {req.url}")


def demo_yiwugo_image_search(path: str):
    """义乌购以图搜货示例"""
    print("\n" + "=" * 60)
    print("📸 义乌购以图搜货")
    print("=" * 60)
    
    yiwugo_handler = yiwugo.YiWuGo()
    res = yiwugo_handler.upload(path)
    
    if "图片搜索" in res.text:
        print("✅ 义乌购搜索成功!")
    else:
        print("❌ 义乌购搜索失败")


if __name__ == "__main__":
    path = "data/down.jpeg"
    
    # 1688 以图搜货（获取前5个产品链接）
    demo_1688_image_search(path, limit=5)
    
    # 淘宝以图搜货
    demo_taobao_image_search(path)
    
    # 阿里巴巴国际站
    demo_alibaba_image_search(path)
    
    # 义乌购
    demo_yiwugo_image_search(path)
