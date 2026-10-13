package com.reon.backend.memory.service;

import com.reon.backend.memory.repository.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.*;
import java.time.*;
import java.util.*;

@Service
@ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemoryHistoryService {
    public static final ZoneOffset ANALYSIS_OFFSET = ZoneOffset.ofHours(9);
    private final MemoryHistoryRevisionRepository revisions;
    private final MemoryRepository memories;
    public MemoryHistoryService(MemoryHistoryRevisionRepository revisions, MemoryRepository memories) {
        this.revisions = revisions; this.memories = memories;
    }
    /** Call BEFORE Moment INSERT/UPDATE/DELETE, inside the SAME database transaction. */
    @Transactional(propagation = Propagation.MANDATORY)
    public long recordChange(long userId, OffsetDateTime before, OffsetDateTime after) {
        if (userId <= 0 || (before == null && after == null)) throw new IllegalArgumentException("사용자와 변경 시각이 필요합니다.");
        revisions.initialize(userId);
        var row = revisions.lock(userId).orElseThrow();
        Set<YearMonth> affected = new TreeSet<>();
        if (before != null) affected.add(month(before));
        if (after != null) affected.add(month(after));
        row.advance(affected);
        // A changed/deleted memo must never be exposed from a previous analysis snapshot.
        // Keep the row ID and read flag so a later valid result can reactivate it.
        memories.findByUserIdAndPeriodMonthIn(userId, affected.stream().map(YearMonth::toString).toList())
                .forEach(m -> m.deactivate(row.getRevision()));
        return row.getRevision();
    }
    @Transactional(propagation = Propagation.MANDATORY)
    public void deleteUserMemories(long userId) {
        revisions.lock(userId); // Same lock order as sync and Moment mutations.
        memories.deleteAllByOwner(userId); revisions.deleteById(userId);
    }
    public static YearMonth month(OffsetDateTime recordedAt) {
        return YearMonth.from(recordedAt.withOffsetSameInstant(ANALYSIS_OFFSET));
    }
}
