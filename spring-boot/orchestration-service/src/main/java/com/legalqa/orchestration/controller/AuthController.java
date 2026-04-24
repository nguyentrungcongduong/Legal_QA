package com.legalqa.orchestration.controller;

import com.legalqa.orchestration.auth.JwtUtils;
import com.legalqa.orchestration.dto.LoginRequest;
import com.legalqa.orchestration.dto.RegisterRequest;
import com.legalqa.orchestration.model.User;
import com.legalqa.orchestration.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserRepository userRepo;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtils jwtUtils;

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest req) {
        if (userRepo.existsByEmail(req.getEmail())) {
            return ResponseEntity.badRequest()
                .body(Map.of("message", "Email đã tồn tại"));
        }

        User user = User.builder()
            .id(UUID.randomUUID().toString())
            .email(req.getEmail())
            .passwordHash(passwordEncoder.encode(req.getPassword()))
            .createdAt(LocalDateTime.now())
            .build();

        userRepo.save(user);

        String token = jwtUtils.generateToken(
            user.getId(),
            user.getEmail()
        );

        return ResponseEntity.ok(Map.of(
            "token", token,
            "email", user.getEmail()
        ));
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest req) {
        User user = userRepo.findByEmail(req.getEmail())
            .orElseThrow(() -> new RuntimeException("Email không tồn tại"));

        if (!passwordEncoder.matches(req.getPassword(), user.getPasswordHash())) {
            return ResponseEntity.status(401)
                .body(Map.of("message", "Sai mật khẩu"));
        }

        String token = jwtUtils.generateToken(
            user.getId(),
            user.getEmail()
        );

        return ResponseEntity.ok(Map.of(
            "token", token,
            "email", user.getEmail(),
            "userId", user.getId()
        ));
    }
}
