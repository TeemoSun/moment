package v1

import (
	"net/http"
	"strings"

	"backend/internal/api/middleware"
	"backend/internal/model"
)

func (h *ApiHandler) GetRSAPublicKey(w http.ResponseWriter, r *http.Request) {
	pubPEM, err := h.services.Auth.GetRSAPublicKey(r.Context())
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, model.RSAKeyOut{
		PublicKey: pubPEM,
	})
}

func (h *ApiHandler) Register(w http.ResponseWriter, r *http.Request) {
	clientIP := middleware.GetClientIP(r)
	if err := h.rateLimiter.Hit("register", clientIP, 5, 3600); err != nil {
		Error(w, err)
		return
	}

	var req model.RegisterIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	req.Email = strings.TrimSpace(req.Email)
	req.Nickname = strings.TrimSpace(req.Nickname)
	req.InviteCode = strings.TrimSpace(req.InviteCode)
	if req.Email == "" || req.Nickname == "" || req.Password == "" || req.InviteCode == "" {
		Error(w, model.NewAppError(model.ErrValidationError, "请填写所有必填字段", http.StatusBadRequest))
		return
	}

	user, token, csrfToken, err := h.services.Auth.Register(r.Context(), req)
	if err != nil {
		Error(w, err)
		return
	}

	SetAuthCookies(w, h.cfg, token, csrfToken)
	JSON(w, http.StatusOK, model.TokenOut{
		User: h.services.User.UserToMeOut(user),
	})
}

func (h *ApiHandler) Login(w http.ResponseWriter, r *http.Request) {
	clientIP := middleware.GetClientIP(r)
	if err := h.rateLimiter.Hit("login", clientIP, 10, 300); err != nil {
		Error(w, err)
		return
	}

	var req model.LoginIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	req.Email = strings.TrimSpace(req.Email)
	if req.Email == "" || req.Password == "" {
		Error(w, model.NewAppError(model.ErrValidationError, "请填写邮箱和密码", http.StatusBadRequest))
		return
	}

	user, token, csrfToken, err := h.services.Auth.Login(r.Context(), req)
	if err != nil {
		Error(w, err)
		return
	}

	SetAuthCookies(w, h.cfg, token, csrfToken)
	JSON(w, http.StatusOK, model.TokenOut{
		User: h.services.User.UserToMeOut(user),
	})
}

func (h *ApiHandler) Logout(w http.ResponseWriter, r *http.Request) {
	ClearAuthCookies(w, h.cfg)
	JSON(w, http.StatusOK, map[string]string{"message": "已登出"})
}

func (h *ApiHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	token, csrfToken, err := h.services.Auth.Refresh(r.Context(), currentUser)
	if err != nil {
		Error(w, err)
		return
	}

	SetAuthCookies(w, h.cfg, token, csrfToken)
	JSON(w, http.StatusOK, model.TokenOut{
		User: h.services.User.UserToMeOut(currentUser),
	})
}
