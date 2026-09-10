package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"backend/internal/config"
)

func TestCSRF_Methods(t *testing.T) {
	cfg := &config.Config{
		CSRFCookieName: "moments_csrf",
	}

	nextHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})

	csrfMW := CSRF(cfg)(nextHandler)

	// 1. GET should pass without CSRF header or cookie
	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	rec := httptest.NewRecorder()
	csrfMW.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Errorf("GET should pass, got status %d", rec.Code)
	}

	// 2. POST without CSRF header should fail (403)
	req = httptest.NewRequest(http.MethodPost, "/test", nil)
	rec = httptest.NewRecorder()
	csrfMW.ServeHTTP(rec, req)
	if rec.Code != http.StatusForbidden {
		t.Errorf("POST without CSRF header should fail 403, got status %d", rec.Code)
	}

	// 3. POST with mismatched header and cookie should fail (403)
	req = httptest.NewRequest(http.MethodPost, "/test", nil)
	req.Header.Set("X-CSRF-Token", "token123")
	req.AddCookie(&http.Cookie{Name: "moments_csrf", Value: "token456"})
	rec = httptest.NewRecorder()
	csrfMW.ServeHTTP(rec, req)
	if rec.Code != http.StatusForbidden {
		t.Errorf("POST with mismatched CSRF should fail 403, got status %d", rec.Code)
	}

	// 4. POST with matching header and cookie should succeed (200)
	req = httptest.NewRequest(http.MethodPost, "/test", nil)
	req.Header.Set("X-CSRF-Token", "validtoken123")
	req.AddCookie(&http.Cookie{Name: "moments_csrf", Value: "validtoken123"})
	rec = httptest.NewRecorder()
	csrfMW.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Errorf("POST with matching CSRF should pass 200, got status %d", rec.Code)
	}
}
