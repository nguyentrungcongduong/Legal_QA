package com.legalqa.gateway;

import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

@RestController
@RequestMapping("/api/ai")
public class GatewayController {
    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${orchestration.base-url:http://localhost:8081}")
    private String orchestrationBaseUrl;

    @PostMapping(value = "/query", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> query(@RequestBody Map<String, Object> body) {
        return forward("/ai/query", body);
    }

    @PostMapping(value = "/compare", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> compare(@RequestBody Map<String, Object> body) {
        return forward("/ai/compare", body);
    }

    @PostMapping(value = "/evaluate", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Object> evaluate(@RequestBody Map<String, Object> body) {
        return forward("/ai/evaluate", body);
    }

    private ResponseEntity<Object> forward(String path, Map<String, Object> body) {
        String url = orchestrationBaseUrl + path;
        ResponseEntity<Object> response = restTemplate.exchange(url, HttpMethod.POST,
                new org.springframework.http.HttpEntity<>(body), Object.class);
        return ResponseEntity.status(response.getStatusCode()).body(response.getBody());
    }
}
