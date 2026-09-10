package service

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type CommentService struct {
	cfg   *config.Config
	repos *repository.Repositories
}

func NewCommentService(cfg *config.Config, repos *repository.Repositories) *CommentService {
	return &CommentService{cfg: cfg, repos: repos}
}

func (s *CommentService) CreateComment(ctx context.Context, user *model.User, postID int, data model.CommentCreateIn) (*model.CommentOut, error) {
	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	// Visibility check
	canView, err := s.canViewPost(ctx, user.ID, post)
	if err != nil {
		return nil, err
	}
	if !canView {
		return nil, model.NewAppError(model.ErrForbidden, "无权评论此动态", 403)
	}

	var content *string
	if data.Content != nil {
		trimmed := strings.TrimSpace(*data.Content)
		if trimmed != "" {
			content = &trimmed
		}
	}

	if content == nil && data.MediaID == nil {
		return nil, model.NewAppError(model.ErrEmptyComment, "评论需包含文字或图片", 400)
	}

	var imagePath, imageThumbPath, imageLargePath *string
	if data.MediaID != nil {
		media, err := s.repos.Media.GetMediaByID(ctx, *data.MediaID)
		if err != nil {
			return nil, err
		}
		if media == nil || media.OwnerID == nil || *media.OwnerID != user.ID {
			return nil, model.NewAppError(model.ErrMediaNotOwned, "无权使用此媒体文件", 403)
		}
		if media.PostID != nil {
			return nil, model.NewAppError(model.ErrMediaAlreadyUsed, "此媒体文件已被使用", 400)
		}
		if media.Kind != "image" {
			return nil, model.NewAppError(model.ErrUnsupportedMedia, "评论仅支持图片", 400)
		}

		imagePath = &media.FilePath
		imageThumbPath = media.ThumbPath
		imageLargePath = media.LargePath
		_ = s.repos.Media.DeleteMedia(ctx, media.ID)
	}

	parentCommentID := data.ParentCommentID
	replyToUserID := data.ReplyToUserID

	var parent *model.Comment
	if parentCommentID != nil {
		parent, err = s.repos.Comment.GetByID(ctx, *parentCommentID)
		if err != nil {
			return nil, err
		}
		if parent == nil || parent.PostID != postID {
			return nil, model.NewAppError(model.ErrCommentNotFound, "父评论不存在", 404)
		}
		if replyToUserID == nil {
			replyToUserID = &parent.UserID
		}
	}

	if replyToUserID != nil {
		replyToUser, err := s.repos.User.GetByID(ctx, *replyToUserID)
		if err != nil {
			return nil, err
		}
		if replyToUser == nil {
			return nil, model.NewAppError(model.ErrNotFound, "被回复用户不存在", 404)
		}
	}

	comment := &model.Comment{
		PostID:          postID,
		UserID:          user.ID,
		ParentCommentID: parentCommentID,
		ReplyToUserID:   replyToUserID,
		Content:         content,
		ImagePath:       imagePath,
		ImageThumbPath:  imageThumbPath,
		ImageLargePath:  imageLargePath,
	}

	if err := s.repos.Comment.Create(ctx, comment); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "发表评论失败", 500)
	}

	// Build response CommentOut
	cAuthorOut := s.buildCommentAuthorOut(user)

	var replyToOut *model.ReplyToOut
	if replyToUserID != nil {
		rtUser, _ := s.repos.User.GetByID(ctx, *replyToUserID)
		replyToOut = s.buildReplyToOut(rtUser)
	}

	var replyPreview *string
	if parent != nil && parent.Content != nil {
		lines := strings.Split(*parent.Content, "\n")
		firstLine := lines[0]
		runes := []rune(firstLine)
		if len(runes) > 10 {
			prev := string(runes[:10]) + "..."
			replyPreview = &prev
		} else {
			replyPreview = &firstLine
		}
	}

	var thumbURL, largeURL *string
	if imageThumbPath != nil {
		u := fmt.Sprintf("/api/v1/comments/%d/media/thumb", comment.ID)
		thumbURL = &u
	}
	if imageLargePath != nil {
		u := fmt.Sprintf("/api/v1/comments/%d/media/large", comment.ID)
		largeURL = &u
	}

	canDelete := comment.UserID == user.ID || post.UserID == user.ID || user.Role == "admin"

	return &model.CommentOut{
		ID:                  comment.ID,
		PostID:              comment.PostID,
		Author:              cAuthorOut,
		ParentCommentID:     comment.ParentCommentID,
		ReplyTo:             replyToOut,
		ReplyContentPreview: replyPreview,
		Content:             comment.Content,
		ImageThumbURL:       thumbURL,
		ImageLargeURL:       largeURL,
		LikeCount:           0,
		LikedByMe:           false,
		IsOwner:             true,
		CanDelete:           canDelete,
		CreatedAt:           comment.CreatedAt,
	}, nil
}

