import duckdb
import os
from pathlib import Path

# 数据库路径
db_path = "data/db/audit.db"
if not os.path.exists(db_path):
    db_path = "data/audit.db"

print(f"Connecting to database: {db_path}")
conn = duckdb.connect(db_path)

# 查询附件表
print("\n=== voucher_attachments 表结构 ===")
result = conn.execute("PRAGMA table_info('voucher_attachments')").fetchall()
for row in result:
    print(row)

print("\n=== 附件记录 ===")
result = conn.execute("SELECT id, voucher_id, file_name, file_path, file_size FROM voucher_attachments LIMIT 10").fetchall()
for row in result:
    print(f"ID: {row[0]}")
    print(f"  Voucher ID: {row[1]}")
    print(f"  File Name: {row[2]}")
    print(f"  File Path: {row[3]}")
    print(f"  File Size: {row[4]}")
    print()

# 查询项目表，看看有哪些项目
print("\n=== 项目列表 ===")
result = conn.execute("SELECT id, name FROM projects LIMIT 10").fetchall()
for row in result:
    print(f"Project ID: {row[0]}, Name: {row[1]}")

# 查询凭证表，看看有哪些凭证
print("\n=== 凭证列表（前5个）===")
result = conn.execute("SELECT id, project_id, voucher_no FROM vouchers LIMIT 5").fetchall()
for row in result:
    print(f"Voucher ID: {row[0]}, Project ID: {row[1]}, Voucher No: {row[2]}")

conn.close()