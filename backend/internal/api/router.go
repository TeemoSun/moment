package api

import (
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"backend/internal/api/middleware"
	v1 "backend/internal/api/v1"
	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/service"
	"github.com/go-chi/chi/v5"
)

func NewRouter(
	cfg *config.Config,
	repos *repository.Repositories,
	services *service.Services,
	rateLimiter *middleware.RateLimiter,
	submitMedia func(mediaID int, kind string),
) http.Handler {
	r := chi.NewRouter()

	// Global middlewares
	r.Use(middleware.Recover)
	r.Use(middleware.GZip)
	if cfg.CORSOrigins != "" {
		r.Use(corsMiddleware(cfg.CORSOrigins))
	}
	r.Use(middleware.MaxBytes(1 << 20)) // 1MB limit for JSON bodies

	handler := v1.NewApiHandler(cfg, services, rateLimiter, submitMedia)

	// Health check
	r.Get("/api/health", func(w http.ResponseWriter, r *http.Request) {
		v1.JSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	// API v1 routes
	r.Route("/api/v1", func(v1Router chi.Router) {
		// System
		v1Router.Get("/system/initialized", handler.CheckInitialized)
		v1Router.Post("/system/init", handler.InitSystem)

		// Auth
		v1Router.Get("/auth/rsa-public-key", handler.GetRSAPublicKey)
		v1Router.Post("/auth/register", handler.Register)
		v1Router.Post("/auth/login", handler.Login)

		// Public Avatars
		v1Router.Get("/avatars/default", handler.GetDefaultAvatar)
		v1Router.Get("/avatars/{user_id}", handler.GetUserAvatar)

		// Auth + CSRF for Logout and Refresh
		v1Router.Group(func(authGroup chi.Router) {
			authGroup.Use(middleware.Auth(cfg, repos))
			authGroup.Use(middleware.CSRF(cfg))
			authGroup.Post("/auth/logout", handler.Logout)
			authGroup.Post("/auth/refresh", handler.Refresh)
		})

		// Authenticated routes
		v1Router.Group(func(authGroup chi.Router) {
			authGroup.Use(middleware.Auth(cfg, repos))

			// Users (Read)
			authGroup.Get("/me", handler.GetMe)
			authGroup.Get("/users/{user_id}", handler.GetOtherUser)

			// Posts (Read)
			authGroup.Get("/feed", handler.GetFeed)
			authGroup.Get("/posts/{post_id}", handler.GetPostDetail)
			authGroup.Get("/users/{user_id}/posts", handler.GetUserPosts)

			// Comments (Read)
			authGroup.Get("/posts/{post_id}/comments", handler.ListComments)
			authGroup.Get("/comments/{comment_id}/media/{spec}", handler.GetCommentMedia)

			// Media (Read)
			authGroup.Get("/posts/{post_id}/media/{media_id}/{spec}", handler.GetPostMedia)

			// Friends (Read)
			authGroup.Get("/friends/requests", handler.ListFriendRequests)
			authGroup.Get("/friends", handler.ListFriends)
			authGroup.Get("/friends/bots", handler.ListBotsPublic)

			// Invites (Read)
			authGroup.Get("/invites", handler.ListInvites)

			// Mutating routes (Auth + CSRF)
			authGroup.Group(func(csrfGroup chi.Router) {
				csrfGroup.Use(middleware.CSRF(cfg))

				// Users
				csrfGroup.Patch("/me", handler.UpdateMe)
				csrfGroup.Post("/me/password", handler.ChangePassword)
				csrfGroup.Post("/me/avatar", handler.UploadAvatar)
				csrfGroup.Post("/me/deactivate", handler.Deactivate)

				// Posts
				csrfGroup.Post("/posts", handler.CreatePost)
				csrfGroup.Delete("/posts/{post_id}", handler.DeletePost)

				// Comments
				csrfGroup.Post("/posts/{post_id}/comments", handler.CreateComment)
				csrfGroup.Delete("/comments/{comment_id}", handler.DeleteComment)
				csrfGroup.Post("/comments/{comment_id}/likes", handler.LikeComment)
				csrfGroup.Delete("/comments/{comment_id}/likes", handler.UnlikeComment)
				csrfGroup.Post("/posts/{post_id}/likes", handler.LikePost)
				csrfGroup.Delete("/posts/{post_id}/likes", handler.UnlikePost)
				csrfGroup.Post("/comments/media", handler.UploadCommentImage)

				// Media
				csrfGroup.Post("/media/upload", handler.UploadMedia)

				// Friends
				csrfGroup.Post("/friends/request", handler.SendFriendRequest)
				csrfGroup.Post("/friends/requests/{request_id}/accept", handler.AcceptFriendRequest)
				csrfGroup.Post("/friends/requests/{request_id}/reject", handler.RejectFriendRequest)
				csrfGroup.Delete("/friends/{user_id}", handler.RemoveFriend)
				csrfGroup.Post("/friends/bots/{bot_user_id}", handler.AddBotFriend)

				// Invites
				csrfGroup.Post("/invites", handler.CreateInvite)
				csrfGroup.Post("/invites/renew", handler.RenewInvite)
				csrfGroup.Post("/invites/{invite_id}/revoke", handler.RevokeInvite)
			})

			// Admin routes (Auth + RequireAdmin)
			authGroup.Group(func(adminGroup chi.Router) {
				adminGroup.Use(middleware.RequireAdmin)

				// Admin Read
				adminGroup.Get("/admin/stats", handler.GetStats)
				adminGroup.Get("/admin/users", handler.ListUsers)
				adminGroup.Get("/admin/posts", handler.ListPosts)
				adminGroup.Get("/admin/comments", handler.ListCommentsAdmin)
				adminGroup.Get("/admin/invites", handler.ListInvitesAdmin)
				adminGroup.Get("/admin/llm-config", handler.GetLLMConfig)
				adminGroup.Get("/admin/bots", handler.ListBotsAdmin)

				// Admin Mutate (CSRF)
				adminGroup.Group(func(adminCsrf chi.Router) {
					adminCsrf.Use(middleware.CSRF(cfg))

					adminCsrf.Patch("/admin/users/{user_id}", handler.UpdateUser)
					adminCsrf.Delete("/admin/posts/{post_id}", handler.DeletePostAdmin)
					adminCsrf.Delete("/admin/comments/{comment_id}", handler.DeleteCommentAdmin)
					adminCsrf.Post("/admin/invites/{invite_id}/revoke", handler.RevokeInviteAdmin)
					adminCsrf.Put("/admin/llm-config", handler.UpdateLLMConfig)
					adminCsrf.Post("/admin/llm-config/test", handler.TestLLMConfig)

					// Bots Admin
					adminCsrf.Post("/admin/bots", handler.CreateBot)
					adminCsrf.Patch("/admin/bots/{bot_id}", handler.UpdateBot)
					adminCsrf.Delete("/admin/bots/{bot_id}", handler.DeleteBot)
					adminCsrf.Post("/admin/bots/{bot_id}/avatar", handler.UploadBotAvatar)
					adminCsrf.Post("/admin/bots/{bot_id}/trigger", handler.TriggerBot)
				})
			})
		})
	})

	// Static assets and SPA fallback
	setupSPAFallback(r, cfg.FrontendDist)

	return r
}

func corsMiddleware(origins string) func(http.Handler) http.Handler {
	allowed := make(map[string]bool)
	for _, o := range strings.Split(origins, ",") {
		o = strings.TrimSpace(o)
		if o != "" {
			allowed[o] = true
		}
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if origin != "" && (allowed["*"] || allowed[origin]) {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Credentials", "true")
				w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
				w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-CSRF-Token, Authorization")
			}

			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func setupSPAFallback(r chi.Router, frontendDist string) {
	distRoot := filepath.Clean(frontendDist)

	r.NotFound(func(w http.ResponseWriter, req *http.Request) {
		path := req.URL.Path

		// Never fallback API paths to SPA
		if strings.HasPrefix(path, "/api/") || path == "/api" {
			v1.Error(w, model.NewAppError(model.ErrNotFound, "资源不存在", http.StatusNotFound))
			return
		}

		cleanPath := filepath.Clean(strings.TrimPrefix(path, "/"))
		targetPath := filepath.Join(distRoot, cleanPath)

		// Security: prevent path traversal
		if !strings.HasPrefix(targetPath, distRoot) {
			v1.Error(w, model.NewAppError(model.ErrForbidden, "无权访问", http.StatusForbidden))
			return
		}

		// Check if exact file exists
		if fi, err := os.Stat(targetPath); err == nil && !fi.IsDir() {
			serveCompressedOrRaw(w, req, targetPath)
			return
		}

		// Serve index.html as fallback
		indexPath := filepath.Join(distRoot, "index.html")
		if _, err := os.Stat(indexPath); err == nil {
			http.ServeFile(w, req, indexPath)
			return
		}

		v1.Error(w, model.NewAppError(model.ErrNotFound, "页面不存在", http.StatusNotFound))
	})
}

func serveCompressedOrRaw(w http.ResponseWriter, r *http.Request, filePath string) {
	acceptEncoding := r.Header.Get("Accept-Encoding")

	// Try br
	if strings.Contains(acceptEncoding, "br") {
		brPath := filePath + ".br"
		if fi, err := os.Stat(brPath); err == nil && !fi.IsDir() {
			w.Header().Set("Content-Encoding", "br")
			w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
			w.Header().Set("Vary", "Accept-Encoding")
			w.Header().Set("Content-Type", guessContentType(filePath))
			http.ServeFile(w, r, brPath)
			return
		}
	}

	// Try gzip
	if strings.Contains(acceptEncoding, "gzip") {
		gzPath := filePath + ".gz"
		if fi, err := os.Stat(gzPath); err == nil && !fi.IsDir() {
			w.Header().Set("Content-Encoding", "gzip")
			w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
			w.Header().Set("Vary", "Accept-Encoding")
			w.Header().Set("Content-Type", guessContentType(filePath))
			http.ServeFile(w, r, gzPath)
			return
		}
	}

	http.ServeFile(w, r, filePath)
}

func guessContentType(p string) string {
	ext := filepath.Ext(p)
	ct := mime.TypeByExtension(ext)
	if ct == "" {
		return "application/octet-stream"
	}
	return ct
}
