package com.reon.backend.memory;

import com.reon.backend.global.ApiException;
import com.reon.backend.memory.engine.*;
import com.reon.backend.memory.engine.EngineContract.*;
import org.junit.jupiter.api.Test;
import org.springframework.http.*;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

class MemoryEngineClientTests {
    static Request request() { return new Request("1", List.of(), List.of(), new Scope("1", List.of("2026-07"), true, 17)); }
    @Test void sendsAuthenticatedCoreRequestAndParsesScope() {
        var builder = RestClient.builder().baseUrl("http://engine.local");
        var server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://engine.local/api/v1/memories/analyze/core"))
                .andExpect(method(HttpMethod.POST)).andExpect(header("X-Service-Token", "test-token"))
                .andExpect(jsonPath("$.scope.history_revision").value(17))
                .andExpect(jsonPath("$.scope.complete_month_history").value(true))
                .andRespond(withSuccess("""
                    {"meta":{},"memories":[],"scope":{"user_id":"1","months":["2026-07"],"complete_month_history":true,"history_revision":17},"deactivated_memory_ids":[]}
                    """, MediaType.APPLICATION_JSON));
        var response = new MemoryEngineClient(builder.build(), "test-token").analyze(request());
        assertEquals(request().scope(), response.scope()); server.verify();
    }
    @Test void missingAndNonAsciiTokensFailBeforeSending() {
        for (String token : List.of("", " ", "토큰", "line\nbreak")) {
            var client = new MemoryEngineClient(RestClient.builder().baseUrl("http://engine.local").build(), token);
            assertEquals("MEMORY_ENGINE_NOT_CONFIGURED", assertThrows(ApiException.class, () -> client.analyze(request())).code());
        }
    }
    @Test void upstreamErrorsDoNotExposeBodyOrToken() {
        var builder = RestClient.builder().baseUrl("http://engine.local");
        var server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://engine.local/api/v1/memories/analyze/core"))
                .andRespond(withStatus(HttpStatus.UNAUTHORIZED).body("private memo and private-token"));
        var ex = assertThrows(ApiException.class, () -> new MemoryEngineClient(builder.build(), "private-token").analyze(request()));
        assertEquals("MEMORY_ENGINE_ERROR", ex.code()); assertFalse(ex.getMessage().contains("private")); server.verify();
    }
}
