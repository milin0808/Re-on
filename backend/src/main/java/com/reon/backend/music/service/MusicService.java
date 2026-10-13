package com.reon.backend.music.service;

import com.reon.backend.global.ApiException;
import com.reon.backend.music.dto.MusicResolveResponse;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;

@Service
public class MusicService {
    private final YouTubeClient youTubeClient;

    public MusicService(YouTubeClient youTubeClient) {
        this.youTubeClient = youTubeClient;
    }

    public MusicResolveResponse resolve(String url) {
        return youTubeClient.findVideo(extractVideoId(url));
    }

    String extractVideoId(String url) {
        try {
            URI uri = URI.create(url);
            if (!"https".equalsIgnoreCase(uri.getScheme())
                    || !"music.youtube.com".equalsIgnoreCase(uri.getHost())
                    || !"/watch".equals(uri.getPath()) || uri.getRawUserInfo() != null
                    || (uri.getPort() != -1 && uri.getPort() != 443)
                    || uri.getRawQuery() == null) {
                throw invalidUrl();
            }
            List<String> ids = Arrays.stream(uri.getRawQuery().split("&"))
                    .map(param -> param.split("=", 2))
                    .filter(param -> URLDecoder.decode(param[0], StandardCharsets.UTF_8).equals("v"))
                    .map(param -> param.length == 2 ? URLDecoder.decode(param[1], StandardCharsets.UTF_8) : "")
                    .toList();
            if (ids.size() != 1 || !ids.getFirst().matches("[A-Za-z0-9_-]{11}")) {
                throw invalidUrl();
            }
            return ids.getFirst();
        } catch (IllegalArgumentException | NullPointerException exception) {
            throw invalidUrl();
        }
    }

    private ApiException invalidUrl() {
        return new ApiException(HttpStatus.BAD_REQUEST, "INVALID_YOUTUBE_MUSIC_URL",
                "올바른 YouTube Music 링크가 아닙니다.");
    }
}
