# 07 · Lịch Sử Trò Chuyện (Chat History)

**Component:** `frontend-vue/src/components/ChatHistorySidebar.vue`
**Store:** `frontend-vue/src/stores/historyStore.js`
**File backend chính:** `spring-boot/.../controller/ChatHistoryController.java` — `/api/history/*`

---

Sidebar bên trái trong trang Chat lưu toàn bộ lịch sử hội thoại của người dùng vào PostgreSQL thông qua Spring Boot. Người dùng có thể quay lại đọc các phiên tư vấn trước, hoặc tiếp tục hỏi thêm trong cùng một phiên.

## Cách lưu trữ và tổ chức dữ liệu

Mỗi cuộc trò chuyện là một **session** riêng biệt lưu trong bảng `chat_sessions`. Mọi tin nhắn — cả câu hỏi lẫn câu trả lời AI — lưu trong bảng `chat_messages` với trường `citations` dạng JSON. Hệ thống lưu tin nhắn **ngay sau khi gửi/nhận**, không chờ đến cuối phiên — phòng mất dữ liệu nếu người dùng đóng tab giữa chừng.

```java
// ChatHistoryController.java — lưu message kèm citations
ChatMessage message = ChatMessage.builder()
    .id(UUID.randomUUID().toString())
    .sessionId(sessionId)
    .role(body.getOrDefault("role", "user"))      // "user" hoặc "assistant"
    .content(body.getOrDefault("content", ""))
    .citations(objectMapper.writeValueAsString(citations))  // JSON array
    .createdAt(LocalDateTime.now())
    .build();
messageRepo.save(message);
```

Khi tải lại một session cũ, Spring Boot trả về toàn bộ messages kèm citations đã parse:

```java
// ChatHistoryController.java — trả về messages với citations
@GetMapping("/sessions/{sessionId}/messages")
public ResponseEntity<?> getMessages(@PathVariable String sessionId) {
    String userId = currentUserId();  // lấy từ SecurityContext (không parse JWT lại)
    // Kiểm tra session thuộc user đang đăng nhập
    if (!session.getUserId().equals(userId)) return ResponseEntity.status(403).build();
    // Trả về messages kèm citations đã parse từ JSON string
}
```

## Bảo mật ở cấp session

Mỗi API đều kiểm tra session có thuộc user đang đăng nhập không — tránh user A đọc được lịch sử của user B. `currentUserId()` lấy từ `SecurityContextHolder` (đã được JwtAuthFilter set sẵn khi validate token), không parse lại JWT để tránh lỗi double-parsing.

## Mối quan hệ giữa Session và RAG Pipeline

Khi người dùng đang trong một session và tiếp tục hỏi, `chat_history` của session đó được gửi kèm request đến FastAPI. LLM nhìn vào lịch sử này để hiểu ngữ cảnh — nền tảng của Multi-turn conversation. Spring Boot không xử lý logic AI, chỉ lưu trữ và trả dữ liệu lịch sử khi được yêu cầu.

## Tại sao lịch sử lưu ở Spring Boot thay vì FastAPI?

Spring Boot dùng JPA/Hibernate quản lý nghiệp vụ thuần túy (users, sessions, messages) ổn định hơn. FastAPI tập trung xử lý AI pipeline. Việc tách ra giúp mỗi service độc lập — nếu AI pipeline bị lỗi hoặc restart, lịch sử chat vẫn truy cập được bình thường.

---

**API chính:** `GET /api/history/sessions` · `POST /api/history/sessions` · `GET /api/history/sessions/:id/messages` · `POST /api/history/sessions/:id/messages` · `DELETE /api/history/sessions/:id`
