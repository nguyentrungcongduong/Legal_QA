# Legal QA - Runbook

## 1) Retriever test

```bash
cd backend-python
python test_retriever.py
```

## 2) FastAPI endpoints

```bash
cd backend-python
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `POST /ai/query`
- `POST /ai/compare`
- `POST /ai/evaluate`

## 3) End-to-end API test (Postman)

Base URL: `http://localhost:8000`

### Query

`POST /ai/query`

```json
{
  "question": "Vượt đèn đỏ xe máy bị phạt bao nhiêu?",
  "top_k": 5
}
```

### Compare

`POST /ai/compare`

```json
{
  "question_a": "Vượt đèn đỏ xe máy bị phạt bao nhiêu?",
  "question_b": "Không đội mũ bảo hiểm bị phạt sao?",
  "top_k": 5
}
```

### Evaluate

`POST /ai/evaluate`

```json
{
  "cases": [
    {
      "question": "Vượt đèn đỏ xe máy bị phạt bao nhiêu?",
      "expected_keywords": ["phạt", "điều"]
    }
  ],
  "top_k": 5
}
```

## 4) Spring Boot

### Orchestration Service

```bash
cd spring-boot/orchestration-service
mvn spring-boot:run
```

Runs on `http://localhost:8081`, proxies to Python (`http://localhost:8000`).

### API Gateway

```bash
cd spring-boot/gateway
mvn spring-boot:run
```

Runs on `http://localhost:8080`, proxies to orchestration service.

Client calls:

- `POST http://localhost:8080/api/ai/query`
- `POST http://localhost:8080/api/ai/compare`
- `POST http://localhost:8080/api/ai/evaluate`

## 5) Vue.js UI

```bash
cd frontend-vue
npm install
npm run dev
```

Open `http://localhost:5173`.
