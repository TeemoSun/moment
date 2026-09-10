package v1

import (
	"io"
	"net/http"

	"backend/internal/model"
)

func (h *ApiHandler) ListBotsAdmin(w http.ResponseWriter, r *http.Request) {
	out, err := h.services.Bot.ListBotsAdmin(r.Context())
	if err != nil {
		Error(w, err)
		return
	}
	if out == nil {
		out = []model.BotAdminOut{}
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) CreateBot(w http.ResponseWriter, r *http.Request) {
	var req model.BotCreateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Bot.CreateBot(r.Context(), req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusCreated, out)
}

func (h *ApiHandler) UpdateBot(w http.ResponseWriter, r *http.Request) {
	botID, err := ParseIntParam(r, "bot_id")
	if err != nil {
		Error(w, err)
		return
	}

	var req model.BotUpdateIn
	if err := ReadJSON(r, &req); err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Bot.UpdateBot(r.Context(), botID, req)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) DeleteBot(w http.ResponseWriter, r *http.Request) {
	botID, err := ParseIntParam(r, "bot_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Bot.DeleteBot(r.Context(), botID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) UploadBotAvatar(w http.ResponseWriter, r *http.Request) {
	botID, err := ParseIntParam(r, "bot_id")
	if err != nil {
		Error(w, err)
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

	out, err := h.services.Bot.UploadBotAvatar(r.Context(), botID, header.Filename, content)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}

func (h *ApiHandler) TriggerBot(w http.ResponseWriter, r *http.Request) {
	botID, err := ParseIntParam(r, "bot_id")
	if err != nil {
		Error(w, err)
		return
	}

	out, err := h.services.Bot.TriggerBot(r.Context(), botID)
	if err != nil {
		Error(w, err)
		return
	}

	JSON(w, http.StatusOK, out)
}
