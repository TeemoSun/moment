package tests

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"backend/internal/model"
)

func TestAuth_InvalidCredentialsAndLockout(t *testing.T) {
	_, router, _, teardown := setupTestApp(t)
	if router == nil {
		return
	}
	defer teardown()

	// 1. Get RSA key
	req := httptest.NewRequest(http.MethodGet, "/api/v1/auth/rsa-public-key", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	var rsaOut model.RSAKeyOut
	_ = json.Unmarshal(rec.Body.Bytes(), &rsaOut)

	// 2. Init Admin
	adminPW := "AdminPass123!"
	initBody, _ := json.Marshal(model.InitIn{
		Email:    "admin@test.local",
		Nickname: "Admin",
		Password: encryptWithPubKey(t, rsaOut.PublicKey, adminPW),
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/system/init", bytes.NewReader(initBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	// 3. Login with wrong password 4 times (returns 401 INVALID_CREDENTIALS)
	wrongPW := encryptWithPubKey(t, rsaOut.PublicKey, "WrongPassword999!")
	for i := 1; i <= 4; i++ {
		loginBody, _ := json.Marshal(model.LoginIn{
			Email:    "admin@test.local",
			Password: wrongPW,
		})
		req = httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(loginBody))
		req.Header.Set("Content-Type", "application/json")
		rec = httptest.NewRecorder()
		router.ServeHTTP(rec, req)

		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("attempt %d: expected status 401, got %d", i, rec.Code)
		}
		var errOut model.ErrorOut
		_ = json.Unmarshal(rec.Body.Bytes(), &errOut)
		if errOut.Code != model.ErrInvalidCredentials {
			t.Fatalf("attempt %d: expected code INVALID_CREDENTIALS, got %s", i, errOut.Code)
		}
	}

	// 4. 5th failed attempt should trigger account lockout (returns 403 ACCOUNT_LOCKED)
	loginBody, _ := json.Marshal(model.LoginIn{
		Email:    "admin@test.local",
		Password: wrongPW,
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/auth/login", bytes.NewReader(loginBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	if rec.Code != http.StatusForbidden {
		t.Fatalf("5th attempt: expected status 403, got %d", rec.Code)
	}
	var errOut model.ErrorOut
	_ = json.Unmarshal(rec.Body.Bytes(), &errOut)
	if errOut.Code != model.ErrAccountLocked {
		t.Fatalf("5th attempt: expected code ACCOUNT_LOCKED, got %s", errOut.Code)
	}
}

func TestAuth_TokenVersionInvalidation(t *testing.T) {
	_, router, _, teardown := setupTestApp(t)
	if router == nil {
		return
	}
	defer teardown()

	// 1. Get RSA key
	req := httptest.NewRequest(http.MethodGet, "/api/v1/auth/rsa-public-key", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	var rsaOut model.RSAKeyOut
	_ = json.Unmarshal(rec.Body.Bytes(), &rsaOut)

	// 2. Init Admin
	oldPW := "OldPassword123!"
	initBody, _ := json.Marshal(model.InitIn{
		Email:    "admin@invalidation.local",
		Nickname: "Admin",
		Password: encryptWithPubKey(t, rsaOut.PublicKey, oldPW),
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/system/init", bytes.NewReader(initBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)

	sessionCookie, csrfCookie := extractCookies(rec.Result())

	// 3. Verify /me works with original token
	req = httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
	req.AddCookie(sessionCookie)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("/me failed with valid session, got %d", rec.Code)
	}

	// 4. Change password -> bumps token_version
	newPW := "NewPassword123!"
	pwChangeBody, _ := json.Marshal(model.PasswordChangeIn{
		OldPassword: encryptWithPubKey(t, rsaOut.PublicKey, oldPW),
		NewPassword: encryptWithPubKey(t, rsaOut.PublicKey, newPW),
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/me/password", bytes.NewReader(pwChangeBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", csrfCookie.Value)
	req.AddCookie(sessionCookie)
	req.AddCookie(csrfCookie)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("Change password failed: status %d: %s", rec.Code, rec.Body.String())
	}

	// 5. Old session token should now be rejected (401 AUTH_REQUIRED)
	req = httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
	req.AddCookie(sessionCookie)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusUnauthorized {
		t.Fatalf("Old token should be rejected after password change, got status %d", rec.Code)
	}
}
