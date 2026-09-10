package v1

import (
	"io"
	"net/http"

	"backend/internal/api/middleware"
	"backend/internal/model"
	"github.com/go-chi/chi/v5"
)

func (h *ApiHandler) ListComments(w http.ResponseWriter, r *http.Request) {
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

	out, err := h.services.Comment.ListComments(r.Context(), currentUser.ID, postID, page, pageSize)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) CreateComment(w http.ResponseWriter, r *http.Request) {
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

	var req model.CommentCreateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Comment.CreateComment(r.Context(), currentUser, postID, req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusCreated, out)
}

func (h *ApiHandler) DeleteComment(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	commentID, err := ParseIntParam(r, "comment_id")
	if err != nil {
		Error(w, err)
		return
	}

	if err := h.services.Comment.DeleteComment(r.Context(), currentUser, commentID); err != nil {
		Error(w, err)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) LikeComment(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	commentID, err := ParseIntParam(r, "comment_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Like.ToggleCommentLike(r.Context(), currentUser, commentID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) UnlikeComment(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	commentID, err := ParseIntParam(r, "comment_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Like.UnlikeComment(r.Context(), currentUser, commentID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) LikePost(w http.ResponseWriter, r *http.Request) {
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

	out, err := h.services.Like.TogglePostLike(r.Context(), currentUser, postID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) UnlikePost(w http.ResponseWriter, r *http.Request) {
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

	out, err := h.services.Like.UnlikePost(r.Context(), currentUser, postID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) UploadCommentImage(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	if err := r.ParseMultipartForm(32 << 20); err != nil {
		Error(w, model.NewAppError(model.ErrValidationError, "解析上传表单失败", http.StatusBadRequest))
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		Error(w, model.NewAppError(model.ErrValidationError, "未提供文件", http.StatusBadRequest))
		return
	}
	defer file.Close()

	maxBytes := int64(h.cfg.MediaImageMaxMB) * 1024 * 1024
	content, err := io.ReadAll(io.LimitReader(file, maxBytes+1))
	if err != nil {
		Error(w, model.NewAppError(model.ErrValidationError, "读取文件失败", http.StatusBadRequest))
		return
	}
	if int64(len(content)) > maxBytes {
		Error(w, model.NewAppError(model.ErrFileTooLarge, "文件过大", http.StatusRequestEntityTooLarge))
		return
	}

	out, err := h.services.Comment.UploadCommentImage(r.Context(), currentUser, header.Filename, content)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) GetCommentMedia(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	commentID, err := ParseIntParam(r, "comment_id")
	if err != nil {
		Error(w, err)
		return
	}

	spec := chi.URLParam(r, "spec")
	path, contentType, err := h.services.Comment.GetCommentImage(r.Context(), currentUser.ID, commentID, spec)
	if err != nil {
		Error(w, err)
		return
	}

	w.Header().Set("Cache-Control", "private, max-age=3600")
	w.Header().Set("Content-Type", contentType)
	http.ServeFile(w, r, path)
}
