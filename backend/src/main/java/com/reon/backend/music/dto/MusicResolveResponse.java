package com.reon.backend.music.dto;

public record MusicResolveResponse(
        String videoId, String title, String channelTitle, String thumbnailUrl
) {}
