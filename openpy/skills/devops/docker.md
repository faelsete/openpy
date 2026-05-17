# Skill: Docker / Docker Compose

## Contexto
O usuário tem problemas com Docker ou Docker Compose.

## Diagnóstico essencial

```bash
docker --version
docker compose version
docker ps -a                        # Todos os containers (inclusive parados)
docker compose ps                   # Status dos serviços do compose
docker compose logs --tail=100      # Últimos logs
docker compose config               # Validar arquivo compose
docker system df                    # Uso de disco pelo Docker
docker network ls                   # Redes
docker volume ls                    # Volumes
```

## Problemas mais comuns

1. **Container não inicia**: Verificar logs, .env, portas em uso
2. **Porta em uso**: `ss -tulpn | grep <PORTA>` para identificar conflito
3. **Volume sem permissão**: Verificar ownership dos diretórios mapeados
4. **Rede**: Containers não se encontram → verificar network e service names
5. **Imagem desatualizada**: `docker compose pull` antes de `up`
6. **Dependência**: Serviço depende de outro que não subiu → healthcheck

## Sequência recomendada para "não sobe"

```bash
docker compose down
docker compose config              # Validar syntax
docker compose pull                # Atualizar imagens
docker compose up -d               # Subir
docker compose ps                  # Verificar
docker compose logs --tail=50      # Checar erros
```

## Riscos
- `docker system prune -a` remove TUDO (imagens, volumes, containers parados)
- `docker compose down -v` apaga VOLUMES (dados persistentes)
