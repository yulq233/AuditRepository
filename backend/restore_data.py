import duckdb
import json
import os

# 确保使用正确的数据库路径
conn = duckdb.connect('data/db/audit.db')

with open('data/backup.json', 'r', encoding='utf-8') as f:
    backup = json.load(f)

# 恢复projects
for row in backup['projects']['data']:
    try:
        conn.execute('INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?)', row)
    except Exception as e:
        print(f'Skip project: {e}')
print(f'Restored {len(backup["projects"]["data"])} projects')

# 恢复vouchers
for row in backup['vouchers']['data']:
    try:
        conn.execute('INSERT INTO vouchers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row)
    except Exception as e:
        print(f'Skip voucher {row[2]}: {e}')
print(f'Restored {len(backup["vouchers"]["data"])} vouchers')

# 恢复sampling_rules
for row in backup['sampling_rules']['data']:
    try:
        conn.execute('INSERT INTO sampling_rules VALUES (?, ?, ?, ?, ?, ?, ?)', row)
    except Exception as e:
        print(f'Skip rule: {e}')
print(f'Restored {len(backup["sampling_rules"]["data"])} rules')

# 恢复sampling_records（如果存在）
if 'sampling_records' in backup and backup['sampling_records']['data']:
    for row in backup['sampling_records']['data']:
        try:
            conn.execute('INSERT INTO sampling_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', row)
        except Exception as e:
            print(f'Skip sampling_record: {e}')
    print(f'Restored {len(backup["sampling_records"]["data"])} sampling_records')

# 恢复samples
for row in backup['samples']['data']:
    try:
        # 在最后添加record_id为None
        new_row = list(row) + [None]
        conn.execute('INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?)', new_row)
    except Exception as e:
        pass
print(f'Restored {len(backup["samples"]["data"])} samples')

conn.close()
print('Database restored!')