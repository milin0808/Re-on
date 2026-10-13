package com.reon.backend.memory.engine;

import tools.jackson.databind.JsonNode;
import java.util.List;

/** The snake_case fields intentionally match the FastAPI internal protocol. */
public final class EngineContract {
    private EngineContract() {}
    public record Scope(String user_id, List<String> months, boolean complete_month_history, long history_revision) {}
    public record Existing(String memory_id, String user_id, String period_month, boolean is_active, String content_hash) {}
    public record Music(String videoId, String title, String artist, String channelTitle, String thumbnailUrl, String originalUrl) {}
    public record Location(double latitude, double longitude) {}
    public record Moment(long id, String userId, String recordedAt, Music music, String memo, Location location) {}
    public record Request(String userId, List<Moment> moments, List<Existing> existing_memories, Scope scope) {}
    public record Period(String month, String start, String end) {}
    public record Track(String track_id, String artist, String song_title) {}
    public record Result(String memory_id, String user_id, String type, String title, String description,
                         Period period, List<String> moment_ids, List<Track> tracks, boolean replay_available,
                         JsonNode context, String content_hash, String sync_action) {}
    public record Response(JsonNode meta, List<Result> memories, Scope scope, List<String> deactivated_memory_ids) {}
}
