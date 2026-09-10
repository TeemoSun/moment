package middleware

import (
	"context"
	"encoding/json"
	"net/http"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type contextKey string

const (
	UserContextKey contextKey = "current_user"
)

func UserFromContext(ctx context.Context) *model.User {
	if u, ok := ctx.Value(UserContextKey).(*model.User); ok {
		return u
	}
	return nil
}

func Auth(cfg *config.Config, repos *repository.Repositories) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			cookie, err := r.Cookie(cfg.CookieName)
			if err != nil || cookie.Value == "" {
				writeError(w, model.NewAppError(model.ErrAuthRequired, "需要登录", 401))
				return
			}

			uid, _, ver, err := util.DecodeAccessToken(cfg.JWTSecret, cookie.Value)
			if err != nil {
				writeError(w, model.NewAppError(model.ErrAuthRequired, "登录凭证无效，请重新登录", 401))
				return
			}

			user, err := repos.User.GetByID(r.Context(), uid)
			if err != nil || user == nil {
				writeError(w, model.NewAppError(model.ErrAuthRequired, "用户不存在", 401))
				return
			}

			if user.TokenVersion != ver {
				writeError(w, model.NewAppError(model.ErrAuthRequired, "登录凭证已失效，请重新登录", 401))
				return
			}

			if user.Role == "bot" {
				writeError(w, model.NewAppError(model.ErrAuthRequired, "机器人账号无法访问", 401))
				return
			}

			if user.Status == "deactivated" {
				writeError(w, model.NewAppError(model.ErrAccountDeactivated, "账号已注销", 401))
				return
			}

			if user.Status == "disabled" {
				writeError(w, model.NewAppError(model.ErrAccountDisabled, "账号已被禁用", 403))
				return
			}

			ctx := context.WithValue(r.Context(), UserContextKey, user)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func RequireAdmin(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user := UserFromContext(r.Context())
		if user == nil || user.Role != "admin" {
			writeError(w, model.NewAppError(model.ErrAdminRequired, "需要管理员权限", 403))
			return
		}
		next.ServeHTTP(w, r)
	})
}

func writeError(w http.ResponseWriter, appErr *model.AppError) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(appErr.StatusCode)
	_ = json.NewEncoder(w).Encode(appErr.ToResponse())
}
