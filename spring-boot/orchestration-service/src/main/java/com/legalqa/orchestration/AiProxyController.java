package com.legalqa.orchestration;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
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

    /** Dùng cho /query và /compare — read timeout 2 phút */
    private final RestTemplate restTemplate;

    /** Dùng riêng cho /evaluate — 20 test cases có thể mất 5-10 phút */
    private final RestTemplate evaluateRestTemplate;

    public AiProxyController() {
        restTemplate         = buildRestTemplate(5_000, 120_000);   // 2 phút
        evaluateRestTemplate = buildRestTemplate(5_000, 600_000);   // 10 phút
    }

    private static RestTemplate buildRestTemplate(int connectMs, int readMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectMs);
        factory.setReadTimeout(readMs);
        return new RestTemplate(factory);
    }

    @Value("${python.api.base-url:http://localhost:8000}")
    private String pythonApiBaseUrl;

    // ─── Endpoints ──────────────────────────────────────────────────────────────

    @PostMapping(value = "/query", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> query(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return forward("/ai/query", body, request, restTemplate);
    }

    @PostMapping(value = "/compare", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> compare(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        return forward("/ai/compare", body, request, restTemplate);
    }

    /** evaluate không có request body — dùng timeout 10 phút */
    @PostMapping(value = "/evaluate")
    public ResponseEntity<Object> evaluate(
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest request) {
        return forward("/ai/evaluate", body != null ? body : Map.of(), request, evaluateRestTemplate);
    }

    /** RAGAS: khởi động job — trả về job_id ngay lập tức (timeout ngắn) */
    @PostMapping(value = "/evaluate/ragas")
    public ResponseEntity<Object> evaluateRagas(
            @RequestBody(required = false) Map<String, Object> body,
            HttpServletRequest request) {
        return forward("/ai/evaluate/ragas", body != null ? body : Map.of(), request, restTemplate);
    }

    /** RAGAS: poll trạng thái job — GET request */
    @GetMapping(value = "/evaluate/ragas/status/{jobId}")
    public ResponseEntity<Object> evaluateRagasStatus(
            @PathVariable String jobId,
            HttpServletRequest request) {
        return forwardGet("/ai/evaluate/ragas/status/" + jobId, request, restTemplate);
    }


    private ResponseEntity<Object> forward(String path, Map<String, Object> body,
                                           HttpServletRequest request, RestTemplate rt) {
        try {
            String url = pythonApiBaseUrl + path;

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            String authHeader = request.getHeader("Authorization");
            if (authHeader != null) headers.set("Authorization", authHeader);
            headers.setContentType(MediaType.APPLICATION_JSON);

            org.springframework.http.HttpEntity<Map<String, Object>> entity =
                new org.springframework.http.HttpEntity<>(body, headers);

            ResponseEntity<Object> response = rt.exchange(url, HttpMethod.POST, entity, Object.class);
            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());

        } catch (ResourceAccessException e) {
            String detail = e.getMessage() != null ? e.getMessage() : "";
            boolean isTimeout = detail.contains("Read timed out");
            String msg = isTimeout
                ? "Evaluation quá lâu (>10 phút). Thử chạy lại hoặc giảm số test cases."
                : "AI backend không khả dụng. Vui lòng đảm bảo FastAPI đang chạy trên cổng 8000.";
            System.err.println("[AiProxy] " + (isTimeout ? "TIMEOUT" : "CONNECTION_ERROR") + ": " + detail);
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("error", msg, "detail", detail));

        } catch (org.springframework.web.client.HttpServerErrorException e) {
            System.err.println("[AiProxy] FastAPI 5xx: " + e.getStatusCode() + " | " + e.getResponseBodyAsString());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "FastAPI error: " + e.getStatusCode(),
                             "detail", e.getResponseBodyAsString()));

        } catch (org.springframework.web.client.HttpClientErrorException e) {
            return ResponseEntity.status(e.getStatusCode())
                .body(Map.of("error", "Client error: " + e.getStatusCode(),
                             "detail", e.getResponseBodyAsString()));

        } catch (Exception e) {
            System.err.println("[AiProxy] Exception: " + e.getClass().getName() + ": " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Lỗi xử lý: " + e.getMessage()));
        }
    }

    private ResponseEntity<Object> forwardGet(String path, HttpServletRequest request, RestTemplate rt) {
        try {
            String url = pythonApiBaseUrl + path;

            // Append query string if present
            String qs = request.getQueryString();
            if (qs != null && !qs.isEmpty()) url += "?" + qs;

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            String authHeader = request.getHeader("Authorization");
            if (authHeader != null) headers.set("Authorization", authHeader);

            org.springframework.http.HttpEntity<Void> entity =
                new org.springframework.http.HttpEntity<>(headers);

            ResponseEntity<Object> response = rt.exchange(url, HttpMethod.GET, entity, Object.class);
            return ResponseEntity.status(response.getStatusCode()).body(response.getBody());

        } catch (ResourceAccessException e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("error", "AI backend không khả dụng", "detail", e.getMessage()));
        } catch (org.springframework.web.client.HttpClientErrorException e) {
            return ResponseEntity.status(e.getStatusCode())
                .body(Map.of("error", "Not found", "detail", e.getResponseBodyAsString()));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Lỗi proxy GET: " + e.getMessage()));
        }
    }
}
