package com.reon.backend.memory.repository;

import com.reon.backend.memory.entity.Memory;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import java.util.*;

public interface MemoryRepository extends JpaRepository<Memory, Long> {
    List<Memory> findByUserIdAndActiveTrueOrderByEndDateDescIdDesc(long userId);
    Optional<Memory> findByIdAndUserIdAndActiveTrue(long id, long userId);
    Optional<Memory> findByEngineMemoryId(String engineMemoryId);
    List<Memory> findByUserIdAndPeriodMonthIn(long userId, Collection<String> months);
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select m from Memory m where m.id = :id and m.userId = :userId and m.active = true")
    Optional<Memory> findOwnedForUpdate(@Param("id") long id, @Param("userId") long userId);
    @Modifying
    @Query("delete from Memory m where m.userId = :userId")
    void deleteAllByOwner(@Param("userId") long userId);
}
