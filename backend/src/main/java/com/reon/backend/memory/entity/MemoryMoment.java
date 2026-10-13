package com.reon.backend.memory.entity;

import jakarta.persistence.*;
import lombok.Getter;
import java.time.OffsetDateTime;

@Embeddable
@Getter
public class MemoryMoment {
    @Column(name = "moment_id", nullable = false) private Long momentId;
    @Column(name = "recorded_at", nullable = false) private OffsetDateTime recordedAt;
    @Column(name = "song_title", nullable = false, length = 255) private String title;
    @Column(length = 255) private String artist;
    @Column(length = 2000) private String memo;
    protected MemoryMoment() {}
    public MemoryMoment(Long momentId, OffsetDateTime recordedAt, String title, String artist, String memo) {
        this.momentId = momentId; this.recordedAt = recordedAt; this.title = title;
        this.artist = artist; this.memo = memo;
    }
}
