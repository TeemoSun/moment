package v1

import (
	"net/http"
	"strings"

	"backend/internal/model"
)

func (h *ApiHandler) CheckInitialized(w http.ResponseWriter, r *http.Request) {
	initialized, err := h.services.System.IsInitialized(r.Context())
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, model.InitializedOut{
		Initialized:            initialized,
		AllowInsecureClipboard: h.cfg.AllowInsecureClipboard,
		AppName:                h.cfg.AppName,
	})
}

func (h *ApiHandler) InitSystem(w http.ResponseWriter, r *http.Request) {
	var req model.InitIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	req.Email = strings.TrimSpace(req.Email)
	req.Nickname = strings.TrimSpace(req.Nickname)
	if req.Email == "" || req.Nickname == "" || req.Password == "" {
		Error(w, model.NewAppError(model.ErrValidationError, "请填写所有必填字段", http.StatusBadRequest))
		return
	}

	user, token, csrfToken, err := h.services.System.InitSystem(r.Context(), req)
	if err != nil {
		Error(w, err)
		return
	}

	SetAuthCookies(w, h.cfg, token, csrfToken)
	JSON(w, http.StatusOK, model.TokenOut{
		User: h.services.User.UserToMeOut(user),
	})
}
