Kiến trúc Hybrid Spring Boot + Python FastAPI

Tổng quan
Vue.js → Spring Boot (API Gateway + Orchestration) → Python FastAPI (RAG Core) → Qdrant + PostgreSQL

Layer 1: Vue.js Frontend
Gồm 4 màn hình chính: Chat UI, Citation Viewer, Model Comparison Dashboard, Evaluation Dashboard.

Layer 2: Spring Boot Backend
API Gateway — xác thực JWT, rate limiting, routing request đến đúng service bên trong.
Orchestration Service — nhận query từ Vue, gọi sang Python FastAPI, nhận kết quả về, lưu history vào PostgreSQL, trả response cho Vue. Đây là service quan trọng nhất của Spring Boot.
User Service — quản lý tài khoản, lịch sử chat, API key của từng user.
Spring Boot không xử lý AI gì hết — nó chỉ điều phối và quản lý business logic.

Layer 3: Python FastAPI — RAG Core
Đây là nơi toàn bộ AI logic chạy. Spring Boot gọi vào đây qua REST.
Query Guard — kiểm tra câu hỏi có trong domain luật giao thông không. Nếu không thì trả về luôn, không đi tiếp.
Retriever — hybrid search kết hợp BM25 (keyword exact match) + Dense embedding (semantic search). Trả về top 20 chunks liên quan nhất.
Reranker — cross-encoder lọc lại top 5 từ 20 chunks, loại bỏ chunks trông có vẻ liên quan nhưng thực ra không đúng.
Conflict Detector — phát hiện mâu thuẫn giữa các văn bản luật khác nhau, ưu tiên văn bản có hiệu lực mới hơn.
Generator + Citation Builder — ghép chunks vào prompt template, gọi LLM, parse citation từ output, trả về answer kèm danh sách điều luật trích dẫn.
LLM Router — điều hướng đến GPT-4o, Gemini, hoặc Claude tùy config. Dùng cho cả RAG mode lẫn vanilla mode khi compare.
Evaluation Service — chạy RAGAS, tính faithfulness, citation precision, hallucination rate trên golden test set.

Layer 4: Storage
Qdrant — lưu vectors và metadata của từng chunk (tên luật, số điều, số khoản, ngày hiệu lực, trang PDF).
PostgreSQL — lưu user, lịch sử chat, metadata văn bản pháp luật, kết quả evaluation.
Ingestion Pipeline — script Python chạy offline: đọc PDF → smart chunk theo điều/khoản → embed → lưu vào Qdrant kèm metadata.

Luồng dữ liệu khi user hỏi
1. User gõ câu hỏi trên Vue
2. Vue gọi POST /api/chat → Spring Boot
3. Spring Boot xác thực JWT → gọi Python /ai/query
4. Python: Query Guard → Retriever → Reranker → Conflict Detector → Generator
5. Generator gọi LLM → parse citation → trả về Python response
6. Python trả JSON về Spring Boot
7. Spring Boot lưu history vào PostgreSQL → trả response về Vue
8. Vue hiển thị answer + citation panel

Luồng khi chạy so sánh model
1. User nhấn Compare trên Vue
2. Spring Boot gọi Python /ai/compare
3. Python gọi song song 3 pipeline:
   - RAG pipeline đầy đủ (hybrid + reranker + prompt cứng)
   - GPT-4o vanilla (chỉ câu hỏi, không có context)
   - Gemini vanilla (chỉ câu hỏi, không có context)
4. Trả về 3 kết quả + metrics
5. Vue render 3 cột so sánh

Giao tiếp giữa Spring Boot và Python
REST API đơn giản. Spring Boot giữ một PythonAIClient bean, gọi HTTP sang http://python-service:8000. Toàn bộ contract là JSON — Spring Boot không biết gì về RAG, Python không biết gì về user hay auth.

Deployment
Docker Compose chạy 5 container: vue-frontend, spring-backend, python-ai, postgres, qdrant. Một lệnh docker-compose up là chạy hết toàn bộ hệ thống.



/////Chi Tiết kiến trúc 
Spring Boot chịu trách nhiệm gì
API Gateway — JWT auth, rate limiting, routing request đến đúng service. User chưa login thì chặn ở đây, không đi tiếp được.
Orchestration Service — đây là "não" của Spring Boot. Nhận query từ Vue, gọi Python FastAPI qua REST, nhận kết quả về, lưu history vào PostgreSQL, rồi trả response cho Vue. Spring Boot không tự xử lý AI gì hết — nó chỉ điều phối.
User Service — quản lý tài khoản, lưu lịch sử chat, quản lý API key của từng user nếu mày muốn cho user tự bring API key của họ.
java// Orchestration Service — core của Spring Boot
@Service
public class OrchestrationService {

