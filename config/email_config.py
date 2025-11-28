#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
QQ 邮箱配置

获取授权码步骤：
1. 登录 QQ 邮箱 (mail.qq.com)
2. 设置 -> 账户 -> POP3/SMTP服务 -> 开启
3. 生成授权码（不是登录密码）
"""

# QQ 邮箱 SMTP 配置
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465
SMTP_USER = "2407924554@qq.com"  # 改成你的 QQ 邮箱
SMTP_PASS = "jidifvqzpavudjce"  # 改成你的授权码（不是密码）

# 发件人名称
SENDER_NAME = "1688 以图搜货"

