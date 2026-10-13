package com.reon.backend.music.controller;

import com.reon.backend.music.dto.MusicResolveRequest;
import com.reon.backend.music.dto.MusicResolveResponse;
import com.reon.backend.music.service.MusicService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/music")
public class MusicController {
    private final MusicService musicService;

    public MusicController(MusicService musicService) {
        this.musicService = musicService;
    }

    @PostMapping("/resolve")
    public MusicResolveResponse resolve(@Valid @RequestBody MusicResolveRequest request) {
        return musicService.resolve(request.url());
    }
}
