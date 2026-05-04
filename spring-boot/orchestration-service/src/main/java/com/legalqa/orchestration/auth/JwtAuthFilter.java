package com.legalqa.orchestration.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
@RequiredArgsConstructor
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtUtils jwtUtils;

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Bỏ qua JWT filter cho các route auth (login/register)
        String path = request.getServletPath();
        return path.startsWith("/api/auth/");
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain chain
    ) throws ServletException, IOException {

        String header = request.getHeader("Authorization");
        String path = request.getServletPath();

        if (header == null || !header.startsWith("Bearer ")) {
            System.err.println("[JwtFilter] NO token on: " + path);
            chain.doFilter(request, response);
            return;
        }

        String token = header.substring(7);
        System.err.println("[JwtFilter] Token received on: " + path + " | token prefix: " + token.substring(0, Math.min(20, token.length())) + "...");

        try {
            if (jwtUtils.validateToken(token)) {
                String userId = jwtUtils.getUserIdFromToken(token);
                System.err.println("[JwtFilter] Token VALID - userId: " + userId);

                UsernamePasswordAuthenticationToken auth =
                    new UsernamePasswordAuthenticationToken(
                        userId, null, List.of()
                    );

                // Spring Security 6: phải tạo context MỚI và set vào holder
                // (không modify context hiện tại — DeferredSecurityContext không memoize đúng)
                var context = SecurityContextHolder.createEmptyContext();
                context.setAuthentication(auth);
                SecurityContextHolder.setContext(context);

                System.err.println("[JwtFilter] SecurityContext set OK");
            } else {
                System.err.println("[JwtFilter] Token INVALID");
            }
        } catch (Exception e) {
            System.err.println("[JwtFilter] Token ERROR: " + e.getMessage());
            SecurityContextHolder.clearContext();
        }


        chain.doFilter(request, response);
    }
}
