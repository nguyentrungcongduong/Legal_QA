package com.legalqa.orchestration;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import jakarta.servlet.http.HttpServletRequest;

@RestController
@RequestMapping("/api/ai")
public class AiProxyController {
    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${python.api.base-url:http://localhost:8000}")
    private String pythonApiBaseUrl;

    @PostMapping(value = "/query", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> query(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return forward("/ai/query", body, request);
    }

    @PostMapping(value = "/compare", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> compare(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return forward("/ai/compare", body, request);
    }

    @PostMapping(value = "/evaluate", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> evaluate(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return forward("/ai/evaluate", body, request);
    }

    private ResponseEntity<Object> forward(String path, Map<String, Object> body, HttpServletRequest request) {
        try {
            String url = pythonApiBaseUrl + path;
            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            String authHeader = request.getHeader("Authorization");
            if (authHeader != null) {
                headers.set("Authorization", authHeader);
            }
            headers.setContentType(MediaType.APPLICATION_JSON);

            org.springframework.http.HttpEntity<Map<String, Object>> entity =
                new org.springframework.http.HttpEntity<>(body, headers);
            ResponseEntity<Object> response = restTemplate.exchange(url, HttpMethod.POST, entity, Object.class);
            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());

        } catch (ResourceAccessException e) {
            // FastAPI không chạy hoặc không thể kết nối
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of(
                    "error", "AI backend không khả dụng. Vui lòng đảm bảo FastAPI đang chạy trên cổng 8000.",
                    "detail", e.getMessage()
                ));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Lỗi xử lý: " + e.getMessage()));
        }
    }
}