func (s *CommentService) DeleteComment(ctx context.Context, user *model.User, commentID int) error {
	comment, err := s.repos.Comment.GetByID(ctx, commentID)
	if err != nil {
		return err
	}
	if comment == nil {
		return model.NewAppError(model.ErrCommentNotFound, "评论不存在", 404)
	}

	post, err := s.repos.Post.GetByIDIncludeDeleted(ctx, comment.PostID)
	if err != nil {
		return err
	}
	if post == nil {
		return model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canDelete := comment.UserID == user.ID || post.UserID == user.ID || user.Role == "admin"
	if !canDelete {
		return model.NewAppError(model.ErrForbidden, "无权删除此评论", 403)
	}

	return s.repos.Comment.SoftDelete(ctx, commentID)
}

func (s *CommentService) ListComments(ctx context.Context, viewerID, postID, page, pageSize int) (*model.CommentListOut, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	} else if pageSize > 100 {
		pageSize = 100
	}

	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canView, err := s.canViewPost(ctx, viewerID, post)
	if err != nil {
		return nil, err
	}
	if !canView {
		return nil, model.NewAppError(model.ErrForbidden, "无权查看此动态", 403)
	}

	var allowedUserIDs []int
	if post.Visibility == "friends" {
		friendIDs, err := s.repos.Friend.GetFriendIDs(ctx, viewerID)
		if err != nil {
			return nil, err
		}
		idMap := make(map[int]bool)
		idMap[viewerID] = true
		idMap[post.UserID] = true
		for _, fid := range friendIDs {
			idMap[fid] = true
		}
		for uid := range idMap {
			allowedUserIDs = append(allowedUserIDs, uid)
		}
	}

	offset := (page - 1) * pageSize
	comments, total, err := s.repos.Comment.ListByPost(ctx, postID, allowedUserIDs, offset, pageSize)
	if err != nil {
		return nil, err
	}

	// Batch preload authors, reply_to, likes, parent comments
	authorIDSet := make(map[int]bool)
	var commentIDs []int
	var parentIDs []int
	for _, c := range comments {
		commentIDs = append(commentIDs, c.ID)
		authorIDSet[c.UserID] = true
		if c.ReplyToUserID != nil {
			authorIDSet[*c.ReplyToUserID] = true
		}
		if c.ParentCommentID != nil {
			parentIDs = append(parentIDs, *c.ParentCommentID)
		}
	}

	parentComments, _ := s.repos.Comment.BatchPreloadParents(ctx, parentIDs)
	likeCounts, _ := s.repos.Comment.BatchPreloadLikeCounts(ctx, commentIDs)
	likedByMe, _ := s.repos.Comment.BatchPreloadLikedByMe(ctx, commentIDs, viewerID)

	var allUserIDs []int
	for uid := range authorIDSet {
		allUserIDs = append(allUserIDs, uid)
	}
	usersMap, _ := s.repos.User.GetByIDs(ctx, allUserIDs)

	viewer := usersMap[viewerID]
	isAdmin := viewer != nil && viewer.Role == "admin"

	var items []model.CommentOut
	for _, c := range comments {
		author := usersMap[c.UserID]
		authorOut := s.buildCommentAuthorOut(author)

		var replyToOut *model.ReplyToOut
		if c.ReplyToUserID != nil {
			rtUser := usersMap[*c.ReplyToUserID]
			replyToOut = s.buildReplyToOut(rtUser)
		}

		var replyPreview *string
		if c.ParentCommentID != nil {
			if parent, ok := parentComments[*c.ParentCommentID]; ok && parent.Content != nil {
				lines := strings.Split(*parent.Content, "\n")
				firstLine := lines[0]
				runes := []rune(firstLine)
				if len(runes) > 10 {
					prev := string(runes[:10]) + "..."
					replyPreview = &prev
				} else {
					replyPreview = &firstLine
				}
			}
		}

		var thumbURL, largeURL *string
		if c.ImageThumbPath != nil {
			u := fmt.Sprintf("/api/v1/comments/%d/media/thumb", c.ID)
			thumbURL = &u
		}
		if c.ImageLargePath != nil {
			u := fmt.Sprintf("/api/v1/comments/%d/media/large", c.ID)
			largeURL = &u
		}

		canDelete := c.UserID == viewerID || post.UserID == viewerID || isAdmin

		items = append(items, model.CommentOut{
			ID:                  c.ID,
			PostID:              c.PostID,
			Author:              authorOut,
			ParentCommentID:     c.ParentCommentID,
			ReplyTo:             replyToOut,
			ReplyContentPreview: replyPreview,
			Content:             c.Content,
			ImageThumbURL:       thumbURL,
			ImageLargeURL:       largeURL,
			LikeCount:           likeCounts[c.ID],
			LikedByMe:           likedByMe[c.ID],
			IsOwner:             c.UserID == viewerID,
			CanDelete:           canDelete,
			CreatedAt:           c.CreatedAt,
		})
	}
	if items == nil {
		items = []model.CommentOut{}
	}

	hasMore := offset+pageSize < total

	return &model.CommentListOut{
		Items:    items,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		HasMore:  hasMore,
	}, nil
}

