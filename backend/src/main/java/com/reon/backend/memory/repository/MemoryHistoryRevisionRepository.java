package com.reon.backend.memory.repository;

import com.reon.backend.memory.entity.MemoryHistoryRevision;
import jakarta.persistence.LockModeType;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import java.util.*;

public interface MemoryHistoryRevisionRepository extends JpaRepository<MemoryHistoryRevision, Long> {
    @Modifying
    @Query(value = "INSERT INTO memory_history_revision (user_id, revision, pending_months) VALUES (:userId, 0, '') ON DUPLICATE KEY UPDATE revision = revision", nativeQuery = true)
    void initialize(@Param("userId") long userId);
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from MemoryHistoryRevision r where r.userId = :userId")
    Optional<MemoryHistoryRevision> lock(@Param("userId") long userId);
    @Query("select r.userId from MemoryHistoryRevision r where r.pendingMonths <> '' and r.userId > :after order by r.userId")
    List<Long> pendingUsersAfter(@Param("after") long after, Pageable pageable);
}
