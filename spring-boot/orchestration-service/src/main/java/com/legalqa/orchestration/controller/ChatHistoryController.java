package com.legalqa.orchestration.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.legalqa.orchestration.model.ChatMessage;
import com.legalqa.orchestration.model.ChatSession;
import com.legalqa.orchestration.repository.ChatMessageRepository;
import com.legalqa.orchestration.repository.ChatSessionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.*;

@RestController
@RequestMapping("/api/history")
@RequiredArgsConstructor
public class ChatHistoryController {

    private final ChatSessionRepository sessionRepo;
    private final ChatMessageRepository messageRepo;
    private final ObjectMapper objectMapper;

    /**
     * Lấy userId từ SecurityContext đã được JwtAuthFilter set sẵn.
     * KHÔNG parse lại JWT — tránh double-parsing gây lỗi 401.
     */
    private String currentUserId() {
        return (String) SecurityContextHolder.getContext()
                .getAuthentication()
                .getPrincipal();
    }

    // ── GET /api/history/sessions ──────────────────────────────────
    @GetMapping("/sessions")
    public ResponseEntity<?> getSessions() {
        String userId = currentUserId();
        List<ChatSession> sessions = sessionRepo.findByUserIdOrderByCreatedAtDesc(userId);
        return ResponseEntity.ok(sessions);
    }

    // ── GET /api/history/sessions/{id}/messages ────────────────────
    @GetMapping("/sessions/{sessionId}/messages")
    public ResponseEntity<?> getMessages(@PathVariable String sessionId) {
        String userId = currentUserId();

        ChatSession session = sessionRepo.findById(sessionId).orElse(null);
        if (session == null) return ResponseEntity.notFound().build();
        if (!session.getUserId().equals(userId)) return ResponseEntity.status(403).body("Không có quyền");

        List<ChatMessage> messages = messageRepo.findBySessionIdOrderByCreatedAtAsc(sessionId);

        List<Map<String, Object>> result = messages.stream()
                .map(m -> {
                    Map<String, Object> map = new LinkedHashMap<>();
                    map.put("role",      m.getRole());
                    map.put("content",   m.getContent());
                    map.put("createdAt", m.getCreatedAt() != null ? m.getCreatedAt().toString() : null);
                    List<?> citations = List.of();
                    if (m.getCitations() != null && !m.getCitations().isBlank()) {
                        try {
                            citations = objectMapper.readValue(m.getCitations(), new TypeReference<List<?>>() {});
                        } catch (Exception ignored) {}
                    }
                    map.put("citations", citations);
                    return map;
                })
                .toList();

        return ResponseEntity.ok(result);
    }

    // ── POST /api/history/sessions/{id}/messages ───────────────────
    @PostMapping("/sessions/{sessionId}/messages")
    public ResponseEntity<?> saveMessage(
            @PathVariable String sessionId,
            @RequestBody Map<String, Object> body) {

        String userId = currentUserId();

        ChatSession session = sessionRepo.findById(sessionId).orElse(null);
        if (session == null) {
            System.err.println("[saveMessage] Session not found in DB: " + sessionId);
            return ResponseEntity.status(404).body(Map.of("error", "Session không tồn tại: " + sessionId));
        }
        if (!session.getUserId().equals(userId)) return ResponseEntity.status(403).body("Không có quyền");

        String citationsJson = "[]";
        Object citations = body.get("citations");
        if (citations != null) {
            try { citationsJson = objectMapper.writeValueAsString(citations); }
            catch (Exception ignored) {}
        }

        ChatMessage message = ChatMessage.builder()
                .id(UUID.randomUUID().toString())
                .sessionId(sessionId)
                .role(String.valueOf(body.getOrDefault("role", "user")))
                .content(String.valueOf(body.getOrDefault("content", "")))
                .citations(citationsJson)
                .createdAt(LocalDateTime.now())
                .build();

        messageRepo.save(message);
        return ResponseEntity.ok(Map.of("id", message.getId(), "saved", true));
    }

    // ── POST /api/history/sessions ─────────────────────────────────
    @PostMapping("/sessions")
    public ResponseEntity<?> createSession(@RequestBody Map<String, String> body) {
        String userId = currentUserId();

        ChatSession session = ChatSession.builder()
                .id(UUID.randomUUID().toString())
                .userId(userId)
                .title(body.getOrDefault("title", "Cuộc hội thoại mới"))
                .createdAt(LocalDateTime.now())
                .build();

        sessionRepo.save(session);
        return ResponseEntity.ok(session);
    }

    // ── DELETE /api/history/sessions/{id} ─────────────────────────
    @Transactional
    @DeleteMapping("/sessions/{sessionId}")
    public ResponseEntity<?> deleteSession(@PathVariable String sessionId) {
        String userId = currentUserId();
        ChatSession session = sessionRepo.findById(sessionId).orElse(null);
        if (session == null) return ResponseEntity.notFound().build();
        if (!session.getUserId().equals(userId)) return ResponseEntity.status(403).build();

        messageRepo.deleteBySessionId(sessionId);
        sessionRepo.deleteById(sessionId);
        return ResponseEntity.ok().build();
    }
}
