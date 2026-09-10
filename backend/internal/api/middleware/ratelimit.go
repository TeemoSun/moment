package middleware

import (
	"fmt"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"backend/internal/config"
	"backend/internal/model"
)

type RateLimiter struct {
	cfg      *config.Config
	mu       sync.Mutex
	attempts map[string][]float64
}

func NewRateLimiter(cfg *config.Config) *RateLimiter {
	return &RateLimiter{
		cfg:      cfg,
		attempts: make(map[string][]float64),
	}
}

func (l *RateLimiter) Hit(scope, ip string, limit, windowSeconds int) error {
	if !l.cfg.RateLimitEnabled {
		return nil
	}

	key := fmt.Sprintf("%s:%s", scope, ip)
	now := float64(time.Now().UnixNano()) / 1e9

	l.mu.Lock()
	defer l.mu.Unlock()

	history := l.attempts[key]
	threshold := now - float64(windowSeconds)

	// Filter expired timestamps
	valid := history[:0]
	for _, ts := range history {
		if ts > threshold {
			valid = append(valid, ts)
		}
	}

	if len(valid) >= limit {
		retryAfter := int(valid[0] + float64(windowSeconds) - now) + 1
		l.attempts[key] = valid
		return model.NewAppError(
			model.ErrRateLimited,
			"请求过于频繁，请稍后再试",
			429,
			map[string]any{"retry_after_seconds": retryAfter},
		)
	}

	valid = append(valid, now)
	l.attempts[key] = valid

	// Evict old keys if too many
	if len(l.attempts) > 100000 {
		for k, q := range l.attempts {
			if len(q) == 0 || q[len(q)-1] <= now-3600 {
				delete(l.attempts, k)
			}
		}
	}

	return nil
}

func GetClientIP(r *http.Request) string {
	// Check X-Forwarded-For
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		if len(parts) > 0 {
			ip := strings.TrimSpace(parts[0])
			if ip != "" {
				return ip
			}
		}
	}
	// Check X-Real-IP
	if xri := r.Header.Get("X-Real-IP"); xri != "" {
		return strings.TrimSpace(xri)
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err == nil {
		return host
	}
	return r.RemoteAddr
}
