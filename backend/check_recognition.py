"""
检查附件识别结果是否正确保存到数据库
"""
import sys
sys.path.insert(0, '.')

from app.core.database import get_db_cursor

def check_attachments():
    with get_db_cursor() as cursor:
        # 检查表结构
        print("=== 检查 voucher_attachments 表结构 ===")
        cursor.execute("PRAGMA table_info(voucher_attachments)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col}")

        print("\n=== 检查附件数据 ===")
        cursor.execute("""
            SELECT id, file_name, recognition_result
            FROM voucher_attachments
            ORDER BY uploaded_at DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        for row in rows:
            print(f"\nID: {row[0][:8]}...")
            print(f"文件名: {row[1]}")
            print(f"识别结果: {row[2][:100] if row[2] else 'NULL'}...")

if __name__ == "__main__":
    check_attachments()
