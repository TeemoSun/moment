package v1

import (
	"net/http"

	"backend/internal/api/middleware"
	"backend/internal/model"
	"github.com/go-chi/chi/v5"
)

func (h *ApiHandler) UploadMedia(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	maxMB := h.cfg.MediaImageMaxMB
	if h.cfg.MediaVideoMaxMB > maxMB {
		maxMB = h.cfg.MediaVideoMaxMB
	}
	if err := r.ParseMultipartForm(int64(maxMB) * 1024 * 1024); err != nil {
		Error(w, model.NewAppError(model.ErrValidationError, "解析上传表单失败", http.StatusBadRequest))
		return
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		Error(w, model.NewAppError(model.ErrValidationError, "未提供文件", http.StatusBadRequest))
		return
	}
	defer file.Close()

	out, err := h.services.Media.UploadMedia(r.Context(), currentUser, header.Filename, file)
	if err != nil {
		Error(w, err)
		return
	}

	if h.submitMedia != nil {
		h.submitMedia(out.MediaID, out.Kind)
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) GetPostMedia(w http.ResponseWriter, r *http.Request) {
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

	mediaID, err := ParseIntParam(r, "media_id")
	if err != nil {
		Error(w, err)
		return
	}

	spec := chi.URLParam(r, "spec")
	path, contentType, err := h.services.Media.GetMediaFile(r.Context(), &currentUser.ID, postID, mediaID, spec)
	if err != nil {
		Error(w, err)
		return
	}

	w.Header().Set("Cache-Control", "private, max-age=3600")
	w.Header().Set("Content-Type", contentType)
	http.ServeFile(w, r, path)
}
