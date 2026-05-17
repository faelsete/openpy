# Skill: Firewall e Portas

## Contexto
O usuário quer gerenciar portas e regras de firewall.

## Diagnóstico

```bash
ss -tulpn                          # Portas em uso
ufw status verbose                 # Status do UFW
iptables -L -n --line-numbers      # Regras iptables
nft list ruleset                   # Regras nftables
```

## UFW (mais comum)

```bash
ufw allow 80/tcp                   # Liberar porta HTTP
ufw allow 443/tcp                  # Liberar HTTPS
ufw allow from 192.168.1.0/24     # Liberar rede local
ufw deny 22/tcp                    # Bloquear SSH (CUIDADO!)
ufw status numbered                # Listar regras numeradas
ufw delete <NUMERO>                # Remover regra
```

## Riscos CRÍTICOS
- Bloquear porta SSH (22) = perder acesso ao servidor
- `ufw enable` sem regra de SSH = trancado para fora
- Abrir tudo (0.0.0.0:0) = vulnerável a ataques

## Rollback
- SEMPRE garantir regra SSH antes de ativar firewall
- Manter acesso console/IPMI como fallback
