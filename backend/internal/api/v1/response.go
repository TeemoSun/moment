package v1

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"backend/internal/config"
	"backend/internal/model"
	"github.com/go-chi/chi/v5"
)

func JSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	if data != nil {
		_ = json.NewEncoder(w).Encode(data)
	}
}

func Error(w http.ResponseWriter, err error) {
	if err == nil {
		return
	}
	if appErr, ok := err.(*model.AppError); ok {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.WriteHeader(appErr.StatusCode)
		_ = json.NewEncoder(w).Encode(appErr.ToResponse())
		return
	}

	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(http.StatusInternalServerError)
	_ = json.NewEncoder(w).Encode(model.NewAppError(model.ErrInternal, "服务器内部错误", 500).ToResponse())
}

func ReadJSON(r *http.Request, dest any) error {
	defer r.Body.Close()
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(dest); err != nil {
		return model.NewAppError(model.ErrValidationError, "请求参数校验失败", http.StatusBadRequest, map[string]any{"errors": err.Error()})
	}
	return nil
}

func SetAuthCookies(w http.ResponseWriter, cfg *config.Config, token, csrfToken string) {
	secure := cfg.SecureCookies || strings.HasPrefix(strings.ToLower(cfg.PublicBaseURL), "https")
	maxAge := cfg.JWTExpireDays * 86400

	http.SetCookie(w, &http.Cookie{
		Name:     cfg.CookieName,
		Value:    token,
		Path:     "/",
		MaxAge:   maxAge,
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})

	http.SetCookie(w, &http.Cookie{
		Name:     cfg.CSRFCookieName,
		Value:    csrfToken,
		Path:     "/",
		MaxAge:   maxAge,
		HttpOnly: false,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
}

func ClearAuthCookies(w http.ResponseWriter, cfg *config.Config) {
	secure := cfg.SecureCookies || strings.HasPrefix(strings.ToLower(cfg.PublicBaseURL), "https")

	http.SetCookie(w, &http.Cookie{
		Name:     cfg.CookieName,
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})

	http.SetCookie(w, &http.Cookie{
		Name:     cfg.CSRFCookieName,
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: false,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
}

func ParseIntParam(r *http.Request, key string) (int, error) {
	raw := chi.URLParam(r, key)
	val, err := strconv.Atoi(raw)
	if err != nil {
		return 0, model.NewAppError(model.ErrValidationError, "无效的ID参数: "+key, http.StatusBadRequest)
	}
	return val, nil
}

func ParseIntQuery(r *http.Request, key string, defaultVal int) int {
	raw := r.URL.Query().Get(key)
	if raw == "" {
		return defaultVal
	}
	val, err := strconv.Atoi(raw)
	if err != nil {
		return defaultVal
	}
	return val
}

func QueryStringPtr(r *http.Request, key string) *string {
	raw := strings.TrimSpace(r.URL.Query().Get(key))
	if raw == "" {
		return nil
	}
	return &raw
}
