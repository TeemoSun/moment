package v1

import (
	"net/http"

	"backend/internal/api/middleware"
	"backend/internal/model"
)

func (h *ApiHandler) CreateInvite(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	var req model.InviteCreateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Invite.CreateInvite(r.Context(), currentUser, req.DurationDays)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) ListInvites(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	out, err := h.services.Invite.ListInvites(r.Context(), currentUser)
	if err != nil {
		Error(w, err)
		return
	}
	if out == nil {
		out = []model.InviteOut{}
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) RenewInvite(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	var req model.InviteCreateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Invite.RenewInvite(r.Context(), currentUser, req.DurationDays)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) RevokeInvite(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	inviteID, err := ParseIntParam(r, "invite_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Invite.RevokeInvite(r.Context(), currentUser, inviteID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}
