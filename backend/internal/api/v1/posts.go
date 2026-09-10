package v1

import (
	"net/http"

	"backend/internal/api/middleware"
	"backend/internal/model"
)

func (h *ApiHandler) CreatePost(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	var req model.PostCreateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Post.CreatePost(r.Context(), currentUser, req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusCreated, out)
}

func (h *ApiHandler) GetFeed(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	cursor := QueryStringPtr(r, "cursor")
	limit := ParseIntQuery(r, "limit", 10)
	if limit < 1 {
		limit = 1
	} else if limit > 50 {
		limit = 50
	}

	out, err := h.services.Post.GetFeed(r.Context(), currentUser.ID, cursor, limit)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) GetPostDetail(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	postID, err := ParseIntParam(r, "post_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Post.GetPost(r.Context(), currentUser.ID, postID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) DeletePost(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	postID, err := ParseIntParam(r, "post_id")
	if err != nil {
		Error(w, err)
		return
	}

	if err := h.services.Post.DeletePost(r.Context(), currentUser, postID); err != nil {
		Error(w, err)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) GetUserPosts(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	userID, err := ParseIntParam(r, "user_id")
	if err != nil {
		Error(w, err)
		return
	}

	cursor := QueryStringPtr(r, "cursor")
	limit := ParseIntQuery(r, "limit", 10)
	if limit < 1 {
		limit = 1
	} else if limit > 50 {
		limit = 50
	}

	out, err := h.services.Post.GetUserPosts(r.Context(), currentUser.ID, userID, cursor, limit)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}
