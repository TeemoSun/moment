package service

import (
	"context"
	"crypto/rand"
	"math/big"
	"time"

	"backend/internal/model"
	"backend/internal/repository"
)

const inviteAlphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

type InviteService struct {
	repos *repository.Repositories
}

func NewInviteService(repos *repository.Repositories) *InviteService {
	return &InviteService{repos: repos}
}

func (s *InviteService) generateCode(ctx context.Context) (string, error) {
	for i := 0; i < 20; i++ {
		b := make([]byte, 8)
		for j := range b {
			idx, _ := rand.Int(rand.Reader, big.NewInt(int64(len(inviteAlphabet))))
			b[j] = inviteAlphabet[idx.Int64()]
		}
		code := string(b)
		existing, err := s.repos.Invite.GetByCode(ctx, code)
		if err != nil {
			return "", err
		}
		if existing == nil {
			return code, nil
		}
	}
	return "", model.NewAppError(model.ErrInternal, "生成唯一邀请码失败，请重试", 500)
}

func (s *InviteService) CreateInvite(ctx context.Context, user *model.User, durationDays *int) (*model.InviteOut, error) {
	if !user.CanInvite {
		return nil, model.NewAppError(model.ErrInviteDisabled, "邀请权限已被关闭", 403)
	}

	_ = s.repos.Invite.SyncExpired(ctx, user.ID)

	active, err := s.repos.Invite.GetActiveByCreator(ctx, user.ID)
	if err != nil {
		return nil, err
	}
	if active != nil {
		return nil, model.NewAppError(model.ErrActiveInviteExists, "已有有效邀请码，请先失效或续期", 400)
	}

	code, err := s.generateCode(ctx)
	if err != nil {
		return nil, err
	}

	var expiresAt *time.Time
	if durationDays != nil {
		t := time.Now().UTC().Add(time.Duration(*durationDays) * 24 * time.Hour)
		expiresAt = &t
	}

	inv := &model.InviteCode{
		Code:      code,
		CreatorID: user.ID,
		Status:    "active",
		ExpiresAt: expiresAt,
	}

	if err := s.repos.Invite.Create(ctx, inv); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建邀请码失败", 500)
	}

	return &model.InviteOut{
		ID:        inv.ID,
		Code:      inv.Code,
		Status:    inv.Status,
		ExpiresAt: inv.ExpiresAt,
		CreatedAt: inv.CreatedAt,
		UsedByID:  inv.UsedByID,
	}, nil
}

func (s *InviteService) ListInvites(ctx context.Context, user *model.User) ([]model.InviteOut, error) {
	_ = s.repos.Invite.SyncExpired(ctx, user.ID)

	invites, err := s.repos.Invite.ListByCreator(ctx, user.ID)
	if err != nil {
		return nil, err
	}

	var result []model.InviteOut
	for _, inv := range invites {
		result = append(result, model.InviteOut{
			ID:        inv.ID,
			Code:      inv.Code,
			Status:    inv.Status,
			ExpiresAt: inv.ExpiresAt,
			CreatedAt: inv.CreatedAt,
			UsedByID:  inv.UsedByID,
		})
	}
	if result == nil {
		result = []model.InviteOut{}
	}
	return result, nil
}

func (s *InviteService) RevokeInvite(ctx context.Context, user *model.User, inviteID int) (*model.InviteActionOut, error) {
	inv, err := s.repos.Invite.GetByID(ctx, inviteID)
	if err != nil {
		return nil, err
	}
	if inv == nil || inv.CreatorID != user.ID {
		return nil, model.NewAppError(model.ErrInviteNotFound, "邀请码不存在", 404)
	}

	if inv.Status == "used" {
		return nil, model.NewAppError(model.ErrInviteAlreadyUsed, "已使用的邀请码无法失效", 400)
	}

	if inv.Status == "revoked" || inv.Status == "expired" {
		return &model.InviteActionOut{Message: "邀请码已失效"}, nil
	}

	if err := s.repos.Invite.Revoke(ctx, inviteID); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "失效邀请码失败", 500)
	}

	return &model.InviteActionOut{Message: "邀请码已失效"}, nil
}

func (s *InviteService) RenewInvite(ctx context.Context, user *model.User, durationDays *int) (*model.InviteOut, error) {
	if !user.CanInvite {
		return nil, model.NewAppError(model.ErrInviteDisabled, "邀请权限已被关闭", 403)
	}

	_ = s.repos.Invite.SyncExpired(ctx, user.ID)

	active, err := s.repos.Invite.GetActiveByCreator(ctx, user.ID)
	if err != nil {
		return nil, err
	}
	if active == nil {
		return nil, model.NewAppError(model.ErrInviteNotFound, "没有可续期的邀请码，请先生成一个", 404)
	}

	var newExpiresAt *time.Time
	if durationDays != nil {
		now := time.Now().UTC()
		base := now
		if active.ExpiresAt != nil && active.ExpiresAt.After(now) {
			base = *active.ExpiresAt
		}
		t := base.Add(time.Duration(*durationDays) * 24 * time.Hour)
		newExpiresAt = &t
	}

	if err := s.repos.Invite.Renew(ctx, active.ID, newExpiresAt); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "续期邀请码失败", 500)
	}

	active.ExpiresAt = newExpiresAt
	return &model.InviteOut{
		ID:        active.ID,
		Code:      active.Code,
		Status:    active.Status,
		ExpiresAt: active.ExpiresAt,
		CreatedAt: active.CreatedAt,
		UsedByID:  active.UsedByID,
	}, nil
}
