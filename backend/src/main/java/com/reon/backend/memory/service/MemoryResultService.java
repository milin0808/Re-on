package com.reon.backend.memory.service;

import com.reon.backend.global.ApiException;
import com.reon.backend.memory.dto.MemoryResponses.Context;
import com.reon.backend.memory.engine.EngineContract.*;
import com.reon.backend.memory.entity.*;
import com.reon.backend.memory.repository.*;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;
import java.time.*;
import java.util.*;
import java.util.stream.Collectors;

@Service @ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemoryResultService {
    private static final Map<String, String> TIME_LABELS = Map.of("DAWN", "새벽", "MORNING", "아침", "AFTERNOON", "오후", "EVENING", "저녁", "NIGHT", "밤");
    private final MemoryRepository memories;
    private final MemoryHistoryRevisionRepository revisions;
    private final ObjectMapper mapper;
    public MemoryResultService(MemoryRepository memories, MemoryHistoryRevisionRepository revisions, ObjectMapper mapper) {
        this.memories = memories; this.revisions = revisions; this.mapper = mapper;
    }
    /** Validation, revision comparison and every write share one locked transaction. */
    @Transactional public boolean apply(MemorySnapshotService.Snapshot snapshot, Response response) {
        var requested = snapshot.request().scope();
        long owner = Long.parseLong(requested.user_id());
        var revision = revisions.lock(owner).orElse(null);
        // A deleted account or a newer Moment mutation makes the entire response stale.
        if (revision == null || revision.getRevision() != requested.history_revision()) return false;
        validate(snapshot, response);
        var current = memories.findByUserIdAndPeriodMonthIn(owner, requested.months()).stream()
                .collect(Collectors.toMap(Memory::getEngineMemoryId, m -> m));
        Set<String> generated = response.memories().stream().map(Result::memory_id).collect(Collectors.toSet());
        // Derive changes from the trusted DB and generated set, rather than trusting sync_action.
        for (var result : response.memories()) {
            var memory = current.get(result.memory_id());
            if (memory == null) {
                if (memories.findByEngineMemoryId(result.memory_id()).isPresent()) throw invalidResult();
                memory = new Memory(owner, result.memory_id(), result.period().month());
            }
            var moments = result.moment_ids().stream().map(snapshot.moments()::get)
                    .sorted(Comparator.comparing(com.reon.backend.memory.port.MomentHistoryReader.Record::recordedAt)
                            .thenComparingLong(com.reon.backend.memory.port.MomentHistoryReader.Record::id))
                    .map(m -> new MemoryMoment(m.id(), m.recordedAt(), m.music().title(), m.music().artist(), m.memo())).toList();
            memory.replace(result.type(), result.title(), result.description(), LocalDate.parse(result.period().start()),
                    LocalDate.parse(result.period().end()), mapper.writeValueAsString(contexts(result)),
                    mapper.writeValueAsString(result.tracks()), result.content_hash(), revision.getRevision(), moments);
            memories.save(memory);
        }
        for (var memory : current.values()) if (!generated.contains(memory.getEngineMemoryId())) memory.deactivate(revision.getRevision());
        revision.complete(requested.months().stream().map(YearMonth::parse).toList());
        return true;
    }
    private void validate(MemorySnapshotService.Snapshot snapshot, Response response) {
        try {
            if (response == null || !snapshot.request().scope().equals(response.scope()) || response.memories() == null
                    || response.deactivated_memory_ids() == null || response.memories().size() > 3) throw invalidResult();
            Set<String> ids = new HashSet<>();
            for (var r : response.memories()) {
                if (r == null || r.memory_id() == null || !r.memory_id().matches("mem_[a-f0-9]{16}") || !ids.add(r.memory_id())
                        || !snapshot.request().userId().equals(r.user_id()) || !Set.of("ARTIST", "LOCATION", "TIME").contains(r.type())
                        || r.title() == null || r.title().isBlank() || r.title().length() > 512
                        || r.description() == null || r.description().isBlank() || r.description().length() > 8000
                        || r.content_hash() == null || !r.content_hash().matches("[a-f0-9]{64}")
                        || r.period() == null || !snapshot.request().scope().months().contains(r.period().month())
                        || r.moment_ids() == null || r.moment_ids().isEmpty() || r.context() == null || !r.context().isObject()
                        || r.tracks() == null || r.replay_available() != !r.tracks().isEmpty()) throw invalidResult();
                Set<String> momentIds = new HashSet<>();
                List<LocalDate> dates = new ArrayList<>();
                Set<String> allowedTracks = new HashSet<>();
                for (String id : r.moment_ids()) {
                    var moment = snapshot.moments().get(id);
                    if (moment == null || !momentIds.add(id)) throw invalidResult();
                    dates.add(moment.recordedAt().withOffsetSameInstant(MemoryHistoryService.ANALYSIS_OFFSET).toLocalDate());
                    if (moment.music().videoId() != null) allowedTracks.add(moment.music().videoId());
                }
                if (!Collections.min(dates).equals(LocalDate.parse(r.period().start()))
                        || !Collections.max(dates).equals(LocalDate.parse(r.period().end()))
                        || !r.context().path("count").isIntegralNumber() || r.context().path("count").asInt() != momentIds.size()) throw invalidResult();
                Set<String> trackIds = new HashSet<>();
                for (var track : r.tracks()) {
                    if (track == null || !allowedTracks.contains(track.track_id()) || !trackIds.add(track.track_id())) throw invalidResult();
                }
                contexts(r); // Reject malformed context before any database write.
            }
            Set<String> expectedDeactivated = snapshot.request().existing_memories().stream()
                    .filter(Existing::is_active).map(Existing::memory_id).filter(id -> !ids.contains(id)).collect(Collectors.toSet());
            if (new HashSet<>(response.deactivated_memory_ids()).size() != response.deactivated_memory_ids().size()
                    || !expectedDeactivated.equals(new HashSet<>(response.deactivated_memory_ids()))) throw invalidResult();
        } catch (ApiException ex) { throw ex; }
        catch (RuntimeException ex) { throw invalidResult(); }
    }
    private List<Context> contexts(Result result) {
        var ctx = result.context();
        List<Context> contexts = new ArrayList<>();
        String band = ctx.path("dominant_time_band").asText("");
        double ratio = ctx.path("dominant_time_ratio").asDouble(-1);
        if (!TIME_LABELS.containsKey(band) || !Double.isFinite(ratio) || ratio < 0 || ratio > 1) throw invalidResult();
        contexts.add(new Context("TIME", TIME_LABELS.get(band), Math.round(ratio * 100) + "%"));
        var place = ctx.path("top_location");
        if (place.isTextual() && !place.asText().isBlank()) contexts.add(new Context("PLACE", place.asText(), null));
        return List.copyOf(contexts);
    }
    private static ApiException invalidResult() {
        return new ApiException(HttpStatus.BAD_GATEWAY, "INVALID_MEMORY_ENGINE_RESPONSE", "Memory 분석 결과의 사용자·범위 또는 데이터가 올바르지 않습니다.");
    }
}
