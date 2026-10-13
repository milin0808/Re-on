package com.reon.backend.memory.engine;

import com.reon.backend.global.ApiException;
import com.reon.backend.memory.engine.EngineContract.*;
import org.springframework.beans.factory.annotation.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.*;
import java.time.Duration;

@Component @ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemoryEngineClient {
    private final RestClient client;
    private final String token;
    @Autowired
    public MemoryEngineClient(RestClient.Builder builder, @Value("${memory.engine.base-url}") String baseUrl,
                              @Value("${memory.engine.token}") String token) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(3)); factory.setReadTimeout(Duration.ofSeconds(20));
        this.client = builder.baseUrl(baseUrl).requestFactory(factory).build(); this.token = token;
    }
    public MemoryEngineClient(RestClient client, String token) { this.client = client; this.token = token; }
    public Response analyze(Request request) {
        if (token.isBlank() || !token.chars().allMatch(c -> c >= 33 && c <= 126))
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "MEMORY_ENGINE_NOT_CONFIGURED", "Memory Engine 내부 토큰 설정이 필요합니다.");
        try {
            var response = client.post().uri("/api/v1/memories/analyze/core")
                    .header("X-Service-Token", token).contentType(MediaType.APPLICATION_JSON)
                    .body(request).retrieve().body(Response.class);
            if (response == null) throw new IllegalStateException("Empty response");
            return response;
        } catch (RestClientException | IllegalStateException ex) {
            // Do not include the request, token, Moment memo, or upstream body in the error.
            throw new ApiException(HttpStatus.BAD_GATEWAY, "MEMORY_ENGINE_ERROR", "Memory 분석에 실패했습니다.");
        }
    }
}
