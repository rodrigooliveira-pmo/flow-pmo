
# Dockerfile para projeto Flow-PMO
FROM python:3.11-slim

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema (ex: para pandas, openpyxl, etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential gcc libpq-dev git && \
	rm -rf /var/lib/apt/lists/*

# Copia todos os requirements
COPY requirements*.txt ./

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do projeto
COPY . .

# Define timezone e encoding padrão
ENV TZ=America/Sao_Paulo
ENV PYTHONIOENCODING=utf-8

# Variáveis de ambiente padrão (pode sobrescrever em runtime)
ENV FLOW_PMO_DASH_MODULE=dashboard_full
ENV FLOW_PMO_DASH_ATTR=app


# Porta padrão para produção/App Runner
EXPOSE 8080

# Comando de start para produção (App Runner/Gunicorn)
CMD ["gunicorn", "api.index:app", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--timeout", "300", \
     "--graceful-timeout", "60", \
     "--keep-alive", "5", \
     "--log-level", "info"]
