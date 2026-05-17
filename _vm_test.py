import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.251.211', username='root', password='14061986', timeout=10)

stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u openpy-telegram --no-pager -n 30 --since "2 min ago" 2>&1',
    timeout=15
)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
