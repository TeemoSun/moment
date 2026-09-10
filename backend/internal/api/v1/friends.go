package v1

import (
	"net/http"
	"strings"

	"backend/internal/api/middleware"
	"backend/internal/model"
)

func (h *ApiHandler) SendFriendRequest(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	var req model.FriendRequestIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	req.Email = strings.TrimSpace(req.Email)
	if req.Email == "" {
		Error(w, model.NewAppError(model.ErrValidationError, "请填写好友邮箱", http.StatusBadRequest))
		return
	}

	out, err := h.services.Friend.RequestFriend(r.Context(), currentUser, req.Email)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) ListFriendRequests(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	out, err := h.services.Friend.ListRequests(r.Context(), currentUser)
	if err != nil {
		Error(w, err)
		return
	}
	if out == nil {
		out = []model.FriendRequestOut{}
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) AcceptFriendRequest(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	reqID, err := ParseIntParam(r, "request_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Friend.AcceptRequest(r.Context(), currentUser, reqID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) RejectFriendRequest(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	reqID, err := ParseIntParam(r, "request_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Friend.RejectRequest(r.Context(), currentUser, reqID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) ListFriends(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	out, err := h.services.Friend.ListFriends(r.Context(), currentUser)
	if err != nil {
		Error(w, err)
		return
	}
	if out == nil {
		out = []model.FriendOut{}
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) RemoveFriend(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	targetID, err := ParseIntParam(r, "user_id")
	if err != nil {
		Error(w, err)
		return
	}

	if err := h.services.Friend.RemoveFriend(r.Context(), currentUser, targetID); err != nil {
		Error(w, err)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) ListBotsPublic(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	out, err := h.services.Bot.ListBotsPublic(r.Context(), currentUser)
	if err != nil {
		Error(w, err)
		return
	}
	if out == nil {
		out = []model.BotPublicOut{}
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) AddBotFriend(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	botUserID, err := ParseIntParam(r, "bot_user_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Bot.AddBotFriend(r.Context(), currentUser, botUserID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}
