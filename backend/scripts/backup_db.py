import subprocess
import os
import datetime
import time

# --- 全局配置区域 (涵盖 3 个数据库) ---
BACKUP_DIR = "./backups"

# 定义所有需要备份的数据库配置
DATABASES = [
    {
        "type": "mysql",
        "container": "library_mysql",  # 确保与 docker-compose 里的名字一致
        "user": "root",
        "pass": "1234",
        "db_name": "library_mysql"
    },
    {
        "type": "postgres",
        "container": "library_pg",
        "user": "postgres",  # PG 默认超级用户
        "pass": "123456",
        "db_name": "library_pg"
    },
    {
        "type": "mssql",  # SQL Server 备份机制较特殊
        "container": "library_sqlserver",
        "user": "sa",
        "pass": "Password123!",  # SQL Server 强密码
        "db_name": "library_mssql"
    }
]

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"📁 Created directory: {directory}")

def backup_all():
    ensure_dir(BACKUP_DIR)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"🚀 Starting FULL SYSTEM BACKUP at {timestamp}...\n")

    for db in DATABASES:
        print(f"--- Processing {db['type'].upper()} ({db['container']}) ---")
        
        try:
            filename = f"{BACKUP_DIR}/{db['type']}_{db['db_name']}_{timestamp}"
            
            # --- 策略 A: MySQL (使用 mysqldump) ---
            if db['type'] == 'mysql':
                full_path = f"{filename}.sql"
                cmd = f"docker exec {db['container']} mysqldump -u{db['user']} -p{db['pass']} {db['db_name']} > {full_path}"
                run_command(cmd, full_path)

            # --- 策略 B: PostgreSQL (使用 pg_dump) ---
            elif db['type'] == 'postgres':
                full_path = f"{filename}.sql"
                # PG 需要通过环境变量传递密码，或者在 exec 中显式指定
                # 这里使用简单的连接串方式 (docker exec 中直接运行 pg_dump)
                cmd = f"docker exec {db['container']} pg_dump -U {db['user']} {db['db_name']} > {full_path}"
                run_command(cmd, full_path)

            # --- 策略 C: SQL Server (特殊处理) ---
            elif db['type'] == 'mssql':
                # SQL Server 通常生成 .bak 文件在容器内，然后复制出来
                bak_file_inner = f"/var/opt/mssql/data/{db['db_name']}_backup.bak"
                full_path = f"{filename}.bak"
                
                # 1. 在容器内执行 T-SQL 备份命令
                sql_cmd = f"BACKUP DATABASE [{db['db_name']}] TO DISK = '{bak_file_inner}' WITH FORMAT, INIT"
                # SQL Server 的工具路径通常是 /opt/mssql-tools/bin/sqlcmd
                exec_cmd = f'docker exec {db['container']} /opt/mssql-tools/bin/sqlcmd -S localhost -U {db['user']} -P "{db['pass']}" -Q "{sql_cmd}"'
                
                print(f"   Step 1: Generating .bak inside container...")
                subprocess.run(exec_cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
                
                # 2. 将 .bak 文件复制到宿主机
                print(f"   Step 2: Copying to host...")
                cp_cmd = f"docker cp {db['container']}:{bak_file_inner} {full_path}"
                subprocess.run(cp_cmd, shell=True, check=True)
                print(f"   ✅ Success! Saved to: {full_path}")

        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to backup {db['container']}. Is it running?")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        print("") # 空行

    print("✨ All backup tasks completed!")

def run_command(cmd, filepath):
    # 辅助函数：执行命令并打印结果
    subprocess.run(cmd, shell=True, check=True)
    # 检查文件是否生成且不为空
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"   ✅ Success! Saved to: {filepath}")
    else:
        print(f"   ⚠️ Warning: File created but looks empty.")

if __name__ == "__main__":
    backup_all()