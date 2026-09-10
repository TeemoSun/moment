package service

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type UserService struct {
	cfg   *config.Config
	repos *repository.Repositories
}

func NewUserService(cfg *config.Config, repos *repository.Repositories) *UserService {
	return &UserService{cfg: cfg, repos: repos}
}

func (s *UserService) AvatarURLFor(user *model.User) string {
	if user != nil && user.AvatarPath != nil && *user.AvatarPath != "" {
		return fmt.Sprintf("/api/v1/avatars/%d", user.ID)
	}
	return "/api/v1/avatars/default"
}

func (s *UserService) UserToMeOut(user *model.User) model.MeOut {
	return model.MeOut{
		ID:        user.ID,
		Email:     user.Email,
		Nickname:  user.Nickname,
		Signature: user.Signature,
		AvatarURL: s.AvatarURLFor(user),
		Role:      user.Role,
		Status:    user.Status,
		CanInvite: user.CanInvite,
		CreatedAt: user.CreatedAt,
	}
}

func (s *UserService) GetMe(ctx context.Context, user *model.User) (model.MeOut, error) {
	// Re-fetch to get fresh data
	fresh, err := s.repos.User.GetByID(ctx, user.ID)
	if err != nil {
		return model.MeOut{}, err
	}
	if fresh != nil {
		user = fresh
	}
	return s.UserToMeOut(user), nil
}

func (s *UserService) UpdateMe(ctx context.Context, user *model.User, data model.MeUpdateIn) (*model.User, error) {
	if err := s.repos.User.UpdateProfile(ctx, user.ID, data.Nickname, data.Signature); err != nil {
		return nil, err
	}
	fresh, err := s.repos.User.GetByID(ctx, user.ID)
	if err != nil {
		return nil, err
	}
	return fresh, nil
}

func (s *UserService) ChangePassword(ctx context.Context, user *model.User, data model.PasswordChangeIn) error {
	rsaKey, err := s.repos.RSA.GetFirst(ctx)
	if err != nil || rsaKey == nil {
		return model.NewAppError(model.ErrInternal, "RSA密钥未就绪", 500)
	}

	plainOld, err := util.RSADecrypt(rsaKey.PrivateKeyPEM, data.OldPassword)
	if err != nil {
		return model.NewAppError(model.ErrRSADecryptFailed, "旧密码解密失败", 400)
	}

	plainNew, err := util.RSADecrypt(rsaKey.PrivateKeyPEM, data.NewPassword)
	if err != nil {
		return model.NewAppError(model.ErrRSADecryptFailed, "新密码解密失败", 400)
	}

	if !util.VerifyPassword(plainOld, user.PasswordHash) {
		return model.NewAppError(model.ErrInvalidCredentials, "旧密码错误", 401)
	}

	pwErrors := util.ValidatePassword(plainNew)
	if len(pwErrors) > 0 {
		return model.NewAppError(model.ErrPasswordTooWeak, "新密码强度不足", 400, map[string]any{"errors": pwErrors})
	}

	newHash, err := util.HashPassword(plainNew)
	if err != nil {
		return model.NewAppError(model.ErrInternal, "新密码哈希失败", 500)
	}

	return s.repos.User.UpdatePasswordAndBumpToken(ctx, user.ID, newHash)
}

