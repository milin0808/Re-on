package com.reon.backend.music.controller;

import com.reon.backend.global.ApiException;
import com.reon.backend.global.GlobalExceptionHandler;
import com.reon.backend.music.dto.MusicResolveResponse;
import com.reon.backend.music.service.MusicService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class MusicControllerTests {
    private final MusicService service = mock(MusicService.class);
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.standaloneSetup(new MusicController(service))
                .setControllerAdvice(new GlobalExceptionHandler()).build();
    }

    @Test
    void returnsMetadata() throws Exception {
        when(service.resolve("https://music.youtube.com/watch?v=wJhWwt1OmT8"))
                .thenReturn(new MusicResolveResponse("wJhWwt1OmT8", "Live Forever", "Oasis - Topic", "https://img.example/high.jpg"));
        mvc.perform(post("/api/v1/music/resolve").contentType(MediaType.APPLICATION_JSON)
                .content("{\"url\":\"https://music.youtube.com/watch?v=wJhWwt1OmT8\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.videoId").value("wJhWwt1OmT8"))
                .andExpect(jsonPath("$.title").value("Live Forever"))
                .andExpect(jsonPath("$.channelTitle").value("Oasis - Topic"))
                .andExpect(jsonPath("$.thumbnailUrl").value("https://img.example/high.jpg"));
    }

    @Test
    void rejectsBlankMissingAndMalformedBodies() throws Exception {
        for (String body : new String[]{"{\"url\":\" \"}", "{}", "{", "{\"url\":null}"}) {
            mvc.perform(post("/api/v1/music/resolve").contentType(MediaType.APPLICATION_JSON).content(body))
                    .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
        }
        verifyNoInteractions(service);
    }

    @Test
    void preservesApiErrorFormat() throws Exception {
        when(service.resolve("invalid")).thenThrow(new ApiException(HttpStatus.BAD_REQUEST,
                "INVALID_YOUTUBE_MUSIC_URL", "올바른 YouTube Music 링크가 아닙니다."));
        mvc.perform(post("/api/v1/music/resolve").contentType(MediaType.APPLICATION_JSON).content("{\"url\":\"invalid\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_YOUTUBE_MUSIC_URL"));
    }
}
