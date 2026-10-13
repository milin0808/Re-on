package com.reon.backend.music.service;

import com.reon.backend.global.ApiException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.ResponseActions;
import org.springframework.web.client.RestClient;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

class YouTubeClientTests {
    private MockRestServiceServer server;
    private YouTubeClient client;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder().baseUrl("https://www.googleapis.com/youtube/v3");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new YouTubeClient(builder.build(), "test-key");
    }

    private ResponseActions expectRequest() {
        return server.expect(requestTo("https://www.googleapis.com/youtube/v3/videos?part=snippet&id=wJhWwt1OmT8&key=test-key"));
    }

    @Test
    void mapsMetadataAndChoosesBestThumbnail() {
        expectRequest().andRespond(withSuccess("""
            {"items":[{"id":"wJhWwt1OmT8","snippet":{"title":"Live Forever",
            "channelTitle":"Oasis - Topic","description":"ignored",
            "thumbnails":{"default":{"url":"https://img.example/default.jpg"},
            "high":{"url":"https://img.example/high.jpg"}}}}]}
            """, MediaType.APPLICATION_JSON));
        var response = client.findVideo("wJhWwt1OmT8");
        assertEquals("wJhWwt1OmT8", response.videoId());
        assertEquals("Live Forever", response.title());
        assertEquals("Oasis - Topic", response.channelTitle());
        assertEquals("https://img.example/high.jpg", response.thumbnailUrl());
        server.verify();
    }

    @Test
    void returnsNotFoundForEmptyItems() {
        expectRequest().andRespond(withSuccess("{\"items\":[]}", MediaType.APPLICATION_JSON));
        ApiException error = assertThrows(ApiException.class, () -> client.findVideo("wJhWwt1OmT8"));
        assertEquals(HttpStatus.NOT_FOUND, error.status());
        assertEquals("MUSIC_NOT_FOUND", error.code());
        server.verify();
    }

    @Test
    void hidesUpstreamErrorsAndKeys() {
        expectRequest().andRespond(withStatus(HttpStatus.FORBIDDEN).body("private test-key"));
        ApiException error = assertThrows(ApiException.class, () -> client.findVideo("wJhWwt1OmT8"));
        assertEquals(HttpStatus.BAD_GATEWAY, error.status());
        assertEquals("YOUTUBE_API_ERROR", error.code());
        assertFalse(error.getMessage().contains("test-key"));
        assertNull(error.getCause());
        server.verify();
    }

    @Test
    void rejectsMissingApiKeyWithoutMakingRequest() {
        var unconfigured = new YouTubeClient(RestClient.create(), "");
        ApiException error = assertThrows(ApiException.class, () -> unconfigured.findVideo("wJhWwt1OmT8"));
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, error.status());
        assertEquals("YOUTUBE_API_NOT_CONFIGURED", error.code());
    }

    @Test
    void handlesInvalidUpstreamBody() {
        expectRequest().andRespond(withSuccess("{\"items\":[{\"id\":\"wJhWwt1OmT8\"}]}", MediaType.APPLICATION_JSON));
        ApiException error = assertThrows(ApiException.class, () -> client.findVideo("wJhWwt1OmT8"));
        assertEquals("YOUTUBE_API_ERROR", error.code());
        server.verify();
    }

    @Test
    void allowsMetadataWithoutThumbnail() {
        expectRequest().andRespond(withSuccess("""
            {"items":[{"id":"wJhWwt1OmT8","snippet":{"title":"Live Forever","channelTitle":"Oasis"}}]}
            """, MediaType.APPLICATION_JSON));
        assertNull(client.findVideo("wJhWwt1OmT8").thumbnailUrl());
        server.verify();
    }
}
