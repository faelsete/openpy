import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.251.211', username='root', password='14061986', timeout=10)

# Ler config atual
stdin, stdout, stderr = ssh.exec_command('cat ~/.openpy/openpy.json', timeout=10)
config = json.loads(stdout.read().decode('utf-8'))

# Atualizar provider
config['providers']['default']['api_key'] = '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'
config['providers']['default']['model'] = 'nvidia/nemotron-nano-12b-v2-vl'

# Salvar
sftp = ssh.open_sftp()
with sftp.file('/root/.openpy/openpy.json', 'w') as f:
    f.write(json.dumps(config, indent=2, ensure_ascii=False))
sftp.close()

print("Config atualizada:")
print(f"  Provider: {config['providers']['default']['type']}")
print(f"  Model: {config['providers']['default']['model']}")
print(f"  API Key: {config['providers']['default']['api_key'][:20]}...")

# Reiniciar telegram bot
stdin, stdout, stderr = ssh.exec_command('systemctl restart openpy-telegram', timeout=10)
stdout.read()
import time; time.sleep(3)

stdin, stdout, stderr = ssh.exec_command('systemctl is-active openpy-telegram', timeout=5)
print(f"\nService: {stdout.read().decode().strip()}")

ssh.close()
print("DONE - Manda mensagem pro bot agora!")
