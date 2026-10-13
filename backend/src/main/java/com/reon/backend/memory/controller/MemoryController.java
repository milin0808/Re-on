package com.reon.backend.memory.controller;

import com.reon.backend.memory.dto.MemoryResponses.*;
import com.reon.backend.memory.security.MemoryUserResolver;
import com.reon.backend.memory.service.MemoryService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.*;
import java.security.Principal;

@RestController @RequestMapping("/api/v1/memories")
@ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemoryController {
    private final MemoryService service;
    public MemoryController(MemoryService service) { this.service = service; }
    @GetMapping public ListResponse list(Principal principal) {
        return service.list(MemoryUserResolver.requireUserId(principal));
    }
    @GetMapping("/{memoryId}") public Detail detail(@PathVariable long memoryId, Principal principal) {
        return service.detail(MemoryUserResolver.requireUserId(principal), memoryId);
    }
    @PatchMapping("/{memoryId}/read") public ReadResponse read(@PathVariable long memoryId, Principal principal) {
        return service.markRead(MemoryUserResolver.requireUserId(principal), memoryId);
    }
}
