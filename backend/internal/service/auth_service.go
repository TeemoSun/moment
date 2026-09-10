package service

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"strings"
	"time"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type AuthService struct {
	cfg   *config.Config
	repos *repository.Repositories
}

func NewAuthService(cfg *config.Config, repos *repository.Repositories) *AuthService {
	return &AuthService{cfg: cfg, repos: repos}
}

func (s *AuthService) GetRSAPublicKey(ctx context.Context) (string, error) {
	key, err := s.repos.RSA.GetFirst(ctx)
	if err != nil {
		return "", err
	}
	if key != nil {
		return key.PublicKeyPEM, nil
	}

	pubPEM, privPEM, err := util.GenerateRSAKeyPair()
	if err != nil {
		return "", fmt.Errorf("failed to generate RSA key: %w", err)
	}

	key, err = s.repos.RSA.Create(ctx, pubPEM, privPEM)
	if err != nil {
		return "", err
	}
	return key.PublicKeyPEM, nil
}

func (s *AuthService) Register(ctx context.Context, data model.RegisterIn) (*model.User, string, string, error) {
	email := strings.ToLower(strings.TrimSpace(data.Email))

	existing, err := s.repos.User.GetByEmail(ctx, email)
	if err != nil {
		return nil, "", "", err
	}
	if existing != nil {
		return nil, "", "", model.NewAppError(model.ErrEmailExists, "该邮箱已注册", 409)
	}

	invite, err := s.repos.Invite.GetByCode(ctx, strings.TrimSpace(data.InviteCode))
	if err != nil {
		return nil, "", "", err
	}
	if invite == nil || invite.Status != "active" || invite.UsedByID != nil {
		return nil, "", "", model.NewAppError(model.ErrInvalidInvite, "邀请码无效", 400)
	}
	if invite.ExpiresAt != nil && invite.ExpiresAt.Before(time.Now().UTC()) {
		return nil, "", "", model.NewAppError(model.ErrInvalidInvite, "邀请码无效", 400)
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

	user := &model.User{
		Email:        email,
		PasswordHash: pwHash,
		Nickname:     data.Nickname,
		Role:         "user",
		Status:       "active",
		CanInvite:    true,
	}

	if err := s.repos.User.Create(ctx, user); err != nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "注册失败", 500)
	}

	_ = s.repos.Invite.MarkUsed(ctx, invite.ID, user.ID)

	token, err := util.CreateAccessToken(s.cfg.JWTSecret, user.ID, user.Role, user.TokenVersion, s.cfg.JWTExpireDays)
	if err != nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "生成认证凭证失败", 500)
	}

	csrfBytes := make([]byte, 32)
	_, _ = rand.Read(csrfBytes)
	csrfToken := base64.RawURLEncoding.EncodeToString(csrfBytes)

	return user, token, csrfToken, nil
}

func (s *AuthService) Login(ctx context.Context, data model.LoginIn) (*model.User, string, string, error) {
	email := strings.ToLower(strings.TrimSpace(data.Email))

	user, err := s.repos.User.GetByEmail(ctx, email)
	if err != nil {
		return nil, "", "", err
	}
	if user == nil {
		return nil, "", "", model.NewAppError(model.ErrInvalidCredentials, "邮箱或密码错误", 401)
	}

	if user.Role == "bot" {
		return nil, "", "", model.NewAppError(model.ErrBotLoginForbidden, "机器人账号无法登录", 403)
	}

	if user.Status == "disabled" {
		return nil, "", "", model.NewAppError(model.ErrAccountDisabled, "账号已被禁用", 403)
	}

	if user.Status == "deactivated" {
		return nil, "", "", model.NewAppError(model.ErrAccountDeactivated, "账号已注销", 403)
	}

	now := time.Now().UTC()
	if user.LockedUntil != nil && user.LockedUntil.After(now) {
		retryAfter := int(user.LockedUntil.Sub(now).Seconds())
		return nil, "", "", model.NewAppError(model.ErrAccountLocked, "账号已锁定", 403, map[string]any{
			"locked_until":        user.LockedUntil.Format(time.RFC3339),
			"retry_after_seconds": retryAfter,
		})
	}

	rsaKey, err := s.repos.RSA.GetFirst(ctx)
	if err != nil || rsaKey == nil {
		return nil, "", "", model.NewAppError(model.ErrInternal, "RSA密钥未就绪", 500)
	}

	plainPassword, err := util.RSADecrypt(rsaKey.PrivateKeyPEM, data.Password)
	if err != nil {
		s.recordFailedAttempt(ctx, user)
		return nil, "", "", model.NewAppError(model.ErrInvalidCredentials, "邮箱或密码错误", 401)
	}

	if !util.VerifyPassword(plainPassword, user.PasswordHash) {
		if lockErr := s.recordFailedAttempt(ctx, user); lockErr != nil {
			return nil, "", "", lockErr
		}
		return nil, "", "", model.NewAppError(model.ErrInvalidCredentials, "邮箱或密码错误", 401)
	}

	if err := s.repos.User.RecordLoginSuccess(ctx, user.ID); err != nil {
		return nil, "", "", err
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

func (s *AuthService) recordFailedAttempt(ctx context.Context, user *model.User) error {
	count, lockedUntil, err := s.repos.User.RecordLoginFailure(ctx, user.ID)
	if err != nil {
		return nil
	}
	if count >= 5 && lockedUntil != nil {
		return model.NewAppError(model.ErrAccountLocked, "账号已锁定", 403, map[string]any{
			"locked_until":        lockedUntil.Format(time.RFC3339),
			"retry_after_seconds": 900,
		})
	}
	return nil
}

func (s *AuthService) Refresh(ctx context.Context, user *model.User) (string, string, error) {
	token, err := util.CreateAccessToken(s.cfg.JWTSecret, user.ID, user.Role, user.TokenVersion, s.cfg.JWTExpireDays)
	if err != nil {
		return "", "", model.NewAppError(model.ErrInternal, "生成认证凭证失败", 500)
	}

	csrfBytes := make([]byte, 32)
	_, _ = rand.Read(csrfBytes)
	csrfToken := base64.RawURLEncoding.EncodeToString(csrfBytes)

	return token, csrfToken, nil
}