    @Autowired private PythonAIClient pythonClient;
    @Autowired private ChatHistoryRepository historyRepo;

    public ChatResponse processQuery(String userId, String query) {

        // Bước 1: gọi Python FastAPI
        AIResponse aiResponse = pythonClient.query(
            AIRequest.builder()
                .query(query)
                .userId(userId)
                .build()
        );

        // Bước 2: lưu history vào PostgreSQL
        historyRepo.save(ChatHistory.builder()
            .userId(userId)
            .query(query)
            .answer(aiResponse.getAnswer())
            .citations(aiResponse.getCitations())
            .faithfulnessScore(aiResponse.getMetrics().getFaithfulness())
            .createdAt(LocalDateTime.now())
            .build()
        );

        // Bước 3: trả về Vue
        return ChatResponse.from(aiResponse);
    }
}

Python FastAPI chịu trách nhiệm gì
Toàn bộ AI logic nằm ở đây — Spring Boot không biết RAG là gì, không biết embedding là gì.
python# main.py — entry point
@app.post("/ai/query")
async def process_query(request: AIRequest):

    # 1. Guard — check có trong domain không
    intent = query_guard.classify(request.query)
    if intent == "OUT_OF_DOMAIN":
        return AIResponse.out_of_domain()

    # 2. Retrieve — hybrid search
    chunks = retriever.hybrid_search(request.query, top_k=20)

    # 3. Rerank — lọc lại top 5
    reranked = reranker.rerank(request.query, chunks, top_k=5)

    # 4. Conflict detection
    conflicts = conflict_detector.detect(reranked)

    # 5. Generate + citation
    response = generator.generate(request.query, reranked, conflicts)

    return response

@app.post("/ai/evaluate")
async def run_evaluation(test_cases: list[TestCase]):
    return evaluation_service.run(test_cases)

@app.post("/ai/compare")  
async def compare_models(request: CompareRequest):
    return llm_router.compare_all(request.query)

Giao tiếp giữa Spring Boot và Python
Dùng REST đơn giản nhất — Spring Boot gọi HTTP sang Python, nhận JSON về.
java// Python AI Client trong Spring Boot
@Component
public class PythonAIClient {

    @Value("${python.service.url}")
    private String pythonUrl;  // http://localhost:8000

    private final RestTemplate restTemplate;

    public AIResponse query(AIRequest request) {
        return restTemplate.postForObject(
            pythonUrl + "/ai/query",
            request,
            AIResponse.class
        );
    }

    public CompareResponse compare(String query) {
        return restTemplate.postForObject(
            pythonUrl + "/ai/compare",
            Map.of("query", query),
            CompareResponse.class
        );
    }
}
Nếu sau này mày muốn nâng cấp lên gRPC để nhanh hơn thì chỉ cần đổi client này — Spring Boot và Python không biết gì về nhau ngoài contract này.

Docker Compose để chạy cả hệ thống
Đây là cách mày run local và cũng là cách demo — một lệnh duy nhất chạy hết:
yamlversion: '3.8'
services:

  vue-frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [spring-backend]

  spring-backend:
    build: ./backend-java
    ports: ["8080:8080"]
    environment:
      - PYTHON_SERVICE_URL=http://python-ai:8000
      - DATABASE_URL=jdbc:postgresql://postgres:5432/ragdb
    depends_on: [postgres, python-ai]

  python-ai:
    build: ./backend-python
    ports: ["8000:8000"]
    environment:
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on: [qdrant]

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ragdb
      POSTGRES_PASSWORD: secret
    volumes: [postgres_data:/var/lib/postgresql/data]

  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes: [qdrant_data:/qdrant/storage]

Thứ tự setup môi trường
Ngày 1:  Docker Compose chạy được Qdrant + PostgreSQL
Ngày 2:  Python FastAPI hello world, Spring Boot gọi được sang Python
Ngày 3:  Ingestion pipeline — nhét 1 file PDF luật vào Qdrant
Ngày 4:  RAG pipeline end-to-end chạy được câu đầu tiên
Sau đó:  Add feature dần — citation, compare, evaluation