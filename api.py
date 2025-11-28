#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
1688 以图搜货 API 服务

支持通过图片文件或图片 URL 搜索产品
"""

import os
import tempfile
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests

from lib.ali1688 import ali1688
from lib.ali1688.search import fetch_product_links_async, get_search_url


app = FastAPI(
    title="1688 以图搜货 API",
    description="上传图片，获取 1688 相似产品链接",
    version="1.0.0"
)


class Product(BaseModel):
    title: str
    url: str
    offer_id: str


class SearchResponse(BaseModel):
    success: bool
    image_id: Optional[str] = None
    search_url: Optional[str] = None
    products: List[Product] = []
    error: Optional[str] = None


def upload_image_to_1688(image_path: str) -> dict:
    """上传图片到 1688"""
    upload = ali1688.Ali1688Upload()
    res = upload.upload(filename=image_path)
    return res.json()


async def search_products(image_path: str, limit: int = 5) -> SearchResponse:
    """搜索产品"""
    # 1. 上传图片
    data = upload_image_to_1688(image_path)
    
    if data.get("ret", [""])[0] != "SUCCESS::调用成功":
        return SearchResponse(success=False, error=f"上传失败: {data}")
    
    image_id = data.get("data", {}).get("imageId", "")
    if not image_id:
        return SearchResponse(success=False, error="未获取到 imageId")
    
    search_url = get_search_url(image_id)
    
    # 2. 获取产品链接（异步）
    products_data = await fetch_product_links_async(image_id, limit=limit, headless=True)
    products = [Product(**p) for p in products_data]
    
    return SearchResponse(
        success=True,
        image_id=image_id,
        search_url=search_url,
        products=products
    )


@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "1688 以图搜货 API",
        "version": "1.0.0",
        "endpoints": {
            "POST /search/upload": "上传图片文件搜索",
            "GET /search/url": "通过图片 URL 搜索"
        }
    }


@app.post("/search/upload", response_model=SearchResponse)
async def search_by_upload(
    file: UploadFile = File(..., description="要搜索的图片文件"),
    limit: int = Query(5, ge=1, le=20, description="返回产品数量")
):
    """
    上传图片文件搜索
    
    - **file**: 图片文件 (支持 jpg, jpeg, png)
    - **limit**: 返回产品数量，默认 5，最大 20
    """
    # 检查文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    # 保存临时文件
    suffix = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = await search_products(tmp_path, limit=limit)
        return result
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/search/url", response_model=SearchResponse)
async def search_by_url(
    image_url: str = Query(..., description="图片 URL"),
    limit: int = Query(5, ge=1, le=20, description="返回产品数量")
):
    """
    通过图片 URL 搜索
    
    - **image_url**: 图片的网络地址
    - **limit**: 返回产品数量，默认 5，最大 20
    """
    # 下载图片
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下载图片失败: {e}")
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name
    
    try:
        result = await search_products(tmp_path, limit=limit)
        return result
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

