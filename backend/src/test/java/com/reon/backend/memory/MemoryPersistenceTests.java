package com.reon.backend.memory;

import com.reon.backend.global.*;
import com.reon.backend.memory.controller.MemoryController;
import com.reon.backend.memory.controller.MemoryApiExceptionHandler;
import com.reon.backend.memory.engine.EngineContract.*;
import com.reon.backend.memory.port.MomentHistoryReader;
import com.reon.backend.memory.repository.*;
import com.reon.backend.memory.service.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.*;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import tools.jackson.databind.ObjectMapper;
import java.time.*;
import com.reon.backend.memory.engine.EngineContract.Period;
import java.util.*;
import java.util.concurrent.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest @ActiveProfiles("memory-test") @Import(MemoryPersistenceTests.Fixtures.class)
public class MemoryPersistenceTests {
    @TestConfiguration public static class Fixtures {
        @Bean public History history() { return new History(); }
    }
    public static class History implements MomentHistoryReader {
        final List<Record> records = new CopyOnWriteArrayList<>();
        @Override public List<Record> readCompleteMonth(long userId, YearMonth month) {
            return records.stream().filter(m -> m.userId() == userId && MemoryHistoryService.month(m.recordedAt()).equals(month)).toList();
        }
    }
    @Autowired MemoryHistoryService historyService;
    @Autowired MemorySnapshotService snapshots;
    @Autowired MemoryResultService results;
    @Autowired MemoryService service;
    @Autowired MemoryRepository memories;
    @Autowired MemoryHistoryRevisionRepository revisions;
    @Autowired PlatformTransactionManager transactionManager;
    @Autowired ObjectMapper mapper;
    @Autowired History history;
    TransactionTemplate tx;
    MockMvc mvc;
    static final OffsetDateTime JULY = OffsetDateTime.parse("2026-07-03T19:00:00+09:00");
    static final String ENGINE_ID = "mem_aaaaaaaaaaaaaaaa";
    @BeforeEach void setup() {
        tx = new TransactionTemplate(transactionManager);
        tx.executeWithoutResult(s -> { memories.deleteAll(); revisions.deleteAll(); });
        history.records.clear();
        for (int i = 1; i <= 3; i++) history.records.add(record(i, JULY.plusDays(i - 1)));
        mvc = MockMvcBuilders.standaloneSetup(new MemoryController(service)).setControllerAdvice(new MemoryApiExceptionHandler(), new GlobalExceptionHandler()).build();
    }
    static MomentHistoryReader.Record record(long id, OffsetDateTime at) {
        return new MomentHistoryReader.Record(id, 1, at,
                new Music("wJhWwt1OmT8", "Live Forever", "Oasis", null, null, null), "공연 메모 " + id, new Location(37.45, 127.128));
    }
    MemorySnapshotService.Snapshot queue(OffsetDateTime before, OffsetDateTime after) {
        tx.executeWithoutResult(s -> historyService.recordChange(1, before, after));
        return snapshots.capture(1).orElseThrow();
    }
    Response response(MemorySnapshotService.Snapshot s) {
        var ids = s.moments().keySet().stream().sorted().toList();
        var dates = s.moments().values().stream().map(m -> m.recordedAt().withOffsetSameInstant(ZoneOffset.ofHours(9)).toLocalDate()).sorted().toList();
        var context = mapper.createObjectNode().put("count", ids.size()).put("dominant_time_band", "EVENING")
                .put("dominant_time_ratio", 1.0).put("top_location", "위도 37.450, 경도 127.128");
        var result = new Result(ENGINE_ID, "1", "ARTIST", "Oasis와 함께한 7월", "7월의 음악 기록", new Period(s.request().scope().months().getFirst(),
                dates.getFirst().toString(), dates.getLast().toString()), ids,
                List.of(new Track("wJhWwt1OmT8", "Oasis", "Live Forever")), true, context, "a".repeat(64), "CREATE");
        return new Response(null, List.of(result), s.request().scope(), List.of());
    }
    long create() {
        var s = queue(null, JULY); assertTrue(results.apply(s, response(s)));
        return service.list(1).content().getFirst().id();
    }
    @Test void createsListAndDetailWithTheDocumentedShape() throws Exception {
        long id = create();
        mvc.perform(get("/api/v1/memories").principal(() -> "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].id").value(id)).andExpect(jsonPath("$.content[0].momentCount").value(3))
                .andExpect(jsonPath("$.content[0].isNew").value(true)).andExpect(jsonPath("$.content[0].startDate").value("2026-07-03"));
        mvc.perform(get("/api/v1/memories/{id}", id).principal(() -> "1")).andExpect(status().isOk())
                .andExpect(jsonPath("$.contexts[0].type").value("TIME")).andExpect(jsonPath("$.contexts[0].value").value("100%"))
                .andExpect(jsonPath("$.contexts[1].type").value("PLACE")).andExpect(jsonPath("$.contexts[1].value").doesNotExist())
                .andExpect(jsonPath("$.moments[0].id").value(1)).andExpect(jsonPath("$.moments[0].recordedAt").value("2026-07-03T19:00:00+09:00"));
        assertTrue(service.list(1).content().getFirst().isNew());
    }
    @Test void readEndpointIsIdempotentAndUpdatePreservesReadState() throws Exception {
        long id = create();
        for (int i = 0; i < 2; i++) mvc.perform(patch("/api/v1/memories/{id}/read", id).principal(() -> "1"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.id").value(id)).andExpect(jsonPath("$.isNew").value(false));
        var s = queue(JULY, JULY); assertTrue(results.apply(s, response(s)));
        assertEquals(id, service.list(1).content().getFirst().id()); assertFalse(service.list(1).content().getFirst().isNew());
    }
    @Test void allEndpointsRequireAValidatedPrincipal() throws Exception {
        long id = create();
        for (var request : List.of(get("/api/v1/memories"), get("/api/v1/memories/" + id), patch("/api/v1/memories/" + id + "/read")))
            mvc.perform(request.header("Authorization", "Bearer 1")).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
        mvc.perform(get("/api/v1/memories").principal(() -> "google-email@example.com")).andExpect(status().isUnauthorized());
    }
    @Test void otherUsersCannotReadOrMarkMemory() throws Exception {
        long id = create(); assertTrue(service.list(2).content().isEmpty());
        mvc.perform(get("/api/v1/memories/{id}", id).principal(() -> "2")).andExpect(status().isNotFound()).andExpect(jsonPath("$.code").value("MEMORY_NOT_FOUND"));
        mvc.perform(patch("/api/v1/memories/{id}/read", id).principal(() -> "2")).andExpect(status().isNotFound());
        assertTrue(service.list(1).content().getFirst().isNew());
    }
    @Test void staleResultCannotSaveOrClearPendingWork() {
        var stale = queue(null, JULY); queue(JULY, JULY.plusDays(1));
        assertFalse(results.apply(stale, response(stale))); assertTrue(service.list(1).content().isEmpty());
        assertTrue(snapshots.capture(1).isPresent()); assertEquals(2, revisions.findById(1L).orElseThrow().getRevision());
    }
    @Test void changeImmediatelyHidesOldMemoAndReactivationKeepsId() {
        long id = create(); service.markRead(1, id);
        var s = queue(JULY, JULY);
        assertTrue(service.list(1).content().isEmpty()); assertThrows(ApiException.class, () -> service.detail(1, id));
        tx.executeWithoutResult(t -> assertTrue(memories.findById(id).orElseThrow().getMoments().isEmpty()));
        history.records.set(0, new MomentHistoryReader.Record(1, 1, JULY, history.records.getFirst().music(), "바뀐 메모", null));
        s = snapshots.capture(1).orElseThrow(); assertTrue(results.apply(s, response(s)));
        assertEquals(id, service.list(1).content().getFirst().id()); assertFalse(service.list(1).content().getFirst().isNew());
        assertEquals("바뀐 메모", service.detail(1, id).moments().getFirst().memo());
    }
    @Test void emptyMonthDeactivatesAndCompletesWork() {
        create(); queue(JULY, null); history.records.clear(); var s = snapshots.capture(1).orElseThrow();
        assertTrue(results.apply(s, new Response(null, List.of(), s.request().scope(), List.of())));
        assertTrue(service.list(1).content().isEmpty()); assertTrue(snapshots.capture(1).isEmpty());
    }
    @Test void monthMoveQueuesBothKoreanMonths() {
        queue(JULY, OffsetDateTime.parse("2026-07-31T15:00:00Z"));
        assertEquals(Set.of(YearMonth.of(2026, 7), YearMonth.of(2026, 8)), revisions.findById(1L).orElseThrow().months());
    }
    @Test void missingAndForeignMomentIdsRejectTheWholeResult() {
        var s = queue(null, JULY); var r = response(s).memories().getFirst();
        var invalid = new Result(r.memory_id(), r.user_id(), r.type(), r.title(), r.description(), r.period(), List.of("999"),
                r.tracks(), r.replay_available(), r.context(), r.content_hash(), r.sync_action());
        assertThrows(ApiException.class, () -> results.apply(s, new Response(null, List.of(invalid), s.request().scope(), List.of())));
        assertEquals(0, memories.count()); assertTrue(snapshots.capture(1).isPresent());
    }
    @Test void changedScopeIsRejected() {
        var s = queue(null, JULY);
        var bad = new Scope("2", s.request().scope().months(), true, s.request().scope().history_revision());
        assertThrows(ApiException.class, () -> results.apply(s, new Response(null, response(s).memories(), bad, List.of())));
        assertEquals(0, memories.count());
    }
    @Test void unexpectedDeactivationCannotDeactivateAnotherMonth() {
        var s = queue(null, JULY);
        assertThrows(ApiException.class, () -> results.apply(s, new Response(null, response(s).memories(), s.request().scope(), List.of("mem_bbbbbbbbbbbbbbbb"))));
        assertEquals(0, memories.count());
    }
    @Test void failedCoreTransactionRollsBackRevisionAndVisibility() {
        long id = create();
        assertThrows(IllegalStateException.class, () -> tx.executeWithoutResult(t -> {
            historyService.recordChange(1, JULY, null); throw new IllegalStateException("Moment DB failure");
        }));
        assertEquals(id, service.list(1).content().getFirst().id()); assertEquals(1, revisions.findById(1L).orElseThrow().getRevision());
    }
    @Test void changeRequiresTheCoreTransaction() {
        assertThrows(org.springframework.transaction.IllegalTransactionStateException.class, () -> historyService.recordChange(1, null, JULY));
    }
    @Test void repeatedAnalysisDoesNotDuplicateMemory() {
        var s = queue(null, JULY); assertTrue(results.apply(s, response(s))); assertTrue(results.apply(s, response(s)));
        assertEquals(1, memories.count());
    }
    @Test void concurrentMutationsIncrementRevisionWithoutLosingMonths() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            var a = pool.submit(() -> tx.execute(t -> historyService.recordChange(1, null, JULY)));
            var b = pool.submit(() -> tx.execute(t -> historyService.recordChange(1, null, JULY.plusMonths(1))));
            Set<Long> returned = Set.of(a.get(10, TimeUnit.SECONDS), b.get(10, TimeUnit.SECONDS));
            assertEquals(Set.of(1L, 2L), returned);
            assertEquals(2, revisions.findById(1L).orElseThrow().getRevision());
            assertEquals(2, revisions.findById(1L).orElseThrow().months().size());
        } finally { pool.shutdownNow(); }
    }
    @Test void oversizedCompleteMonthIsNotSilentlyTruncated() {
        queue(null, JULY); history.records.clear();
        for (int i = 1; i <= 1001; i++) history.records.add(record(i, JULY));
        assertThrows(IllegalStateException.class, () -> snapshots.capture(1));
        assertFalse(revisions.findById(1L).orElseThrow().months().isEmpty());
    }
    @Test void inactiveMemoriesCannotBeMarkedReadOrReplayed() throws Exception {
        long id = create(); queue(JULY, null);
        mvc.perform(patch("/api/v1/memories/{id}/read", id).principal(() -> "1")).andExpect(status().isNotFound());
        assertThrows(ApiException.class, () -> service.replayVideoIds(1, id));
    }
    @Test void malformedMemoryIdUsesCommonErrorShape() throws Exception {
        mvc.perform(get("/api/v1/memories/not-a-number").principal(() -> "1")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_REQUEST"));
    }
    @Test void invalidSecondMemoryRollsBackEntireBatch() {
        var s = queue(null, JULY); var valid = response(s).memories().getFirst();
        var invalid = new Result("mem_bbbbbbbbbbbbbbbb", "2", valid.type(), valid.title(), valid.description(), valid.period(),
                valid.moment_ids(), valid.tracks(), valid.replay_available(), valid.context(), valid.content_hash(), valid.sync_action());
        assertThrows(ApiException.class, () -> results.apply(s, new Response(null, List.of(valid, invalid), s.request().scope(), List.of())));
        assertEquals(0, memories.count()); assertTrue(snapshots.capture(1).isPresent());
    }
    @Test void accountRemovalPreventsLateResponseFromRecreatingMemories() {
        long id = create(); var s = queue(JULY, JULY);
        tx.executeWithoutResult(t -> historyService.deleteUserMemories(1));
        assertFalse(results.apply(s, response(s))); assertEquals(0, memories.count()); assertFalse(revisions.existsById(1L));
    }
}
