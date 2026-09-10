package middleware

import (
	"sync"
	"testing"

	"backend/internal/config"
	"backend/internal/model"
)

func TestRateLimiter_SlidingWindow(t *testing.T) {
	cfg := &config.Config{
		RateLimitEnabled: true,
	}
	limiter := NewRateLimiter(cfg)

	scope := "test"
	ip := "192.168.1.100"
	limit := 3
	window := 60

	// 1st hit
	if err := limiter.Hit(scope, ip, limit, window); err != nil {
		t.Fatalf("1st hit should pass, got: %v", err)
	}

	// 2nd hit
	if err := limiter.Hit(scope, ip, limit, window); err != nil {
		t.Fatalf("2nd hit should pass, got: %v", err)
	}

	// 3rd hit
	if err := limiter.Hit(scope, ip, limit, window); err != nil {
		t.Fatalf("3rd hit should pass, got: %v", err)
	}

	// 4th hit should be rate limited
	err := limiter.Hit(scope, ip, limit, window)
	if err == nil {
		t.Fatalf("4th hit should be rate limited, got nil")
	}

	appErr, ok := err.(*model.AppError)
	if !ok {
		t.Fatalf("expected *model.AppError, got %T", err)
	}

	if appErr.StatusCode != 429 {
		t.Errorf("expected status code 429, got %d", appErr.StatusCode)
	}

	if appErr.Code != model.ErrRateLimited {
		t.Errorf("expected code RATE_LIMITED, got %s", appErr.Code)
	}
}

func TestRateLimiter_ConcurrentSafety(t *testing.T) {
	cfg := &config.Config{
		RateLimitEnabled: true,
	}
	limiter := NewRateLimiter(cfg)

	scope := "concurrent"
	ip := "10.0.0.1"
	limit := 50
	window := 10

	var wg sync.WaitGroup
	var rejectedCount int
	var mu sync.Mutex

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if err := limiter.Hit(scope, ip, limit, window); err != nil {
				mu.Lock()
				rejectedCount++
				mu.Unlock()
			}
		}()
	}

	wg.Wait()

	if rejectedCount != 50 {
		t.Errorf("expected 50 rejections, got %d", rejectedCount)
	}
}
