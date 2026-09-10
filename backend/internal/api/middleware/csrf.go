package middleware

import (
	"net/http"

	"backend/internal/config"
	"backend/internal/model"
)

func CSRF(cfg *config.Config) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.Method == http.MethodGet || r.Method == http.MethodHead || r.Method == http.MethodOptions {
				next.ServeHTTP(w, r)
				return
			}

			headerToken := r.Header.Get("X-CSRF-Token")
			cookie, err := r.Cookie(cfg.CSRFCookieName)
			cookieToken := ""
			if err == nil {
				cookieToken = cookie.Value
			}

			if headerToken == "" || cookieToken == "" || headerToken != cookieToken {
				writeError(w, model.NewAppError(model.ErrCSRFFailed, "CSRF 校验失败，请刷新页面重试", 403))
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}
