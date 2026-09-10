package service

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type MediaService struct {
	cfg   *config.Config
	repos *repository.Repositories
}

func NewMediaService(cfg *config.Config, repos *repository.Repositories) *MediaService {
	return &MediaService{cfg: cfg, repos: repos}
}

func (s *MediaService) UploadMedia(ctx context.Context, user *model.User, originalName string, r io.Reader) (*model.MediaUploadOut, error) {
	if originalName == "" {
		return nil, model.NewAppError(model.ErrValidationError, "未提供文件", 400)
	}

	maxAnyMB := s.cfg.MediaImageMaxMB
	if s.cfg.MediaVideoMaxMB > maxAnyMB {
		maxAnyMB = s.cfg.MediaVideoMaxMB
	}
	maxAnyBytes := int64(maxAnyMB) * 1024 * 1024

	mediaDir, err := util.GetMediaDir(s.cfg.StorageRoot)
	if err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建媒体目录失败", 500)
	}

	// Stream to temp file
	tmpFile, err := os.CreateTemp(mediaDir, "upload_*.tmp")
	if err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建临时文件失败", 500)
	}
	tmpPath := tmpFile.Name()
	_ = tmpFile.Close()

	total, err := util.StreamToFile(r, tmpPath, maxAnyBytes, s.cfg.StorageRoot)
	if err != nil {
		_ = os.Remove(tmpPath)
		if errors.Is(err, errors.New("file too large")) {
			return nil, model.NewAppError(model.ErrFileTooLarge, "文件过大", 413)
		}
		return nil, model.NewAppError(model.ErrValidationError, "读取上传文件失败", 400)
	}

	// Read header to detect kind
	f, err := os.Open(tmpPath)
	if err != nil {
		_ = os.Remove(tmpPath)
		return nil, model.NewAppError(model.ErrInternal, "打开临时文件失败", 500)
	}
	header := make([]byte, 261)
	n, _ := f.Read(header)
	_ = f.Close()

	kind, ext, mime, err := util.DetectKind(header[:n])
	if err != nil {
		_ = os.Remove(tmpPath)
		return nil, model.NewAppError(model.ErrUnsupportedMedia, "不支持的文件类型", 400)
	}

	// Check kind size
	if kind == "image" {
		if total > int64(s.cfg.MediaImageMaxMB)*1024*1024 {
			_ = os.Remove(tmpPath)
			return nil, model.NewAppError(model.ErrFileTooLarge, "文件过大", 413)
		}
	} else if kind == "video" {
		if total > int64(s.cfg.MediaVideoMaxMB)*1024*1024 {
			_ = os.Remove(tmpPath)
			return nil, model.NewAppError(model.ErrFileTooLarge, "文件过大", 413)
		}
	}

	finalFilename := util.GenerateFilename(ext)
	finalAbsPath := filepath.Join(mediaDir, finalFilename)
	if err := os.Rename(tmpPath, finalAbsPath); err != nil {
		_ = os.Remove(tmpPath)
		return nil, model.NewAppError(model.ErrInternal, "保存媒体文件失败", 500)
	}

	relPath, err := filepath.Rel(s.cfg.StorageRoot, finalAbsPath)
	if err != nil {
		relPath = filepath.Join("media", filepath.Base(mediaDir), finalFilename)
	}

	media := &model.PostMedia{
		PostID:    nil,
		OwnerID:   &user.ID,
		FilePath:  relPath,
		Filename:  finalFilename,
		Size:      int(total),
		Mime:      mime,
		Format:    ext,
		Kind:      kind,
		SortOrder: 0,
	}

	if err := s.repos.Media.CreateMedia(ctx, media); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "记录媒体失败", 500)
	}

	_ = s.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
		StoragePath:  relPath,
		OriginalName: originalName,
		Filename:     finalFilename,
		Size:         int(total),
		Mime:         mime,
		Format:       ext,
		Kind:         kind,
		OwnerID:      &user.ID,
	})

	return &model.MediaUploadOut{
		MediaID:   media.ID,
		Kind:      media.Kind,
		Format:    media.Format,
		Size:      media.Size,
		Status:    "pending",
		CreatedAt: media.CreatedAt,
	}, nil
}

func (s *MediaService) GetMediaFile(ctx context.Context, viewerID *int, postID, mediaID int, spec string) (string, string, error) {
	if spec != "thumb" && spec != "large" && spec != "original" {
		return "", "", model.NewAppError(model.ErrValidationError, "规格参数无效", 400)
	}

	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return "", "", err
	}
	if post == nil {
		return "", "", model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canView := false
	if post.Visibility == "public" {
		canView = true
	} else if viewerID != nil {
		if *viewerID == post.UserID {
			canView = true
		} else {
			areFriends, _ := s.repos.Friend.AreFriends(ctx, *viewerID, post.UserID)
			canView = areFriends
		}
	}
	if !canView {
		return "", "", model.NewAppError(model.ErrForbidden, "无权查看此媒体", 403)
	}

	media, err := s.repos.Media.GetPostMedia(ctx, postID, mediaID)
	if err != nil {
		return "", "", err
	}
	if media == nil {
		return "", "", model.NewAppError(model.ErrNotFound, "媒体不存在", 404)
	}

	var relPath *string
	mime := media.Mime

	switch spec {
	case "original":
		relPath = &media.FilePath
	case "thumb":
		relPath = media.ThumbPath
		mime = "image/webp"
	case "large":
		relPath = media.LargePath
		mime = "image/webp"
	}

	if relPath == nil || *relPath == "" {
		return "", "", model.NewAppError(model.ErrMediaNotReady, "媒体尚未就绪", 404)
	}

	absPath, ok := util.ResolveWithinStorage(s.cfg.StorageRoot, *relPath)
	if !ok {
		return "", "", model.NewAppError(model.ErrNotFound, "文件不存在", 404)
	}

	return absPath, mime, nil
}
