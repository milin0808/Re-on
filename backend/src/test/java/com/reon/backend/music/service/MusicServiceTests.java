package com.reon.backend.music.service;

import com.reon.backend.global.ApiException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class MusicServiceTests {
    private final YouTubeClient client = mock(YouTubeClient.class);
    private final MusicService service = new MusicService(client);

    @Test
    void extractsSharedUrlAndCallsClient() {
        service.resolve("https://music.youtube.com/watch?si=share&v=wJhWwt1OmT8&list=playlist");
        verify(client).findVideo("wJhWwt1OmT8");
    }

    @ParameterizedTest
    @ValueSource(strings = {
        "", "not a url", "http://music.youtube.com/watch?v=wJhWwt1OmT8",
        "https://example.com/watch?v=wJhWwt1OmT8",
        "https://music.youtube.com.evil.com/watch?v=wJhWwt1OmT8",
        "https://music.youtube.com/playlist?v=wJhWwt1OmT8",
        "https://music.youtube.com/watch?si=share", "https://music.youtube.com/watch?v=",
        "https://music.youtube.com/watch?v=short",
        "https://music.youtube.com/watch?v=wJhWwt1OmT8&v=wJhWwt1OmT8",
        "https://someone@music.youtube.com/watch?v=wJhWwt1OmT8",
        "https://music.youtube.com:1234/watch?v=wJhWwt1OmT8",
        "https://music.youtube.com/watch?v=%ZZ"
    })
    void rejectsInvalidUrlsWithoutCallingYouTube(String url) {
        ApiException error = assertThrows(ApiException.class, () -> service.resolve(url));
        assertEquals("INVALID_YOUTUBE_MUSIC_URL", error.code());
        verifyNoInteractions(client);
    }
}
