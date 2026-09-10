package tests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"backend/internal/model"
)

func createTestUser(t *testing.T, router http.Handler, rsaPubKey string, adminSession, adminCSRF *http.Cookie, email, nickname string) (*http.Cookie, *http.Cookie, int) {
	// 1. Admin generates invite
	durationDays := 7
	inviteBody, _ := json.Marshal(model.InviteCreateIn{
		DurationDays: &durationDays,
	})
	req := httptest.NewRequest(http.MethodPost, "/api/v1/invites", bytes.NewReader(inviteBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", adminCSRF.Value)
	req.AddCookie(adminSession)
	req.AddCookie(adminCSRF)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("Failed to create invite: %s", rec.Body.String())
	}
	var inv model.InviteOut
	_ = json.Unmarshal(rec.Body.Bytes(), &inv)

	// 2. User registers
	userPW := "UserPass123!"
	regBody, _ := json.Marshal(model.RegisterIn{
		Email:      email,
		Nickname:   nickname,
		Password:   encryptWithPubKey(t, rsaPubKey, userPW),
		InviteCode: inv.Code,
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewReader(regBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("Failed to register %s: %s", email, rec.Body.String())
	}

	var tokenOut model.TokenOut
	_ = json.Unmarshal(rec.Body.Bytes(), &tokenOut)

	session, csrf := extractCookies(rec.Result())
	return session, csrf, tokenOut.User.ID
}

func makeFriends(t *testing.T, router http.Handler, sessionA, csrfA, sessionB, csrfB *http.Cookie, emailB string) {
	// User A sends friend request to User B's email
	reqBody, _ := json.Marshal(model.FriendRequestIn{Email: emailB})
	req := httptest.NewRequest(http.MethodPost, "/api/v1/friends/request", bytes.NewReader(reqBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", csrfA.Value)
	req.AddCookie(sessionA)
	req.AddCookie(csrfA)
	rec := httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("Friend request failed: %s", rec.Body.String())
	}

	// User B lists requests to get request ID
	req = httptest.NewRequest(http.MethodGet, "/api/v1/friends/requests", nil)
	req.AddCookie(sessionB)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("List friend requests failed: %s", rec.Body.String())
	}

	var requests []model.FriendRequestOut
	_ = json.Unmarshal(rec.Body.Bytes(), &requests)
	if len(requests) == 0 {
		t.Fatalf("No friend requests received by User B")
	}

	requestID := requests[0].ID

	// User B accepts request
	req = httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/v1/friends/requests/%d/accept", requestID), nil)
	req.Header.Set("X-CSRF-Token", csrfB.Value)
	req.AddCookie(sessionB)
	req.AddCookie(csrfB)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("Accept friend request failed: %s", rec.Body.String())
	}
}

func TestVisibility_PostAndComment(t *testing.T) {
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
		Email:    "admin@vis.local",
		Nickname: "Admin",
		Password: encryptWithPubKey(t, rsaOut.PublicKey, adminPW),
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/system/init", bytes.NewReader(initBody))
	req.Header.Set("Content-Type", "application/json")
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	adminSession, adminCSRF := extractCookies(rec.Result())

	// 3. Create User 1 (Author), User 2 (Friend of Author), User 3 (Friend of Author, but NOT friend of User 2)
	s1, c1, _ := createTestUser(t, router, rsaOut.PublicKey, adminSession, adminCSRF, "author@test.local", "Author")
	s2, c2, _ := createTestUser(t, router, rsaOut.PublicKey, adminSession, adminCSRF, "user2@test.local", "User2")
	s3, _, _ := createTestUser(t, router, rsaOut.PublicKey, adminSession, adminCSRF, "user3@test.local", "User3")

	// Author is friends with User 2
	makeFriends(t, router, s1, c1, s2, c2, "user2@test.local")
	// Author is friends with User 3
	makeFriends(t, router, s1, c1, s3, c1, "user3@test.local")
	// NOTE: User 2 and User 3 are NOT friends!

	// 4. Author posts a "friends" visibility post
	postBody, _ := json.Marshal(model.PostCreateIn{
		Content:    "Post for friends only!",
		Visibility: "friends",
		MediaIDs:   []int{},
	})
	req = httptest.NewRequest(http.MethodPost, "/api/v1/posts", bytes.NewReader(postBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", c1.Value)
	req.AddCookie(s1)
	req.AddCookie(c1)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("Author post creation failed: %s", rec.Body.String())
	}
	var postOut model.PostOut
	_ = json.Unmarshal(rec.Body.Bytes(), &postOut)

	// 5. User 2 comments on Author's post
	cText := "User 2 comment"
	commentBody, _ := json.Marshal(model.CommentCreateIn{
		Content: &cText,
	})
	req = httptest.NewRequest(http.MethodPost, fmt.Sprintf("/api/v1/posts/%d/comments", postOut.ID), bytes.NewReader(commentBody))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CSRF-Token", c2.Value)
	req.AddCookie(s2)
	req.AddCookie(c2)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("User 2 comment creation failed: %s", rec.Body.String())
	}

	// 6. Author views comments -> can see User 2's comment (Author sees all)
	req = httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/v1/posts/%d/comments", postOut.ID), nil)
	req.AddCookie(s1)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	var commentList model.CommentListOut
	_ = json.Unmarshal(rec.Body.Bytes(), &commentList)
	if len(commentList.Items) != 1 {
		t.Errorf("Author should see 1 comment, got %d", len(commentList.Items))
	}

	// 7. User 2 views comments -> can see own comment
	req = httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/v1/posts/%d/comments", postOut.ID), nil)
	req.AddCookie(s2)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	_ = json.Unmarshal(rec.Body.Bytes(), &commentList)
	if len(commentList.Items) != 1 {
		t.Errorf("User 2 should see their own comment, got %d", len(commentList.Items))
	}

	// 8. User 3 views comments -> CANNOT see User 2's comment because User 3 is NOT friends with User 2! (WeChat Moments rule)
	req = httptest.NewRequest(http.MethodGet, fmt.Sprintf("/api/v1/posts/%d/comments", postOut.ID), nil)
	req.AddCookie(s3)
	rec = httptest.NewRecorder()
	router.ServeHTTP(rec, req)
	_ = json.Unmarshal(rec.Body.Bytes(), &commentList)
	if len(commentList.Items) != 0 {
		t.Errorf("User 3 should NOT see User 2's comment (not mutual friends), got %d comments", len(commentList.Items))
	}
}