func (s *CommentService) UploadCommentImage(ctx context.Context, user *model.User, originalName string, content []byte) (*model.CommentMediaOut, error) {
	maxBytes := s.cfg.MediaImageMaxMB * 1024 * 1024
	if len(content) > maxBytes {
		return nil, model.NewAppError(model.ErrFileTooLarge, "文件过大", 413)
	}

	kind, ext, mime, err := util.DetectKind(content)
	if err != nil || kind != "image" {
		return nil, model.NewAppError(model.ErrUnsupportedMedia, "评论仅支持图片", 400)
	}

	mediaDir, err := util.GetMediaDir(s.cfg.StorageRoot)
	if err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建媒体目录失败", 500)
	}

	filename := util.GenerateFilename(ext)
	origAbs, finalName, err := util.SafeSaveBytes(mediaDir, filename, content)
	if err != nil {
		return nil, model.NewAppError(model.ErrInternal, "保存图片失败", 500)
	}
	origRel, _ := filepath.Rel(s.cfg.StorageRoot, origAbs)

	stem := strings.TrimSuffix(finalName, filepath.Ext(finalName))
	thumbName := fmt.Sprintf("%s_thumb.webp", stem)
	largeName := fmt.Sprintf("%s_large.webp", stem)
	thumbAbs := filepath.Join(mediaDir, thumbName)
	largeAbs := filepath.Join(mediaDir, largeName)

	// Generate thumb (400px) and large (2160px) via ffmpeg
	cmdThumb := exec.Command("ffmpeg", "-y", "-i", origAbs,
		"-vf", fmt.Sprintf("scale='min(%d,iw)':-2", s.cfg.ThumbSize),
		"-quality", fmt.Sprintf("%d", s.cfg.WebpThumbQuality),
		thumbAbs)
	_ = cmdThumb.Run()

	cmdLarge := exec.Command("ffmpeg", "-y", "-i", origAbs,
		"-vf", fmt.Sprintf("scale='min(%d,iw)':-2", s.cfg.LargeSize),
		"-quality", fmt.Sprintf("%d", s.cfg.WebpLargeQuality),
		largeAbs)
	_ = cmdLarge.Run()

	thumbRel, _ := filepath.Rel(s.cfg.StorageRoot, thumbAbs)
	largeRel, _ := filepath.Rel(s.cfg.StorageRoot, largeAbs)

	media := &model.PostMedia{
		PostID:    nil,
		OwnerID:   &user.ID,
		FilePath:  origRel,
		ThumbPath: &thumbRel,
		LargePath: &largeRel,
		Filename:  finalName,
		Size:      len(content),
		Mime:      mime,
		Format:    ext,
		Kind:      "image",
		SortOrder: 0,
	}

	if err := s.repos.Media.CreateMedia(ctx, media); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "保存媒体记录失败", 500)
	}

	// Insert file_metadata records
	_ = s.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
		StoragePath:  origRel,
		OriginalName: originalName,
		Filename:     finalName,
		Size:         len(content),
		Mime:         mime,
		Format:       ext,
		Kind:         "image",
		OwnerID:      &user.ID,
	})
	if fi, err := os.Stat(thumbAbs); err == nil {
		_ = s.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
			StoragePath:  thumbRel,
			OriginalName: originalName,
			Filename:     thumbName,
			Size:         int(fi.Size()),
			Mime:         "image/webp",
			Format:       "webp",
			Kind:         "thumb",
			OwnerID:      &user.ID,
		})
	}
	if fi, err := os.Stat(largeAbs); err == nil {
		_ = s.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
			StoragePath:  largeRel,
			OriginalName: originalName,
			Filename:     largeName,
			Size:         int(fi.Size()),
			Mime:         "image/webp",
			Format:       "webp",
			Kind:         "large",
			OwnerID:      &user.ID,
		})
	}

	return &model.CommentMediaOut{
		MediaID:       media.ID,
		ImageThumbURL: nil,
		ImageLargeURL: nil,
		Status:        "ready",
	}, nil
}

