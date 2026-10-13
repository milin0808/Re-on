package com.reon.backend.memory.service;

import com.reon.backend.global.ApiException;
import com.reon.backend.memory.dto.MemoryResponses.*;
import com.reon.backend.memory.entity.Memory;
import com.reon.backend.memory.repository.MemoryRepository;
import com.reon.backend.memory.engine.EngineContract.Track;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;
import java.time.ZoneOffset;
import java.util.List;

@Service @Transactional(readOnly = true)
@ConditionalOnProperty(name = "memory.enabled", havingValue = "true")
public class MemoryService {
    private final MemoryRepository repository;
    private final ObjectMapper mapper;
    public MemoryService(MemoryRepository repository, ObjectMapper mapper) {
        this.repository = repository; this.mapper = mapper;
    }
    public ListResponse list(long userId) {
        return new ListResponse(repository.findByUserIdAndActiveTrueOrderByEndDateDescIdDesc(userId).stream()
                .map(m -> new Summary(m.getId(), m.getTitle(), m.getDescription(), m.getMomentCount(),
                        m.getStartDate(), m.getEndDate(), m.isNew())).toList());
    }
    public Detail detail(long userId, long id) {
        Memory m = repository.findByIdAndUserIdAndActiveTrue(id, userId).orElseThrow(MemoryService::notFound);
        List<Context> contexts = mapper.readValue(m.getContextsJson(), new TypeReference<>() {});
        var moments = m.getMoments().stream().map(x -> new Moment(x.getMomentId(),
                x.getRecordedAt().withOffsetSameInstant(ZoneOffset.ofHours(9)), x.getTitle(), x.getArtist(), x.getMemo())).toList();
        return new Detail(m.getId(), m.getTitle(), m.getDescription(), m.getStartDate(), m.getEndDate(),
                m.getMomentCount(), contexts, moments);
    }
    @Transactional public ReadResponse markRead(long userId, long id) {
        Memory m = repository.findOwnedForUpdate(id, userId).orElseThrow(MemoryService::notFound);
        m.markRead(); return new ReadResponse(m.getId(), false);
    }
    /** RE:PLAY service uses this method; it performs the same owner/active checks as detail. */
    public List<String> replayVideoIds(long userId, long id) {
        Memory m = repository.findByIdAndUserIdAndActiveTrue(id, userId).orElseThrow(MemoryService::notFound);
        List<Track> tracks = mapper.readValue(m.getTracksJson(), new TypeReference<>() {});
        return tracks.stream().map(Track::track_id).distinct().toList();
    }
    private static ApiException notFound() {
        return new ApiException(HttpStatus.NOT_FOUND, "MEMORY_NOT_FOUND", "Memory를 찾을 수 없습니다.");
    }
}
