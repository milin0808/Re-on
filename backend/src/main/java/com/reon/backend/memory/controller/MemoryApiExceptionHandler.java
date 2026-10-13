package com.reon.backend.memory.controller;

import com.reon.backend.global.GlobalExceptionHandler.ErrorResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

@RestControllerAdvice(assignableTypes = MemoryController.class)
public class MemoryApiExceptionHandler {
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponse> invalidId() {
        return ResponseEntity.badRequest().body(new ErrorResponse("INVALID_REQUEST", "Memory ID는 정수여야 합니다."));
    }
}