func (s *UserService) UploadAvatar(ctx context.Context, user *model.User, originalName string, content []byte) (*model.User, error) {
	maxBytes := s.cfg.MediaImageMaxMB * 1024 * 1024
	if len(content) > maxBytes {
		return nil, model.NewAppError(model.ErrFileTooLarge, "文件过大", 413)
	}

	kind, _, _, err := util.DetectKind(content)
	if err != nil || kind != "image" {
		return nil, model.NewAppError(model.ErrUnsupportedMedia, "不是有效的图片文件", 400)
	}

	avatarsDir, err := util.GetAvatarsDir(s.cfg.StorageRoot)
	if err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建头像目录失败", 500)
	}

	// Temporary file to run ffmpeg
	tmpFile, err := os.CreateTemp(avatarsDir, "avatar_upload_*.tmp")
	if err != nil {
		return nil, err
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.Write(content); err != nil {
		tmpFile.Close()
		return nil, err
	}
	tmpFile.Close()

	// Convert avatar to WebP thumbnail (max 400px)
	filename := util.GenerateFilename("webp")
	avatarAbsPath := filepath.Join(avatarsDir, filename)

	cmd := exec.Command("ffmpeg", "-y", "-i", tmpFile.Name(),
		"-vf", fmt.Sprintf("scale='min(%d,iw)':-2", s.cfg.ThumbSize),
		"-quality", fmt.Sprintf("%d", s.cfg.WebpThumbQuality),
		avatarAbsPath)
	if out, err := cmd.CombinedOutput(); err != nil {
		// If ffmpeg fails, fallback to direct save
		_ = out
		if err := os.WriteFile(avatarAbsPath, content, 0644); err != nil {
			return nil, model.NewAppError(model.ErrInternal, "保存头像文件失败", 500)
		}
	}

	relPath, err := filepath.Rel(s.cfg.StorageRoot, avatarAbsPath)
	if err != nil {
		relPath = filepath.Join("avatars", filename)
	}

	if err := s.repos.User.UpdateAvatar(ctx, user.ID, relPath); err != nil {
		return nil, err
	}

	fi, _ := os.Stat(avatarAbsPath)
	fileSize := int(fi.Size())

	_ = s.repos.Media.CreateFileMetadata(ctx, &model.FileMetadata{
		StoragePath:  relPath,
		OriginalName: originalName,
		Filename:     filename,
		Size:         fileSize,
		Mime:         "image/webp",
		Format:       "webp",
		Kind:         "avatar",
		OwnerID:      &user.ID,
	})

	user.AvatarPath = &relPath
	return user, nil
}

func (s *UserService) Deactivate(ctx context.Context, user *model.User) error {
	return s.repos.User.Deactivate(ctx, user.ID)
}

func (s *UserService) GetOtherUser(ctx context.Context, viewerID, targetUserID int) (*model.OtherUserOut, error) {
	target, err := s.repos.User.GetByID(ctx, targetUserID)
	if err != nil {
		return nil, err
	}
	if target == nil {
		return nil, model.NewAppError(model.ErrUserNotFound, "用户不存在", 404)
	}

	friendshipStatus := "none"
	if viewerID == targetUserID {
		friendshipStatus = "self"
	} else {
		areFriends, err := s.repos.Friend.AreFriends(ctx, viewerID, targetUserID)
		if err != nil {
			return nil, err
		}
		if areFriends {
			friendshipStatus = "friends"
		} else {
			f, err := s.repos.Friend.GetFriendship(ctx, viewerID, targetUserID)
			if err != nil {
				return nil, err
			}
			if f != nil && f.Status == "pending" {
				if f.RequesterID == viewerID {
					friendshipStatus = "pending_sent"
				} else {
					friendshipStatus = "pending_received"
				}
			}
		}
	}

	isDeactivated := target.Status == "deactivated"
	nickname := target.Nickname
	avatarURL := s.AvatarURLFor(target)
	if isDeactivated {
		nickname = "已注销"
		avatarURL = "/api/v1/avatars/default"
	}

	var isBot bool
	var personaBrief *string
	if target.Role == "bot" {
		bot, _ := s.repos.Bot.GetByUserID(ctx, target.ID)
		if bot != nil {
			isBot = true
			runes := []rune(bot.Persona)
			brief := string(runes)
			if len(runes) > 80 {
				brief = string(runes[:80])
			}
			personaBrief = &brief
		}
	}

	return &model.OtherUserOut{
		ID:               target.ID,
		Nickname:         nickname,
		Signature:        target.Signature,
		AvatarURL:        avatarURL,
		IsDeactivated:    isDeactivated,
		CreatedAt:        target.CreatedAt,
		FriendshipStatus: friendshipStatus,
		IsBot:            isBot,
		PersonaBrief:     personaBrief,
	}, nil
}
