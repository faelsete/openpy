import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('207.180.251.211', username='root', password='14061986', timeout=10)

# Verificar se a resposta foi enviada ao telegram
stdin, stdout, stderr = ssh.exec_command(
    'journalctl -u openpy-telegram --no-pager -n 60 2>&1 | grep -i -E "(erro|error|mensagem|send|task|resposta)"',
    timeout=15
)
print("FILTERED LOGS:")
print(stdout.read().decode('utf-8', errors='replace'))

# Testar envio manual
test = """
import httpx, asyncio

async def main():
    TOKEN = "8852005678:AAHsjLggeQD2mAeuv4lgQ5QlQuJYCbosGJw"
    CHAT_ID = 1050410410
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": "Teste direto: Pipeline funcionou! O Nemotron respondeu via NVIDIA NIM."}
        )
        print("Envio direto:", r.json().get("ok"))

asyncio.run(main())
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_send2.py', 'w') as f:
    f.write(test)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(
    'cd ~/openpy && source .venv/bin/activate && python /tmp/test_send2.py 2>&1',
    timeout=15
)
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
