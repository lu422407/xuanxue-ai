FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY agents ./agents
COPY engines ./engines
COPY fusion ./fusion
COPY rag ./rag
COPY knowledge ./knowledge
COPY database ./database
COPY llm ./llm
COPY observability ./observability
COPY conftest.py ./

ENV XUANXUE_API_KEYS=${XUANXUE_API_KEYS:-dev-key-0001}
ENV DATABASE_URL=postgresql+psycopg2://xuanxue:xuanxue@postgres:5432/xuanxue

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]