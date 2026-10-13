package com.reon.backend.memory.entity;

import jakarta.persistence.*;
import lombok.Getter;
import java.time.YearMonth;
import java.util.*;
import java.util.stream.Collectors;

@Entity @Table(name = "memory_history_revision") @Getter
public class MemoryHistoryRevision {
    @Id @Column(name = "user_id") private Long userId;
    @Column(nullable = false) private long revision;
    @Column(name = "pending_months", nullable = false, length = 2048) private String pendingMonths;
    protected MemoryHistoryRevision() {}
    public Set<YearMonth> months() {
        return pendingMonths.isBlank() ? new TreeSet<>() : Arrays.stream(pendingMonths.split(","))
                .map(YearMonth::parse).collect(Collectors.toCollection(TreeSet::new));
    }
    public void advance(Collection<YearMonth> affected) {
        Set<YearMonth> months = months(); months.addAll(affected);
        if (months.size() > 120) throw new IllegalArgumentException("한 사용자의 대기 분석 범위는 최대 120개월입니다.");
        revision = Math.incrementExact(revision); setMonths(months);
    }
    public void complete(Collection<YearMonth> completed) {
        Set<YearMonth> months = months(); months.removeAll(completed); setMonths(months);
    }
    private void setMonths(Set<YearMonth> months) {
        pendingMonths = months.stream().map(YearMonth::toString).collect(Collectors.joining(","));
    }
}
