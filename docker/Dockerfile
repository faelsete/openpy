FROM python:3.11-slim

# Metadados
LABEL maintainer="OpenPy Team"
LABEL description="OpenPy — Ecossistema operacional agêntico"

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV OPENPY_HOME=/root/.openpy

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    ffmpeg \
    htop \
    net-tools \
    iproute2 \
    dnsutils \
    sudo \
    vim \
    jq \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instalar ngrok
RUN curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok-v3-stable-linux-amd64.tgz \
    | tar xz -C /usr/local/bin

# Diretório de trabalho
WORKDIR /opt/openpy

# Copiar projeto
COPY . .

# Instalar dependências Python
RUN pip install --no-cache-dir -e .

# Criar diretórios persistentes
RUN mkdir -p $OPENPY_HOME/data $OPENPY_HOME/logs $OPENPY_HOME/skills $OPENPY_HOME/workspace

# Portas
EXPOSE 18790

# Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["openpy", "gateway", "start"]
