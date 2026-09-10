package service

import (
	"context"
	"fmt"
	"strings"

	"backend/internal/model"
	"backend/internal/repository"
)

type FriendService struct {
	repos *repository.Repositories
}

func NewFriendService(repos *repository.Repositories) *FriendService {
	return &FriendService{repos: repos}
}

func (s *FriendService) RequestFriend(ctx context.Context, user *model.User, email string) (*model.FriendRequestActionOut, error) {
	cleanEmail := strings.ToLower(strings.TrimSpace(email))

	target, err := s.repos.User.GetByEmail(ctx, cleanEmail)
	if err != nil {
		return nil, err
	}
	if target == nil || target.Status != "active" {
		return nil, model.NewAppError(model.ErrUserNotFound, "用户不存在", 404)
	}

	if target.ID == user.ID {
		return nil, model.NewAppError(model.ErrCannotFriendSelf, "不能向自己发送好友请求", 400)
	}

	areFriends, err := s.repos.Friend.AreFriends(ctx, user.ID, target.ID)
	if err != nil {
		return nil, err
	}
	if areFriends {
		return nil, model.NewAppError(model.ErrAlreadyFriends, "你们已经是好友了", 400)
	}

	existing, err := s.repos.Friend.GetFriendship(ctx, user.ID, target.ID)
	if err != nil {
		return nil, err
	}
	if existing != nil && existing.Status == "pending" {
		return nil, model.NewAppError(model.ErrFriendRequestExists, "好友请求已存在，请等待对方确认", 400)
	}

	if err := s.repos.Friend.CreateRequest(ctx, user.ID, user.ID, target.ID); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "发送好友请求失败", 500)
	}

	return &model.FriendRequestActionOut{Message: "好友请求已发送"}, nil
}

func (s *FriendService) ListRequests(ctx context.Context, user *model.User) ([]model.FriendRequestOut, error) {
	reqs, err := s.repos.Friend.ListPendingRequests(ctx, user.ID)
	if err != nil {
		return nil, err
	}

	var requesterIDs []int
	for _, f := range reqs {
		requesterIDs = append(requesterIDs, f.RequesterID)
	}
	usersMap, err := s.repos.User.GetByIDs(ctx, requesterIDs)
	if err != nil {
		return nil, err
	}

	var result []model.FriendRequestOut
	for _, f := range reqs {
		requester := usersMap[f.RequesterID]
		if requester == nil {
			continue
		}
		result = append(result, model.FriendRequestOut{
			ID:        f.ID,
			Requester: s.buildUserBrief(requester),
			CreatedAt: f.CreatedAt,
		})
	}
	if result == nil {
		result = []model.FriendRequestOut{}
	}
	return result, nil
}

func (s *FriendService) AcceptRequest(ctx context.Context, user *model.User, requestID int) (*model.FriendRequestActionOut, error) {
	f, err := s.repos.Friend.GetRequestByID(ctx, requestID)
	if err != nil {
		return nil, err
	}
	if f == nil || f.Status != "pending" {
		return nil, model.NewAppError(model.ErrFriendRequestNotFound, "好友请求不存在", 404)
	}

	// Must be the receiver
	if f.RequesterID == user.ID || (f.UserAID != user.ID && f.UserBID != user.ID) {
		return nil, model.NewAppError(model.ErrForbidden, "无权处理此好友请求", 403)
	}

	if err := s.repos.Friend.AcceptRequest(ctx, requestID); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "接受好友请求失败", 500)
	}

	return &model.FriendRequestActionOut{Message: "已接受好友请求"}, nil
}

func (s *FriendService) RejectRequest(ctx context.Context, user *model.User, requestID int) (*model.FriendRequestActionOut, error) {
	f, err := s.repos.Friend.GetRequestByID(ctx, requestID)
	if err != nil {
		return nil, err
	}
	if f == nil || f.Status != "pending" {
		return nil, model.NewAppError(model.ErrFriendRequestNotFound, "好友请求不存在", 404)
	}

	// Must be the receiver
	if f.RequesterID == user.ID || (f.UserAID != user.ID && f.UserBID != user.ID) {
		return nil, model.NewAppError(model.ErrForbidden, "无权处理此好友请求", 403)
	}

	if err := s.repos.Friend.RejectRequest(ctx, requestID); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "拒绝好友请求失败", 500)
	}

	return &model.FriendRequestActionOut{Message: "已拒绝好友请求"}, nil
}

func (s *FriendService) ListFriends(ctx context.Context, user *model.User) ([]model.FriendOut, error) {
	friends, err := s.repos.Friend.ListFriends(ctx, user.ID)
	if err != nil {
		return nil, err
	}

	var otherIDs []int
	for _, f := range friends {
		otherID := f.UserBID
		if f.UserAID != user.ID {
			otherID = f.UserAID
		}
		otherIDs = append(otherIDs, otherID)
	}

	usersMap, err := s.repos.User.GetByIDs(ctx, otherIDs)
	if err != nil {
		return nil, err
	}

	var result []model.FriendOut
	for _, f := range friends {
		otherID := f.UserBID
		if f.UserAID != user.ID {
			otherID = f.UserAID
		}
		otherUser := usersMap[otherID]
		if otherUser == nil {
			continue
		}
		since := f.CreatedAt
		if f.AcceptedAt != nil {
			since = *f.AcceptedAt
		}
		result = append(result, model.FriendOut{
			ID:          f.ID,
			User:        s.buildUserBrief(otherUser),
			Since:       since,
			RequesterID: f.RequesterID,
		})
	}
	if result == nil {
		result = []model.FriendOut{}
	}
	return result, nil
}

func (s *FriendService) RemoveFriend(ctx context.Context, user *model.User, otherID int) error {
	areFriends, err := s.repos.Friend.AreFriends(ctx, user.ID, otherID)
	if err != nil {
		return err
	}
	if !areFriends {
		return model.NewAppError(model.ErrNotFriends, "你们还不是好友", 400)
	}

	return s.repos.Friend.RemoveFriendship(ctx, user.ID, otherID)
}

func (s *FriendService) buildUserBrief(u *model.User) model.FriendUserBrief {
	if u.Status == "deactivated" {
		return model.FriendUserBrief{
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
	return model.FriendUserBrief{
		ID:            u.ID,
		Nickname:      u.Nickname,
		AvatarURL:     avatarURL,
		IsDeactivated: false,
	}
}
