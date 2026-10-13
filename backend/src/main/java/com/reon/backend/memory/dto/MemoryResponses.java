package com.reon.backend.memory.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.*;
import java.util.List;

public final class MemoryResponses {
    private MemoryResponses() {}
    public record ListResponse(List<Summary> content) {}
    public record Summary(long id, String title, String description, int momentCount,
                          LocalDate startDate, LocalDate endDate, boolean isNew) {}
    public record Detail(long id, String title, String description, LocalDate startDate, LocalDate endDate,
                         int momentCount, List<Context> contexts, List<Moment> moments) {}
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Context(String type, String label, String value) {}
    public record Moment(long id, OffsetDateTime recordedAt, String title, String artist, String memo) {}
    public record ReadResponse(long id, boolean isNew) {}
}
