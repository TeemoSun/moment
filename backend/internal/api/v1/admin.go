package v1

import (
	"net/http"
	"strconv"

	"backend/internal/model"
)

func (h *ApiHandler) GetStats(w http.ResponseWriter, r *http.Request) {
	out, err := h.services.Admin.GetStats(r.Context())
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) ListUsers(w http.ResponseWriter, r *http.Request) {
	search := r.URL.Query().Get("search")
	page := ParseIntQuery(r, "page", 1)
	if page < 1 {
		page = 1
	}
	pageSize := ParseIntQuery(r, "page_size", 20)
	if pageSize < 1 {
		pageSize = 1
	} else if pageSize > 100 {
		pageSize = 100
	}

	out, err := h.services.Admin.ListUsers(r.Context(), page, pageSize, search)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) UpdateUser(w http.ResponseWriter, r *http.Request) {
	userID, err := ParseIntParam(r, "user_id")
	if err != nil {
		Error(w, err)
		return
	}

	var req model.AdminUserUpdateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Admin.UpdateUser(r.Context(), userID, req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) ListPosts(w http.ResponseWriter, r *http.Request) {
	var userID *int
	if uStr := r.URL.Query().Get("user_id"); uStr != "" {
		if uid, err := strconv.Atoi(uStr); err == nil {
			userID = &uid
		}
	}

	var visibility *string
	if vStr := r.URL.Query().Get("visibility"); vStr != "" {
		visibility = &vStr
	}

	page := ParseIntQuery(r, "page", 1)
	if page < 1 {
		page = 1
	}
	pageSize := ParseIntQuery(r, "page_size", 20)
	if pageSize < 1 {
		pageSize = 1
	} else if pageSize > 100 {
		pageSize = 100
	}

	out, err := h.services.Admin.ListPosts(r.Context(), page, pageSize, userID, visibility)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) DeletePostAdmin(w http.ResponseWriter, r *http.Request) {
	postID, err := ParseIntParam(r, "post_id")
	if err != nil {
		Error(w, err)
		return
	}

	if err := h.services.Admin.DeletePost(r.Context(), postID); err != nil {
		Error(w, err)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) ListCommentsAdmin(w http.ResponseWriter, r *http.Request) {
	page := ParseIntQuery(r, "page", 1)
	if page < 1 {
		page = 1
	}
	pageSize := ParseIntQuery(r, "page_size", 20)
	if pageSize < 1 {
		pageSize = 1
	} else if pageSize > 100 {
		pageSize = 100
	}

	out, err := h.services.Admin.ListComments(r.Context(), page, pageSize)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) DeleteCommentAdmin(w http.ResponseWriter, r *http.Request) {
	commentID, err := ParseIntParam(r, "comment_id")
	if err != nil {
		Error(w, err)
		return
	}

	if err := h.services.Admin.DeleteComment(r.Context(), commentID); err != nil {
		Error(w, err)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) ListInvitesAdmin(w http.ResponseWriter, r *http.Request) {
	page := ParseIntQuery(r, "page", 1)
	if page < 1 {
		page = 1
	}
	pageSize := ParseIntQuery(r, "page_size", 20)
	if pageSize < 1 {
		pageSize = 1
	} else if pageSize > 100 {
		pageSize = 100
	}

	out, err := h.services.Admin.ListInvites(r.Context(), page, pageSize)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) RevokeInviteAdmin(w http.ResponseWriter, r *http.Request) {
	inviteID, err := ParseIntParam(r, "invite_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Admin.RevokeInvite(r.Context(), inviteID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) GetLLMConfig(w http.ResponseWriter, r *http.Request) {
	out, err := h.services.Admin.GetLLMConfig(r.Context())
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) UpdateLLMConfig(w http.ResponseWriter, r *http.Request) {
	var req model.LLMConfigUpdateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Admin.UpdateLLMConfig(r.Context(), req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) TestLLMConfig(w http.ResponseWriter, r *http.Request) {
	var req model.LLMConfigTestIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Admin.TestLLMConfig(r.Context(), req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}
