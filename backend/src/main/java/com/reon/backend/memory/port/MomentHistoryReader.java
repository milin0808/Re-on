package com.reon.backend.memory.port;

import com.reon.backend.memory.engine.EngineContract.*;
import java.time.*;
import java.util.List;

/** Core implements this with its Moment repository. Never return a page or another user's records. */
public interface MomentHistoryReader {
    List<Record> readCompleteMonth(long userId, YearMonth month);
    record Record(long id, long userId, OffsetDateTime recordedAt, Music music, String memo, Location location) {
        public Moment engineMoment() {
            return new Moment(id, Long.toString(userId), recordedAt.toString(), music, memo, location);
        }
    }
}
