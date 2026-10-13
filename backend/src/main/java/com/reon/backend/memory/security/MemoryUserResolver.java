package com.reon.backend.memory.security;

import com.reon.backend.global.ApiException;
import java.security.Principal;
import org.springframework.http.HttpStatus;

/** Auth filter supplies a verified database user ID as Principal.getName(). */
public final class MemoryUserResolver {
    private MemoryUserResolver() {}
    public static long requireUserId(Principal principal) {
        if (principal != null) {
            try {
                long id = Long.parseLong(principal.getName());
                if (id > 0) return id;
            } catch (NumberFormatException ignored) {}
        }
        throw new ApiException(HttpStatus.UNAUTHORIZED, "UNAUTHORIZED", "로그인이 필요합니다.");
    }
}
