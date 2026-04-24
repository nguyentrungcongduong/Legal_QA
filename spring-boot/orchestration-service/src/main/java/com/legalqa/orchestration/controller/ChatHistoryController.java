package com.legalqa.orchestration.controller;

import com.legalqa.orchestration.auth.JwtUtils;
import com.legalqa.orchestration.model.ChatMessage;
import com.legalqa.orchestration.model.ChatSession;
import com.legalqa.orchestration.repository.ChatMessageRepository;
import com.legalqa.orchestration.repository.ChatSessionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/history")
@RequiredArgsConstructor
public class ChatHistoryController {

    private final ChatSessionRepository sessionRepo;
    private final ChatMessageRepository messageRepo;
    private final JwtUtils jwtUtils;

    // Lấy danh sách session của user
    @GetMapping("/sessions")
    public ResponseEntity<?> getSessions(
        @RequestHeader("Authorization") String authHeader
    ) {
        String userId = extractUserId(authHeader);
        List<ChatSession> sessions = sessionRepo
            .findByUserIdOrderByCreatedAtDesc(userId);
        return ResponseEntity.ok(sessions);
    }

    // Lấy messages của một session
    @GetMapping("/sessions/{sessionId}/messages")
    public ResponseEntity<?> getMessages(
        @PathVariable String sessionId,
        @RequestHeader("Authorization") String authHeader
    ) {
        String userId = extractUserId(authHeader);

        // Verify session thuộc về user này
        ChatSession session = sessionRepo.findById(sessionId)
            .orElseThrow(() -> new RuntimeException("Session không tồn tại"));

        if (!session.getUserId().equals(userId)) {
            return ResponseEntity.status(403).body("Không có quyền truy cập");
        }

        List<ChatMessage> messages = messageRepo
            .findBySessionIdOrderByCreatedAtAsc(sessionId);
        return ResponseEntity.ok(messages);
    }

    // Tạo session mới
    @PostMapping("/sessions")
    public ResponseEntity<?> createSession(
        @RequestBody Map<String, String> body,
        @RequestHeader("Authorization") String authHeader
    ) {
        String userId = extractUserId(authHeader);

        ChatSession session = ChatSession.builder()
            .id(UUID.randomUUID().toString())
            .userId(userId)
            .title(body.getOrDefault("title", "Cuộc hội thoại mới"))
            .createdAt(LocalDateTime.now())
            .build();

        sessionRepo.save(session);
        return ResponseEntity.ok(session);
    }

    // Xóa session
    @Transactional
    @DeleteMapping("/sessions/{sessionId}")
    public ResponseEntity<?> deleteSession(
        @PathVariable String sessionId,
        @RequestHeader("Authorization") String authHeader
    ) {
        String userId = extractUserId(authHeader);
        ChatSession session = sessionRepo.findById(sessionId)
            .orElseThrow();

        if (!session.getUserId().equals(userId)) {
            return ResponseEntity.status(403).build();
        }

        messageRepo.deleteBySessionId(sessionId);
        sessionRepo.deleteById(sessionId);
        return ResponseEntity.ok().build();
    }

    private String extractUserId(String authHeader) {
        String token = authHeader.substring(7);
        return jwtUtils.getUserIdFromToken(token);
    }
}
