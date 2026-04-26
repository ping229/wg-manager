#!/usr/bin/env python3
"""
数据库迁移脚本
用于添加新字段到现有数据库
"""

import sqlite3
import os

# 默认数据库路径
DB_PATH = '/opt/wg-manager/data/wg.db'


def migrate():
    print(f"数据库路径: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("数据库文件不存在，将在服务启动时自动创建")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查nodes表是否有blocked_patterns列
    cursor.execute("PRAGMA table_info(nodes)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'blocked_patterns' not in columns:
        print("添加 nodes.blocked_patterns 列...")
        cursor.execute("ALTER TABLE nodes ADD COLUMN blocked_patterns TEXT")
        conn.commit()
        print("完成")
    else:
        print("blocked_patterns 列已存在")

    conn.close()
    print("迁移完成")


if __name__ == '__main__':
    migrate()