func (s *CommentService) GetCommentImage(ctx context.Context, viewerID, commentID int, spec string) (string, string, error) {
	if spec != "thumb" && spec != "large" {
		return "", "", model.NewAppError(model.ErrValidationError, "规格参数无效", 400)
	}

	comment, err := s.repos.Comment.GetByID(ctx, commentID)
	if err != nil {
		return "", "", err
	}
	if comment == nil {
		return "", "", model.NewAppError(model.ErrCommentNotFound, "评论不存在", 404)
	}

	post, err := s.repos.Post.GetByID(ctx, comment.PostID)
	if err != nil {
		return "", "", err
	}
	if post == nil {
		return "", "", model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canView, err := s.canViewPost(ctx, viewerID, post)
	if err != nil {
		return "", "", err
	}
	if !canView {
		return "", "", model.NewAppError(model.ErrForbidden, "无权查看此媒体", 403)
	}

	var rel *string
	if spec == "thumb" {
		rel = comment.ImageThumbPath
	} else {
		rel = comment.ImageLargePath
	}

	if rel == nil || *rel == "" {
		return "", "", model.NewAppError(model.ErrMediaNotReady, "媒体尚未就绪", 404)
	}

	absPath, ok := util.ResolveWithinStorage(s.cfg.StorageRoot, *rel)
	if !ok {
		return "", "", model.NewAppError(model.ErrNotFound, "文件不存在", 404)
	}

	return absPath, "image/webp", nil
}

func (s *CommentService) canViewPost(ctx context.Context, viewerID int, post *model.Post) (bool, error) {
	if post.DeletedAt != nil {
		return false, nil
	}
	if post.Visibility == "public" {
		return true, nil
	}
	if viewerID == post.UserID {
		return true, nil
	}
	return s.repos.Friend.AreFriends(ctx, viewerID, post.UserID)
}

func (s *CommentService) buildCommentAuthorOut(u *model.User) model.CommentAuthorOut {
	if u == nil {
		return model.CommentAuthorOut{
			ID:            0,
			Nickname:      "未知",
			AvatarURL:     "/api/v1/avatars/default",
			IsDeactivated: false,
		}
	}
	if u.Status == "deactivated" {
		return model.CommentAuthorOut{
			ID:            u.ID,
			Nickname:      "已注销",
			AvatarURL:     "/api/v1/avatars/default",
			IsDeactivated: true,
		}
	}
	avatarURL := "/api/v1/avatars/default"
	if u.AvatarPath != nil && *u.AvatarPath != "" {
		avatarURL = fmt.Sprintf("/api/v1/avatars/%d", u.ID)
	}
	return model.CommentAuthorOut{
		ID:            u.ID,
		Nickname:      u.Nickname,
		AvatarURL:     avatarURL,
		IsDeactivated: false,
	}
}

func (s *CommentService) buildReplyToOut(u *model.User) *model.ReplyToOut {
	if u == nil {
		return nil
	}
	if u.Status == "deactivated" {
		return &model.ReplyToOut{
			ID:            u.ID,
			Nickname:      "已注销",
			IsDeactivated: true,
		}
	}
	return &model.ReplyToOut{
		ID:            u.ID,
		Nickname:      u.Nickname,
		IsDeactivated: false,
	}
}
