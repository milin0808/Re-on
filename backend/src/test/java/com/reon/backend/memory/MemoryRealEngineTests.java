package com.reon.backend.memory;

import com.reon.backend.memory.engine.EngineContract.*;
import com.reon.backend.memory.port.MomentHistoryReader;
import com.reon.backend.memory.repository.*;
import com.reon.backend.memory.service.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import java.time.OffsetDateTime;
import static org.junit.jupiter.api.Assertions.*;

/** Optional live loopback test. Start FastAPI with the token in application-memory-test.properties first. */
@SpringBootTest @ActiveProfiles("memory-test") @Import(MemoryPersistenceTests.Fixtures.class)
@EnabledIfEnvironmentVariable(named = "REON_MEMORY_ENGINE_INTEGRATION", matches = "true")
class MemoryRealEngineTests {
    @Autowired MemoryPersistenceTests.History history;
    @Autowired MemoryHistoryService changes;
    @Autowired MemorySyncCoordinator sync;
    @Autowired MemoryService memory;
    @Autowired MemoryRepository memories;
    @Autowired MemoryHistoryRevisionRepository revisions;
    @Autowired PlatformTransactionManager transactionManager;
    @Test void realFastApiResponsePersistsReadsRevisesAndDeactivates() {
        var tx = new TransactionTemplate(transactionManager);
        tx.executeWithoutResult(t -> { memories.deleteAll(); revisions.deleteAll(); }); history.records.clear();
        var at = OffsetDateTime.parse("2026-07-03T19:00:00+09:00");
        for (int i = 1; i <= 3; i++) history.records.add(MemoryPersistenceTests.record(i, at.plusDays(i - 1)));
        tx.executeWithoutResult(t -> changes.recordChange(1, null, at));
        assertTrue(sync.synchronizeNext(1));
        long id = memory.list(1).content().getFirst().id();
        assertEquals(3, memory.detail(1, id).momentCount()); assertEquals("wJhWwt1OmT8", memory.replayVideoIds(1, id).getFirst());
        memory.markRead(1, id);
        tx.executeWithoutResult(t -> changes.recordChange(1, at, at));
        var old = history.records.getFirst();
        history.records.set(0, new MomentHistoryReader.Record(old.id(), old.userId(), old.recordedAt(), old.music(), "수정한 메모", old.location()));
        assertTrue(sync.synchronizeNext(1)); assertEquals(id, memory.list(1).content().getFirst().id());
        assertFalse(memory.list(1).content().getFirst().isNew()); assertEquals("수정한 메모", memory.detail(1, id).moments().getFirst().memo());
        tx.executeWithoutResult(t -> changes.recordChange(1, at, null)); history.records.clear();
        assertTrue(sync.synchronizeNext(1)); assertTrue(memory.list(1).content().isEmpty());
        assertFalse(sync.synchronizeNext(1));
    }
}
