package com.reon.backend.memory.service;

import com.reon.backend.global.ApiException;
import com.reon.backend.memory.engine.EngineContract.*;
import com.reon.backend.memory.port.MomentHistoryReader;
import com.reon.backend.memory.repository.*;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.YearMonth;
import java.util.*;

@Service @ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemorySnapshotService {
    public record Snapshot(Request request, Map<String, MomentHistoryReader.Record> moments) {}
    private final MemoryHistoryRevisionRepository revisions;
    private final MemoryRepository memories;
    private final ObjectProvider<MomentHistoryReader> readers;
    public MemorySnapshotService(MemoryHistoryRevisionRepository revisions, MemoryRepository memories,
                                 ObjectProvider<MomentHistoryReader> readers) {
        this.revisions = revisions; this.memories = memories; this.readers = readers;
    }
    public boolean sourceAvailable() { return readers.getIfAvailable() != null; }
    @Transactional public Optional<Snapshot> capture(long userId) {
        var reader = readers.getIfAvailable();
        if (reader == null) throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "MOMENT_SOURCE_NOT_CONFIGURED", "Moment DB 조회 어댑터가 필요합니다.");
        var row = revisions.lock(userId).orElse(null);
        if (row == null || row.months().isEmpty()) return Optional.empty();
        YearMonth month = row.months().iterator().next(); // One complete month per request; never truncate.
        var records = reader.readCompleteMonth(userId, month);
        if (records == null || records.size() > 1000) throw new IllegalStateException("월 전체 Moment는 최대 1000개여야 합니다. 페이지를 보내면 안 됩니다.");
        Map<String, MomentHistoryReader.Record> byId = new LinkedHashMap<>();
        for (var m : records) {
            if (m == null || m.id() <= 0 || m.userId() != userId || m.recordedAt() == null || m.music() == null
                    || !MemoryHistoryService.month(m.recordedAt()).equals(month) || byId.put(Long.toString(m.id()), m) != null) {
                throw new IllegalStateException("Moment DB 스냅샷의 소유자, 월 또는 ID가 잘못됐습니다.");
            }
        }
        String owner = Long.toString(userId);
        var existing = memories.findByUserIdAndPeriodMonthIn(userId, List.of(month.toString())).stream()
                .map(m -> new Existing(m.getEngineMemoryId(), owner, m.getPeriodMonth(), m.isActive(), m.getContentHash())).toList();
        var scope = new Scope(owner, List.of(month.toString()), true, row.getRevision());
        return Optional.of(new Snapshot(new Request(owner, records.stream().map(MomentHistoryReader.Record::engineMoment).toList(),
                existing, scope), Map.copyOf(byId)));
    }
}
