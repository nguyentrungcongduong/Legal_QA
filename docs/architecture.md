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