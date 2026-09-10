package v1

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"backend/internal/api/middleware"
	"backend/internal/model"
)

func (h *ApiHandler) GetMe(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	me, err := h.services.User.GetMe(r.Context(), currentUser)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, me)
}

func (h *ApiHandler) UpdateMe(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	var req model.MeUpdateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	user, err := h.services.User.UpdateMe(r.Context(), currentUser, req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, h.services.User.UserToMeOut(user))
}

func (h *ApiHandler) ChangePassword(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	var req model.PasswordChangeIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	if err := h.services.User.ChangePassword(r.Context(), currentUser, req); err != nil {
		Error(w, err)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) UploadAvatar(w http.ResponseWriter, r *http.Request) {
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

	user, err := h.services.User.UploadAvatar(r.Context(), currentUser, header.Filename, content)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, model.AvatarOut{
		AvatarURL: h.services.User.AvatarURLFor(user),
	})
}

func (h *ApiHandler) Deactivate(w http.ResponseWriter, r *http.Request) {
	currentUser := middleware.UserFromContext(r.Context())
	if currentUser == nil {
		Error(w, model.NewAppError(model.ErrAuthRequired, "需要登录", http.StatusUnauthorized))
		return
	}

	if err := h.services.User.Deactivate(r.Context(), currentUser); err != nil {
		Error(w, err)
		return
	}

	ClearAuthCookies(w, h.cfg)
	w.WriteHeader(http.StatusNoContent)
}

func (h *ApiHandler) GetOtherUser(w http.ResponseWriter, r *http.Request) {
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

	out, err := h.services.User.GetOtherUser(r.Context(), currentUser.ID, targetID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) GetDefaultAvatar(w http.ResponseWriter, r *http.Request) {
	defaultPath := filepath.Join(h.cfg.ProjectRoot, "assets", "default_avatar.png")
	w.Header().Set("Content-Type", "image/png")
	http.ServeFile(w, r, defaultPath)
}

func (h *ApiHandler) GetUserAvatar(w http.ResponseWriter, r *http.Request) {
	userID, err := ParseIntParam(r, "user_id")
	if err != nil {
		h.GetDefaultAvatar(w, r)
		return
	}

	user, err := h.services.Repos.User.GetByID(r.Context(), userID)
	if err != nil || user == nil || user.AvatarPath == nil || *user.AvatarPath == "" {
		h.GetDefaultAvatar(w, r)
		return
	}

	storageRoot := filepath.Clean(h.cfg.StorageRoot)
	fileAbs := filepath.Clean(filepath.Join(storageRoot, *user.AvatarPath))

	if !strings.HasPrefix(fileAbs, storageRoot+string(filepath.Separator)) && fileAbs != storageRoot {
		h.GetDefaultAvatar(w, r)
		return
	}

	if fi, err := os.Stat(fileAbs); err != nil || fi.IsDir() {
		h.GetDefaultAvatar(w, r)
		return
	}

	w.Header().Set("Content-Type", "image/webp")
	http.ServeFile(w, r, fileAbs)
}
