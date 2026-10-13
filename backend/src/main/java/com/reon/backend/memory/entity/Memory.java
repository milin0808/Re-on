package com.reon.backend.memory.entity;

import jakarta.persistence.*;
import lombok.Getter;
import java.time.*;
import java.util.*;

@Entity
@Table(name = "reon_memory", uniqueConstraints = @UniqueConstraint(name = "uk_memory_engine", columnNames = "engine_memory_id"),
        indexes = @Index(name = "idx_memory_owner_active", columnList = "user_id,active,end_date"))
@Getter
public class Memory {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(name = "user_id", nullable = false) private Long userId;
    @Column(name = "engine_memory_id", nullable = false, length = 64) private String engineMemoryId;
    @Column(name = "period_month", nullable = false, length = 7) private String periodMonth;
    @Column(name = "pattern_type", nullable = false, length = 16) private String patternType;
    @Column(nullable = false, length = 512) private String title;
    @Column(nullable = false, columnDefinition = "TEXT") private String description;
    @Column(name = "start_date", nullable = false) private LocalDate startDate;
    @Column(name = "end_date", nullable = false) private LocalDate endDate;
    @Column(name = "moment_count", nullable = false) private int momentCount;
    @Column(name = "contexts_json", nullable = false, columnDefinition = "TEXT") private String contextsJson;
    @Column(name = "tracks_json", nullable = false, columnDefinition = "TEXT") private String tracksJson;
    @Column(name = "content_hash", nullable = false, length = 64) private String contentHash;
    @Column(nullable = false) private boolean active;
    @Column(name = "history_revision", nullable = false) private long historyRevision;
    @Column(name = "read_at") private OffsetDateTime readAt;
    @Version @Column(nullable = false) private long version;
    @ElementCollection
    @CollectionTable(name = "reon_memory_moment", joinColumns = @JoinColumn(name = "memory_id"))
    @OrderColumn(name = "sort_index")
    private List<MemoryMoment> moments = new ArrayList<>();

    protected Memory() {}
    public Memory(long userId, String engineMemoryId, String periodMonth) {
        this.userId = userId; this.engineMemoryId = engineMemoryId; this.periodMonth = periodMonth;
    }
    public void replace(String patternType, String title, String description, LocalDate start, LocalDate end,
                        String contextsJson, String tracksJson, String hash, long revision, List<MemoryMoment> moments) {
        this.patternType = patternType; this.title = title; this.description = description;
        this.startDate = start; this.endDate = end; this.contextsJson = contextsJson;
        this.tracksJson = tracksJson; this.contentHash = hash; this.historyRevision = revision;
        this.active = true; this.momentCount = moments.size();
        this.moments.clear(); this.moments.addAll(moments);
    }
    public boolean isNew() { return readAt == null; }
    public void markRead() { if (readAt == null) readAt = OffsetDateTime.now(ZoneOffset.UTC); }
    public void deactivate(long revision) {
        active = false; historyRevision = revision;
        // Deleted/edited Moment memo snapshots must not remain in inactive memories.
        moments.clear(); momentCount = 0; tracksJson = "[]"; contextsJson = "[]";
    }
}
