package com.legalqa.orchestration.auth;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Date;

@Component
public class JwtUtils {

    @Value("${app.jwt.secret}")
    private String jwtSecret;

    @Value("${app.jwt.expiration-ms}")
    private long jwtExpirationMs;

    @jakarta.annotation.PostConstruct
    public void init() {
        System.out.println("====== JWT SECRET LENGTH: " + (jwtSecret != null ? jwtSecret.length() : 0) + " ======");
        if (jwtSecret != null) {
            System.out.print("====== SECRET CHARS: ");
            for (int i = 0; i < jwtSecret.length(); i++) {
                System.out.print("[" + (int)jwtSecret.charAt(i) + "='" + jwtSecret.charAt(i) + "'] ");
            }
            System.out.println("======");
        }
    }

    public String generateToken(String userId, String email) {
        return Jwts.builder()
            .setSubject(userId)
            .claim("email", email)
            .setIssuedAt(new Date())
            .setExpiration(new Date(System.currentTimeMillis() + jwtExpirationMs))
            .signWith(Keys.hmacShaKeyFor(jwtSecret.getBytes()), SignatureAlgorithm.HS256)
            .compact();
    }

    public String getUserIdFromToken(String token) {
        return Jwts.parserBuilder()
            .setSigningKey(Keys.hmacShaKeyFor(jwtSecret.getBytes()))
            .build()
            .parseClaimsJws(token)
            .getBody()
            .getSubject();
    }

    public boolean validateToken(String token) {
        try {
            Jwts.parserBuilder()
                .setSigningKey(Keys.hmacShaKeyFor(jwtSecret.getBytes()))
                .build()
                .parseClaimsJws(token);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
