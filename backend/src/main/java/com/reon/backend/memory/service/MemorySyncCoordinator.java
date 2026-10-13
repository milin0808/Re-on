package com.reon.backend.memory.service;

import com.reon.backend.memory.engine.MemoryEngineClient;
import com.reon.backend.memory.repository.MemoryHistoryRevisionRepository;
import org.slf4j.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Service @ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemorySyncCoordinator {
    private static final Logger log = LoggerFactory.getLogger(MemorySyncCoordinator.class);
    private final MemorySnapshotService snapshots;
    private final MemoryEngineClient engine;
    private final MemoryResultService results;
    private final MemoryHistoryRevisionRepository revisions;
    private long cursor;
    public MemorySyncCoordinator(MemorySnapshotService snapshots, MemoryEngineClient engine,
                                 MemoryResultService results, MemoryHistoryRevisionRepository revisions) {
        this.snapshots = snapshots; this.engine = engine; this.results = results; this.revisions = revisions;
    }
    /** Each database transaction ends before the HTTP call begins. */
    public boolean synchronizeNext(long userId) {
        var snapshot = snapshots.capture(userId);
        return snapshot.isPresent() && results.apply(snapshot.get(), engine.analyze(snapshot.get().request()));
    }
    @Scheduled(fixedDelayString = "${memory.engine.poll-delay-ms:5000}", initialDelayString = "${memory.engine.poll-delay-ms:5000}")
    public void retryPending() {
        if (!snapshots.sourceAvailable()) return;
        var users = revisions.pendingUsersAfter(cursor, PageRequest.of(0, 20));
        if (users.isEmpty()) {
            cursor = 0;
            users = revisions.pendingUsersAfter(0, PageRequest.of(0, 20));
        }
        for (long userId : users) {
            try { synchronizeNext(userId); }
            catch (RuntimeException ex) {
                // Pending work stays in the DB after crashes/failures; do not log sensitive exception bodies.
                log.warn("Memory analysis remains pending for user {} ({})", userId, ex.getClass().getSimpleName());
            }
            cursor = userId;
        }
    }
}
