package com.reon.backend.music.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record MusicResolveRequest(
        @NotBlank(message = "음악 URL을 입력해주세요.")
        @Size(max = 2048, message = "URL은 2048자 이하여야 합니다.") String url
) {}
