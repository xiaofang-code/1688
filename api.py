#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
1688 以图搜货 API 服务

支持:
- 单张图片搜索
- 批量图片搜索（最多 3000 张）
- 处理完成后发送 Excel 到邮箱
"""

import os
import uuid
import asyncio
import tempfile
from typing import List, Optional, Dict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.header import Header
from email import encoders
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
import requests
import aiosmtplib
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

from lib.ali1688 import ali1688
from lib.ali1688.search import fetch_product_links_async, get_search_url
from lib.proxy import get_new_proxy, ProxyInfo
from config.email_config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SENDER_NAME


app = FastAPI(
    title="1688 以图搜货 API",
    description="上传图片，获取 1688 相似产品链接。支持批量处理 + 邮件通知。",
    version="2.0.0"
)


# ============== 任务存储 ==============
tasks_store: Dict[str, dict] = {}


# ============== 数据模型 ==============

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


class EmailBatchRequest(BaseModel):
    image_urls: List[str]
    email: str
    limit: int = 5


# ============== 核心函数 ==============

def upload_image_to_1688(image_path: str) -> dict:
    """上传图片到 1688"""
    upload = ali1688.Ali1688Upload()
    res = upload.upload(filename=image_path)
    return res.json()


async def search_products(
    image_path: str, 
    limit: int = 5,
    proxy_info: Optional[ProxyInfo] = None,  # 可指定代理
    max_retries: int = 3  # 最大重试次数
) -> SearchResponse:
    """搜索产品（带重试机制）"""
    import asyncio
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # 上传图片到 1688
            data = upload_image_to_1688(image_path)
            
            # 检查上传结果
            ret_msg = data.get("ret", [""])[0] if data.get("ret") else ""
            if ret_msg != "SUCCESS::调用成功":
                last_error = "上传失败"
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⚠️ 上传失败，{wait_time}秒后重试... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                return SearchResponse(success=False, error=last_error)
            
            image_id = data.get("data", {}).get("imageId", "")
            if not image_id:
                return SearchResponse(success=False, error="未获取到 imageId")
            
            search_url = get_search_url(image_id)
            products_data = await fetch_product_links_async(
                image_id, 
                limit=limit, 
                headless=True,
                proxy_info=proxy_info  # 传递指定的代理
            )
            products = [Product(**p) for p in products_data]
            
            return SearchResponse(
                success=True,
                image_id=image_id,
                search_url=search_url,
                products=products
            )
            
        except (TimeoutError, ConnectionError) as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"⚠️ 连接超时: {e}，{wait_time}秒后重试... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
                continue
            return SearchResponse(success=False, error=f"连接超时: {last_error}")
            
        except Exception as e:
            error_msg = str(e)
            # 检查是否是可重试的错误
            if any(keyword in error_msg for keyword in ["timeout", "timed out", "Connection aborted", "Connection reset"]):
                last_error = error_msg
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⚠️ {error_msg[:50]}...，{wait_time}秒后重试... ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
            return SearchResponse(success=False, error=error_msg)
    
    return SearchResponse(success=False, error=f"重试 {max_retries} 次后仍失败: {last_error}")


# ============== Excel 生成 ==============

def create_excel(results: List[dict]) -> BytesIO:
    """
    生成 Excel 文件
    表头：序号、原图URL、状态、产品链接
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "搜索结果"
    
    # 表头
    headers = ["序号", "原图URL", "状态", "产品链接"]
    ws.append(headers)
    
    # 设置表头样式
    for col in range(1, 5):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # 数据行
    for idx, result in enumerate(results, 1):
        row_num = idx + 1
        
        # 序号
        ws.cell(row=row_num, column=1, value=idx)
        
        # 原图 URL
        ws.cell(row=row_num, column=2, value=result.get("image_url", ""))
        
        # 状态
        if result.get("success"):
            ws.cell(row=row_num, column=3, value="成功")
            
            # 产品链接（5 个链接用逗号分隔）
            products = result.get("products", [])
            links = [p.get("url", "") for p in products[:5]]
            ws.cell(row=row_num, column=4, value=",".join(links))
        else:
            ws.cell(row=row_num, column=3, value="失败: " + result.get("error", "未知错误"))
            ws.cell(row=row_num, column=4, value="")
    
    # 调整列宽
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 60
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 150
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ============== 邮件发送 ==============

