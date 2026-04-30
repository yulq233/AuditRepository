import duckdb

conn = duckdb.connect('data/db/audit.db')

# 删除所有可能导致问题的索引
indexes_to_drop = [
    'idx_vouchers_project_id',
    'idx_vouchers_voucher_date',
    'idx_samples_project_id',
    'idx_samples_record_id'
]

for idx in indexes_to_drop:
    try:
        conn.execute(f'DROP INDEX IF EXISTS {idx}')
        print(f'Dropped {idx}')
    except Exception as e:
        print(f'Skip {idx}: {e}')

# 测试删除
print('\nTesting delete...')
try:
    result = conn.execute('DELETE FROM vouchers LIMIT 1')
    print(f'Deleted from vouchers')
    conn.commit()
except Exception as e:
    print(f'Error: {e}')

conn.close()
print('Done')