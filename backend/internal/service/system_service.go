package service

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"strings"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type SystemService struct {
	cfg   *config.Config
	repos *repository.Repositories
}

func NewSystemService(cfg *config.Config, repos *repository.Repositories) *SystemService {
	return &SystemService{cfg: cfg, repos: repos}
}

func (s *SystemService) IsInitialized(ctx context.Context) (bool, error) {
	status, err := s.repos.System.GetStatus(ctx)
	if err != nil {
		return false, err
	}
	if status == nil {
		return false, nil
	}
	return status.Initialized, nil
}

func (s *SystemService) InitSystem(ctx context.Context, data model.InitIn) (*model.User, string, string, error) {
	status, err := s.repos.System.GetStatus(ctx)
	if err != nil {
		return nil, "", "", err
	}
	if status != nil && status.Initialized {
		return nil, "", "", model.NewAppError(model.ErrAlreadyInitialized, "系统已初始化", 409)
	}

	rsaKey, err := s.repos.RSA.GetFirst(ctx)
	if err != nil || rsaKey == nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "RSA密钥未就绪", 500)
	}

	plainPassword, err := util.RSADecrypt(rsaKey.PrivateKeyPEM, data.Password)
	if err != nil {
		return nil, "", "", model.NewAppError(model.ErrRSADecryptFailed, "密码解密失败", 400)
	}

	pwErrors := util.ValidatePassword(plainPassword)
	if len(pwErrors) > 0 {
		return nil, "", "", model.NewAppError(model.ErrPasswordTooWeak, "密码强度不足", 400, map[string]any{"errors": pwErrors})
	}

	pwHash, err := util.HashPassword(plainPassword)
	if err != nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "密码哈希失败", 500)
	}

	email := strings.ToLower(strings.TrimSpace(data.Email))
	user := &model.User{
		Email:        email,
		PasswordHash: pwHash,
		Nickname:     data.Nickname,
		Role:         "admin",
		Status:       "active",
		CanInvite:    true,
	}

	if err := s.repos.User.Create(ctx, user); err != nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "创建管理员失败", 500)
	}

	if err := s.repos.System.SetInitialized(ctx, user.ID); err != nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "更新系统状态失败", 500)
	}

	token, err := util.CreateAccessToken(s.cfg.JWTSecret, user.ID, user.Role, user.TokenVersion, s.cfg.JWTExpireDays)
	if err != nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "生成认证凭证失败", 500)
	}

	csrfBytes := make([]byte, 32)
	_, _ = rand.Read(csrfBytes)
	csrfToken := base64.RawURLEncoding.EncodeToString(csrfBytes)

	return user, token, csrfToken, nil
}
