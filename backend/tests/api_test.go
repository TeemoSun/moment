package tests

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"backend/internal/api"
	"backend/internal/api/middleware"
	"backend/internal/config"
	"backend/internal/database"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/service"
	"github.com/jackc/pgx/v5/pgxpool"
)

func setupTestApp(t *testing.T) (*config.Config, http.Handler, *pgxpool.Pool, func()) {
	testDBURL := os.Getenv("TEST_DATABASE_URL")
	if testDBURL == "" {
		testDBURL = "postgres://moments:moments@localhost:5432/moments_test"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	pool, err := database.NewPool(ctx, testDBURL)
	if err != nil {
		t.Skipf("Skipping integration test: database %s not reachable: %v", testDBURL, err)
		return nil, nil, nil, nil
	}

	// Clean tables before test
	cleanTables := `
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
`
	_, err = pool.Exec(context.Background(), cleanTables)
	if err != nil {
		t.Fatalf("failed to clean test database: %v", err)
	}

	tempDir, err := os.MkdirTemp("", "moments_test_*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}

	cfg := &config.Config{
		AppName:                "Moments Test",
		Debug:                  true,
		SecureCookies:          false,
		RateLimitEnabled:       true,
		AllowInsecureClipboard: true,
		DBURL:                  testDBURL,
		JWTSecret:              "test-jwt-secret-very-long-and-secure-random-48bytes!",
		JWTAlgorithm:           "HS256",
		JWTExpireDays:          7,
		CookieName:             "moments_token",
		CSRFCookieName:         "moments_csrf",
		StorageRoot:            tempDir,
		MediaImageMaxMB:        20,
		MediaVideoMaxMB:        100,
		ThumbSize:              400,
		LargeSize:              1280,
		WebpThumbQuality:       80,
		WebpLargeQuality:       85,
		BackendHost:            "127.0.0.1",
		BackendPort:            8000,
		FrontendDist:           tempDir,
		ProjectRoot:            tempDir,
	}

	// Run migrations
	if err := database.RunMigrations(context.Background(), pool, tempDir); err != nil {
		t.Fatalf("RunMigrations failed: %v", err)
	}

	repos := repository.NewRepositories(pool)
	services := service.NewServices(cfg, repos, func(botUserID int) {})
	rateLimiter := middleware.NewRateLimiter(cfg)

	router := api.NewRouter(cfg, repos, services, rateLimiter, func(mediaID int, kind string) {})

	teardown := func() {
		pool.Close()
		_ = os.RemoveAll(tempDir)
	}

	return cfg, router, pool, teardown
}

func encryptWithPubKey(t *testing.T, pubKeyPEM, plaintext string) string {
	block, _ := pem.Decode([]byte(pubKeyPEM))
	if block == nil {
		t.Fatalf("failed to decode public key PEM")
	}
	pubInterface, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		t.Fatalf("failed to parse PKIX public key: %v", err)
	}
	pubKey, ok := pubInterface.(*rsa.PublicKey)
	if !ok {
		t.Fatalf("key is not rsa.PublicKey")
	}

	cipherBytes, err := rsa.EncryptPKCS1v15(rand.Reader, pubKey, []byte(plaintext))
	if err != nil {
		t.Fatalf("EncryptPKCS1v15 failed: %v", err)
	}
	return base64.StdEncoding.EncodeToString(cipherBytes)
}

func extractCookies(resp *http.Response) (sessionCookie, csrfCookie *http.Cookie) {
	for _, c := range resp.Cookies() {
		if c.Name == "moments_token" {
			sessionCookie = c
		} else if c.Name == "moments_csrf" {
			csrfCookie = c
		}
	}
	return
}

func TestAPI_CompleteFlow(t *testing.T) {
	cfg, router, _, teardown := setupTestApp(t)
	if router == nil {
		return
	}
	defer teardown()

	// 1. GET /api/health
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/health status %d, want 200", rec.Code)
	}
	var healthResp map[string]string
	_ = json.Unmarshal(rec.Body.Bytes(), &healthResp)
	if healthResp["status"] != "ok" {
		t.Errorf("health status = %s, want ok", healthResp["status"])
	}

	// 2. GET /api/v1/system/initialized -> false
	req = httptest.NewRequest(http.MethodGet, "/api/v1/system/initialized", nil)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /system/initialized status %d, want 200", rec.Code)
	}
	var initStatus model.InitializedOut
	_ = json.Unmarshal(rec.Body.Bytes(), &initStatus)
	if initStatus.Initialized {
		t.Errorf("expected initialized = false on fresh database")
	}

	// 3. GET /api/v1/auth/rsa-public-key
	req = httptest.NewRequest(http.MethodGet, "/api/v1/auth/rsa-public-key", nil)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /auth/rsa-public-key status %d, want 200", rec.Code)
	}
	var rsaOut model.RSAKeyOut
	_ = json.Unmarshal(rec.Body.Bytes(), &rsaOut)
	if !strings.Contains(rsaOut.PublicKey, "BEGIN PUBLIC KEY") {
		t.Fatalf("invalid public key PEM: %s", rsaOut.PublicKey)
	}

	// 4. POST /api/v1/system/init (create admin)
	adminPW := "AdminPass123!"
	encryptedAdminPW := encryptWithPubKey(t, rsaOut.PublicKey, adminPW)
	initBody, _ := json.Marshal(model.InitIn{
		Email:    "admin@moments.local",
		Nickname: "SuperAdmin",
		Password: encryptedAdminPW,
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/system/init", bytes.NewReader(initBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /system/init status %d: %s", rec.Code, rec.Body.String())
	}

	var adminToken model.TokenOut
	_ = json.Unmarshal(rec.Body.Bytes(), &adminToken)
	if adminToken.User.Role != "admin" {
		t.Errorf("admin role mismatch: got %s, want admin", adminToken.User.Role)
	}

	adminSession, adminCSRF := extractCookies(rec.Result())
	if adminSession == nil || adminCSRF == nil {
		t.Fatalf("expected session and csrf cookies to be set")
	}

	// 5. Verify system is now initialized
	req = httptest.NewRequest(http.MethodGet, "/api/v1/system/initialized", nil)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	_ = json.Unmarshal(rec.Body.Bytes(), &initStatus)
	if !initStatus.Initialized {
		t.Errorf("expected initialized = true after init")
	}

	// 6. Admin creates invite code
	durationDays := 7
	inviteBody, _ := json.Marshal(model.InviteCreateIn{
		DurationDays: &durationDays,
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/invites", bytes.NewReader(inviteBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", adminCSRF.Value)
	req.AddCookie(adminSession)
	req.AddCookie(adminCSRF)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /invites status %d: %s", rec.Code, rec.Body.String())
	}

	var inviteOut model.InviteOut
	_ = json.Unmarshal(rec.Body.Bytes(), &inviteOut)
	if inviteOut.Code == "" {
		t.Fatalf("empty invite code returned")
	}

	// 7. Regular user registers using the invite code
	userPW := "UserPass123!"
	encryptedUserPW := encryptWithPubKey(t, rsaOut.PublicKey, userPW)
	regBody, _ := json.Marshal(model.RegisterIn{
		Email:      "alice@moments.local",
		Nickname:   "Alice",
		Password:   encryptedUserPW,
		InviteCode: inviteOut.Code,
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewReader(regBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /auth/register status %d: %s", rec.Code, rec.Body.String())
	}

	var userToken model.TokenOut
	_ = json.Unmarshal(rec.Body.Bytes(), &userToken)
	if userToken.User.Role != "user" || userToken.User.Nickname != "Alice" {
		t.Errorf("registered user mismatch: got %+v", userToken.User)
	}

	userSession, userCSRF := extractCookies(rec.Result())
	if userSession == nil || userCSRF == nil {
		t.Fatalf("expected user session and csrf cookies to be set")
	}

	// 8. User posts a moment
	postBody, _ := json.Marshal(model.PostCreateIn{
		Content:    "Hello World! This is my first moment in Go backend.",
		Visibility: "public",
		MediaIDs:   []int{},
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/posts", bytes.NewReader(postBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", userCSRF.Value)
	req.AddCookie(userSession)
	req.AddCookie(userCSRF)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /posts status %d: %s", rec.Code, rec.Body.String())
	}

	var postOut model.PostOut
	_ = json.Unmarshal(rec.Body.Bytes(), &postOut)
	if postOut.Content != "Hello World! This is my first moment in Go backend." {
		t.Errorf("created post content mismatch: got %s", postOut.Content)
	}

	// 9. User likes own post
	req = httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/v1/posts/%d/likes", postOut.ID), nil)
	req.Header.Set("X-CSRF-Token", userCSRF.Value)
	req.AddCookie(userSession)
	req.AddCookie(userCSRF)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /posts/%d/likes status %d: %s", postOut.ID, rec.Code, rec.Body.String())
	}

	var likeOut model.LikeCountOut
	_ = json.Unmarshal(rec.Body.Bytes(), &likeOut)
	if likeOut.LikeCount != 1 || !likeOut.LikedByMe {
		t.Errorf("like response mismatch: got %+v", likeOut)
	}

	// 10. User creates a comment on the post
	commentText := "Welcome to Moments!"
	commentBody, _ := json.Marshal(model.CommentCreateIn{
		Content: &commentText,
	})
	req = httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/v1/posts/%d/comments", postOut.ID), bytes.NewReader(commentBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", userCSRF.Value)
	req.AddCookie(userSession)
	req.AddCookie(userCSRF)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /posts/%d/comments status %d: %s", postOut.ID, rec.Code, rec.Body.String())
	}

	var commentOut model.CommentOut
	_ = json.Unmarshal(rec.Body.Bytes(), &commentOut)
	if commentOut.Content == nil || *commentOut.Content != commentText {
		t.Errorf("comment content mismatch: got %v", commentOut.Content)
	}

	// 11. User fetches feed: check post, author, like count, comment count
	req = httptest.NewRequest(http.MethodGet, "/api/v1/feed", nil)
	req.AddCookie(userSession)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("GET /feed status %d: %s", rec.Code, rec.Body.String())
	}

	var feedOut model.FeedOut
	_ = json.Unmarshal(rec.Body.Bytes(), &feedOut)
	if len(feedOut.Items) != 1 {
		t.Fatalf("feed items count = %d, want 1", len(feedOut.Items))
	}
	item := feedOut.Items[0]
	if item.LikeCount != 1 || !item.LikedByMe || item.CommentCount != 1 {
		t.Errorf("feed post item counts mismatch: %+v", item)
	}

	// 12. User logs out: cookies cleared
	req = httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", nil)
	req.Header.Set("X-CSRF-Token", userCSRF.Value)
	req.AddCookie(userSession)
	req.AddCookie(userCSRF)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /auth/logout status %d: %s", rec.Code, rec.Body.String())
	}
	clearedSession, clearedCSRF := extractCookies(rec.Result())
	if clearedSession != nil && clearedSession.Value != "" {
		t.Errorf("session cookie not cleared: %s", clearedSession.Value)
	}
	if clearedCSRF != nil && clearedCSRF.Value != "" {
		t.Errorf("csrf cookie not cleared: %s", clearedCSRF.Value)
	}
	_ = cfg
}