async def send_email_with_excel(to_email: str, excel_buffer: BytesIO, task_info: dict):
    """发送带 Excel 附件的邮件"""
    msg = MIMEMultipart()
    # RFC2047 编码中文发件人名称
    from email.utils import formataddr
    msg["From"] = formataddr((str(Header(SENDER_NAME, "utf-8")), SMTP_USER))
    msg["To"] = to_email
    msg["Subject"] = Header(f"1688 以图搜货结果 - {task_info['total']} 张图片", "utf-8")
    
    # 邮件正文
    body = f"""您好！

您提交的 1688 以图搜货任务已完成。

📋 任务信息：
━━━━━━━━━━━━━━━━━━━━━━━━
• 任务 ID: {task_info['task_id']}
• 图片数量: {task_info['total']}
• 成功数量: {task_info['success_count']}
• 失败数量: {task_info['fail_count']}
• 处理时间: {task_info['duration']} 秒
━━━━━━━━━━━━━━━━━━━━━━━━

请查看附件中的 Excel 文件获取详细结果。

Excel 表格说明：
• 序号：图片序号
• 原图URL：您提交的图片地址
• 状态：成功/失败
• 产品链接：5 个相似产品的链接（逗号分隔）

--
1688 以图搜货 API
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    # Excel 附件
    attachment = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    attachment.set_payload(excel_buffer.getvalue())
    encoders.encode_base64(attachment)
    filename = f"1688_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)
    
    # 发送邮件 - QQ 邮箱 465 端口使用 SSL
    import ssl
    context = ssl.create_default_context()
    
    async with aiosmtplib.SMTP(
        hostname=SMTP_HOST, 
        port=SMTP_PORT, 
        use_tls=True,
        tls_context=context
    ) as smtp:
        await smtp.login(SMTP_USER, SMTP_PASS)
        await smtp.send_message(msg)


# ============== 后台任务处理 ==============

async def process_email_batch_task(task_id: str, image_urls: List[str], email: str, limit: int):
    """后台处理批量任务并发送邮件"""
    task = tasks_store[task_id]
    task["status"] = "processing"
    start_time = datetime.now()
    
    results = []
    results_lock = asyncio.Lock()
    
    # 🚀 并行工作队列：3 个 worker 并行，每个 worker 内部串行（获取代理→使用→获取→使用）
    WORKER_COUNT = 3
    queue = asyncio.Queue()
    
    # 填充任务队列
    for i, url in enumerate(image_urls):
        await queue.put((i, url))
    
    async def worker(worker_id: int):
        """工作协程：从队列取任务，获取代理，执行搜索"""
        while True:
            try:
                index, url = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            
            result = {"image_url": url, "index": index}
            try:
                # 下载图片
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(response.content)
                    tmp_path = tmp.name
                
                try:
                    # 🔄 获取代理并立即使用（worker 内串行，不会空等）
                    proxy = get_new_proxy()
                    print(f"[Worker-{worker_id}] 🌐 使用代理: {proxy.server if proxy else 'None'}")
                    search_result = await search_products(tmp_path, limit=limit, proxy_info=proxy)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                
                result.update({
                    "success": search_result.success,
                    "products": [p.dict() for p in search_result.products] if search_result.products else [],
                    "error": search_result.error
                })
            except Exception as e:
                result.update({"success": False, "error": str(e), "products": []})
            
            async with results_lock:
                results.append(result)
                task["completed"] += 1
                print(f"[{task_id[:8]}] 进度: {task['completed']}/{task['total']}")
    
    print(f"[{task_id[:8]}] 开始处理 {len(image_urls)} 张图片（{WORKER_COUNT} 个 worker 并行）")
    
    # 启动 worker 并等待完成
    workers = [worker(i) for i in range(WORKER_COUNT)]
    await asyncio.gather(*workers)
    
    # 按原始顺序排序
    results.sort(key=lambda x: x.get("index", 0))
    
    # 统计
    success_count = sum(1 for r in results if r.get("success"))
    fail_count = len(results) - success_count
    duration = (datetime.now() - start_time).total_seconds()
    
    task_info = {
        "task_id": task_id,
        "total": len(results),
        "success_count": success_count,
        "fail_count": fail_count,
        "duration": round(duration, 1)
    }
    
    # 生成 Excel
    print(f"[{task_id[:8]}] 生成 Excel...")
    excel_buffer = create_excel(results)
    
    # 发送邮件
    try:
        print(f"[{task_id[:8]}] 发送邮件到 {email}...")
        await send_email_with_excel(email, excel_buffer, task_info)
        task["status"] = "completed"
        task["message"] = f"结果已发送到 {email}"
        print(f"[{task_id[:8]}] ✅ 完成！邮件已发送")
    except Exception as e:
        task["status"] = "email_failed"
        task["message"] = f"处理完成但邮件发送失败: {e}"
        print(f"[{task_id[:8]}] ❌ 邮件发送失败: {e}")
    
    task["completed"] = len(results)
    task["success_count"] = success_count
    task["fail_count"] = fail_count
    task["duration"] = round(duration, 1)


# ============== API 端点 ==============

@app.get("/")
async def root():
    """API 根路径"""
    return {
        "name": "1688 以图搜货 API",
        "version": "2.0.0",
        "endpoints": {
            "POST /search/upload": "单张图片搜索",
            "GET /search/url": "通过 URL 搜索",
            "POST /batch/email": "批量搜索 + 邮件通知（最多 3000 张）",
            "GET /batch/status/{task_id}": "查询任务状态"
        }
    }


@app.post("/search/upload", response_model=SearchResponse)
async def search_by_upload(
    file: UploadFile = File(..., description="要搜索的图片文件"),
    limit: int = Query(5, ge=1, le=20, description="返回产品数量")
):
    """单张图片搜索"""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")
    
    suffix = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        result = await search_products(tmp_path, limit=limit)
        return result
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.get("/search/url", response_model=SearchResponse)
async def search_by_url(
    image_url: str = Query(..., description="图片 URL"),
    limit: int = Query(5, ge=1, le=20, description="返回产品数量")
):
    """通过 URL 搜索"""
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下载图片失败: {e}")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name
    
    try:
        result = await search_products(tmp_path, limit=limit)
        return result
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/batch/email")
async def batch_search_with_email(
    request: EmailBatchRequest,
    background_tasks: BackgroundTasks
):
    """
    批量搜索 + 邮件通知
    
    - **image_urls**: 图片 URL 列表（最多 3000 个）
    - **email**: 结果发送到的邮箱地址
    - **limit**: 每张图片返回的产品数量（默认 5）
    
    💡 提交后立即返回，处理完成后发送 Excel 到邮箱
    
    Excel 格式：序号、原图URL、状态、产品链接（5个链接用逗号分隔）
    """
    if len(request.image_urls) > 3000:
        raise HTTPException(status_code=400, detail="最多支持 3000 个 URL")
    
    if len(request.image_urls) == 0:
        raise HTTPException(status_code=400, detail="请提供至少 1 个 URL")
    
    if not request.email or "@" not in request.email:
        raise HTTPException(status_code=400, detail="请提供有效的邮箱地址")
    
    # 创建任务
    task_id = str(uuid.uuid4())
    tasks_store[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "total": len(request.image_urls),
        "completed": 0,
        "success_count": 0,
        "fail_count": 0,
        "email": request.email,
        "created_at": datetime.now().isoformat(),
        "message": ""
    }
    
    # 后台处理
    background_tasks.add_task(
        process_email_batch_task, 
        task_id, 
        request.image_urls, 
        request.email, 
        request.limit
    )
    
    # 预估时间（每张约 15-30 秒，3 并发）
    estimated_minutes = (len(request.image_urls) * 20) // 60 // 3
    
    return {
        "task_id": task_id,
        "status": "pending",
        "total": len(request.image_urls),
        "email": request.email,
        "message": f"任务已提交！处理完成后结果将发送到 {request.email}",
        "estimated_time": f"约 {estimated_minutes} - {estimated_minutes * 2} 分钟"
    }


@app.get("/batch/status/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    if task_id not in tasks_store:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_store[task_id]
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "total": task["total"],
        "completed": task["completed"],
        "success_count": task.get("success_count", 0),
        "fail_count": task.get("fail_count", 0),
        "progress": f"{task['completed']}/{task['total']}",
        "email": task["email"],
        "message": task.get("message", ""),
        "duration": task.get("duration"),
        "created_at": task["created_at"]
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "active_tasks": len([t for t in tasks_store.values() if t["status"] == "processing"])
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
