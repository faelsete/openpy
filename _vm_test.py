import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.251.211', username='root', password='14061986', timeout=10)

# Descobrir path correto do venv
stdin, stdout, stderr = ssh.exec_command('ls /root/openpy/.venv/bin/python* 2>&1; ls /root/.openpy/.venv/bin/python* 2>&1', timeout=10)
print("VENVS:", stdout.read().decode('utf-8', errors='replace').strip())

# Corrigir service com path correto
gateway_service = """[Unit]
Description=OpenPy Gateway + Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/openpy
ExecStart=/root/openpy/.venv/bin/python -m openpy.gateway.server
Restart=always
RestartSec=5
Environment=PYTHONIOENCODING=utf-8
Environment=HOME=/root
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openpy-gateway

[Install]
WantedBy=multi-user.target
"""

telegram_service = """[Unit]
Description=OpenPy Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/openpy
ExecStart=/root/openpy/.venv/bin/python -m openpy.cli.main telegram
Restart=always
RestartSec=5
Environment=PYTHONIOENCODING=utf-8
Environment=HOME=/root
StandardOutput=journal
StandardError=journal
SyslogIdentifier=openpy-telegram

[Install]
WantedBy=multi-user.target
"""

sftp = ssh.open_sftp()
with sftp.file('/etc/systemd/system/openpy-gateway.service', 'w') as f:
    f.write(gateway_service)
with sftp.file('/etc/systemd/system/openpy-telegram.service', 'w') as f:
    f.write(telegram_service)
sftp.close()

cmds = [
    'systemctl daemon-reload',
    'systemctl restart openpy-telegram',
    'sleep 3',
    'systemctl status openpy-telegram --no-pager 2>&1 | head -15',
    'journalctl -u openpy-telegram --no-pager -n 5 2>&1',
]

for cmd in cmds:
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=15)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    if out: print(out)
    print()

ssh.close()
print('DONE')
