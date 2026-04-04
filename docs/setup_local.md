# Thu tu setup local (Windows)

## 1) Cai Docker Desktop

Tai Docker Desktop tai [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) va cai dat.

Kiem tra:

```bash
docker --version
docker compose version
```

## 2) Cau truc project

Da tao san:

- `frontend/`
- `backend-java/`
- `backend-python/`
- `docker-compose.yml`
- `.env` va `.env.example`

## 3) Chay infrastructure

Tu thu muc goc project:

```bash
docker compose up -d postgres qdrant
```

Kiem tra:

```bash
docker ps
```

Qdrant dashboard:

- [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

Kiem tra PostgreSQL:

```bash
docker exec -it rag-postgres psql -U raguser -d ragdb
```

## 4) Schema PostgreSQL

File schema da duoc tao tai `backend-python/sql/init.sql`.
File nay duoc Docker tu dong chay khi volume PostgreSQL duoc khoi tao lan dau.

Kiem tra bang:

```bash
docker exec -it rag-postgres psql -U raguser -d ragdb -c "\dt"
```

Neu truoc do da tao volume cu va schema chua cap nhat, reset volume:

```bash
docker compose down -v
docker compose up -d postgres qdrant
```

## 5) Setup Python environment

```bash
cd backend-python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 6) Cai dat bien moi truong

File `.env` da co san o thu muc goc. Cap nhat gia tri that:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

## 7) Test ket noi

Tu thu muc `backend-python`:

```bash
python test_connections.py
```

Neu thanh cong se in:

- danh sach Qdrant collections
- danh sach bang PostgreSQL
- `Tat ca ket noi OK!`

## 8) Download embedding model

Tu thu muc `backend-python`:

```bash
python download_model.py
```

Model `BAAI/bge-m3` lon (~2GB), nen tai truoc ingestion.
