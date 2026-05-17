# Skill: Diagnóstico de Servidor

## Contexto
O usuário quer diagnosticar e/ou consertar um servidor Linux.

## Comandos de diagnóstico essenciais

```bash
uptime                              # Tempo ligado, load average
free -h                             # Memória RAM
df -h                               # Espaço em disco
ss -tulpn                           # Portas abertas
systemctl --failed                  # Serviços falhados
journalctl -p err -n 80 --no-pager  # Últimos erros do sistema
top -bn1 | head -20                 # Processos consumindo mais
dmesg --level=err,warn | tail -30   # Erros de kernel
```

## Critérios de sucesso
- Load average < número de CPUs
- RAM livre > 10%
- Disco livre > 15% em partições críticas
- Zero serviços falhados
- Zero erros críticos recentes no journal

## Riscos comuns
- Reiniciar serviço pode derrubar dependências
- Limpar logs pode apagar evidências
- Matar processo pode corromper dados
