package service

import (
	"context"
	"fmt"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
)

type AdminService struct {
	cfg         *config.Config
	repos       *repository.Repositories
	userService *UserService
	llmClient   *LLMClient
}

func NewAdminService(cfg *config.Config, repos *repository.Repositories, userService *UserService, llmClient *LLMClient) *AdminService {
	return &AdminService{
		cfg:         cfg,
		repos:       repos,
		userService: userService,
		llmClient:   llmClient,
	}
}

func (s *AdminService) GetStats(ctx context.Context) (*model.StatsOut, error) {
	userCount, err := s.repos.User.CountAll(ctx)
	if err != nil {
		return nil, err
	}
	postCount, err := s.repos.Post.CountActive(ctx)
	if err != nil {
		return nil, err
	}
	commentCount, err := s.repos.Comment.CountActive(ctx)
	if err != nil {
		return nil, err
	}
	likeCount, err := s.repos.Like.CountAll(ctx)
	if err != nil {
		return nil, err
	}
	totalInvites, usedInvites, err := s.repos.Invite.CountAll(ctx)
	if err != nil {
		return nil, err
	}

	return &model.StatsOut{
		UserCount:       userCount,
		PostCount:       postCount,
		CommentCount:    commentCount,
		LikeCount:       likeCount,
		InviteCount:     totalInvites,
		UsedInviteCount: usedInvites,
	}, nil
}

func (s *AdminService) ListUsers(ctx context.Context, page, pageSize int, search string) (*model.AdminUserListOut, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	} else if pageSize > 100 {
		pageSize = 100
	}

	offset := (page - 1) * pageSize
	users, total, err := s.repos.User.ListAdmin(ctx, search, offset, pageSize)
	if err != nil {
		return nil, err
	}

	var items []model.AdminUserOut
	for _, u := range users {
		items = append(items, model.AdminUserOut{
			ID:          u.ID,
			Email:       u.Email,
			Nickname:    u.Nickname,
			Role:        u.Role,
			Status:      u.Status,
			CanInvite:   u.CanInvite,
			AvatarURL:   s.userService.AvatarURLFor(u),
			CreatedAt:   u.CreatedAt,
			LastLoginAt: u.LastLoginAt,
		})
	}
	if items == nil {
		items = []model.AdminUserOut{}
	}

	hasMore := offset+pageSize < total
	return &model.AdminUserListOut{
		Items:    items,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		HasMore:  hasMore,
	}, nil
}

func (s *AdminService) UpdateUser(ctx context.Context, userID int, data model.AdminUserUpdateIn) (*model.AdminUserOut, error) {
	user, err := s.repos.User.GetByID(ctx, userID)
	if err != nil {
		return nil, err
	}
	if user == nil {
		return nil, model.NewAppError(model.ErrUserNotFound, "用户不存在", 404)
	}

	if data.Restore != nil && *data.Restore {
		if user.Status == "deactivated" {
			user.Status = "active"
		}
	}

	if data.Status != nil {
		if user.Status == "deactivated" {
			return nil, model.NewAppError(model.ErrValidationError, "无法直接修改已注销用户的状态，请使用恢复操作", 400)
		}
		user.Status = *data.Status
	}

	if data.CanInvite != nil {
		user.CanInvite = *data.CanInvite
	}

	if err := s.repos.User.Update(ctx, user); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "更新用户状态失败", 500)
	}

	return &model.AdminUserOut{
		ID:          user.ID,
		Email:       user.Email,
		Nickname:    user.Nickname,
		Role:        user.Role,
		Status:      user.Status,
		CanInvite:   user.CanInvite,
		AvatarURL:   s.userService.AvatarURLFor(user),
		CreatedAt:   user.CreatedAt,
		LastLoginAt: user.LastLoginAt,
	}, nil
}

func (s *AdminService) ListPosts(ctx context.Context, page, pageSize int, userID *int, visibility *string) (*model.AdminPostListOut, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	} else if pageSize > 100 {
		pageSize = 100
	}

	offset := (page - 1) * pageSize
	posts, total, err := s.repos.Post.ListAdmin(ctx, userID, visibility, offset, pageSize)
	if err != nil {
		return nil, err
	}

	if len(posts) == 0 {
		return &model.AdminPostListOut{
			Items:    []model.AdminPostOut{},
			Total:    total,
			Page:     page,
			PageSize: pageSize,
			HasMore:  false,
		}, nil
	}

	postIDs := make([]int, len(posts))
	authorIDs := make(map[int]bool)
	for i, p := range posts {
		postIDs[i] = p.ID
		authorIDs[p.UserID] = true
	}

	likeCounts, _ := s.repos.Post.BatchPreloadLikeCounts(ctx, postIDs)
	commentCounts, _ := s.repos.Post.BatchPreloadCommentCounts(ctx, postIDs)

	var uids []int
	for uid := range authorIDs {
		uids = append(uids, uid)
	}
	usersMap, _ := s.repos.User.GetByIDs(ctx, uids)

	var items []model.AdminPostOut
	for _, p := range posts {
		author := usersMap[p.UserID]
		authorOut := s.buildAdminAuthorOut(author)

		items = append(items, model.AdminPostOut{
			ID:           p.ID,
			Content:      p.Content,
			Visibility:   p.Visibility,
			Deleted:      p.DeletedAt != nil,
			Author:       authorOut,
			LikeCount:    likeCounts[p.ID],
			CommentCount: commentCounts[p.ID],
			CreatedAt:    p.CreatedAt,
			DeletedAt:    p.DeletedAt,
		})
	}

	hasMore := offset+pageSize < total
	return &model.AdminPostListOut{
		Items:    items,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		HasMore:  hasMore,
	}, nil
}

func (s *AdminService) DeletePost(ctx context.Context, postID int) error {
	post, err := s.repos.Post.GetByIDIncludeDeleted(ctx, postID)
	if err != nil {
		return err
	}
	if post == nil {
		return model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}
	if post.DeletedAt != nil {
		return nil
	}
	return s.repos.Post.SoftDelete(ctx, postID)
}

func (s *AdminService) ListComments(ctx context.Context, page, pageSize int) (*model.AdminCommentListOut, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	} else if pageSize > 100 {
		pageSize = 100
	}

	offset := (page - 1) * pageSize
	comments, total, err := s.repos.Comment.ListAdmin(ctx, offset, pageSize)
	if err != nil {
		return nil, err
	}

	if len(comments) == 0 {
		return &model.AdminCommentListOut{
			Items:    []model.AdminCommentOut{},
			Total:    total,
			Page:     page,
			PageSize: pageSize,
			HasMore:  false,
		}, nil
	}

	commentIDs := make([]int, len(comments))
	authorIDs := make(map[int]bool)
	for i, c := range comments {
		commentIDs[i] = c.ID
		authorIDs[c.UserID] = true
	}

	likeCounts, _ := s.repos.Comment.BatchPreloadLikeCounts(ctx, commentIDs)

	var uids []int
	for uid := range authorIDs {
		uids = append(uids, uid)
	}
	usersMap, _ := s.repos.User.GetByIDs(ctx, uids)

	var items []model.AdminCommentOut
	for _, c := range comments {
		author := usersMap[c.UserID]
		authorOut := s.buildAdminAuthorOut(author)

		var thumbURL *string
		if c.ImageThumbPath != nil {
			u := fmt.Sprintf("/api/v1/comments/%d/media/thumb", c.ID)
			thumbURL = &u
		}

		items = append(items, model.AdminCommentOut{
			ID:            c.ID,
			PostID:        c.PostID,
			Content:       c.Content,
			ImageThumbURL: thumbURL,
			Deleted:       c.DeletedAt != nil,
			Author:        authorOut,
			LikeCount:     likeCounts[c.ID],
			CreatedAt:     c.CreatedAt,
			DeletedAt:     c.DeletedAt,
		})
	}

	hasMore := offset+pageSize < total
	return &model.AdminCommentListOut{
		Items:    items,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		HasMore:  hasMore,
	}, nil
}

func (s *AdminService) DeleteComment(ctx context.Context, commentID int) error {
	comment, err := s.repos.Comment.GetByIDIncludeDeleted(ctx, commentID)
	if err != nil {
		return err
	}
	if comment == nil {
		return model.NewAppError(model.ErrCommentNotFound, "评论不存在", 404)
	}
	if comment.DeletedAt != nil {
		return nil
	}
	return s.repos.Comment.SoftDelete(ctx, commentID)
}

func (s *AdminService) ListInvites(ctx context.Context, page, pageSize int) (*model.AdminInviteListOut, error) {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	} else if pageSize > 100 {
		pageSize = 100
	}

	offset := (page - 1) * pageSize
	invites, total, err := s.repos.Invite.ListAdmin(ctx, offset, pageSize)
	if err != nil {
		return nil, err
	}

	var creatorIDs []int
	for _, inv := range invites {
		creatorIDs = append(creatorIDs, inv.CreatorID)
	}
	usersMap, _ := s.repos.User.GetByIDs(ctx, creatorIDs)

	var items []model.AdminInviteOut
	for _, inv := range invites {
		creator := usersMap[inv.CreatorID]
		items = append(items, model.AdminInviteOut{
			ID:        inv.ID,
			Code:      inv.Code,
			Status:    inv.Status,
			ExpiresAt: inv.ExpiresAt,
			CreatedAt: inv.CreatedAt,
			UsedByID:  inv.UsedByID,
			Creator:   s.buildAdminAuthorOut(creator),
		})
	}
	if items == nil {
		items = []model.AdminInviteOut{}
	}

	hasMore := offset+pageSize < total
	return &model.AdminInviteListOut{
		Items:    items,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		HasMore:  hasMore,
	}, nil
}

func (s *AdminService) RevokeInvite(ctx context.Context, inviteID int) (*model.InviteActionOut, error) {
	inv, err := s.repos.Invite.GetByID(ctx, inviteID)
	if err != nil {
		return nil, err
	}
	if inv == nil {
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

func (s *AdminService) GetLLMConfig(ctx context.Context) (*model.LLMConfigOut, error) {
	st, err := s.repos.System.GetStatus(ctx)
	if err != nil {
		return nil, err
	}
	if st == nil {
		return nil, model.NewAppError(model.ErrNotFound, "系统状态未初始化", 500)
	}

	return &model.LLMConfigOut{
		BaseURL:   st.LLMBaseURL,
		Model:     st.LLMModel,
		Timeout:   st.LLMTimeout,
		MaxTokens: st.LLMMaxTokens,
		HasAPIKey: st.LLMAPIKey != "",
	}, nil
}

func (s *AdminService) UpdateLLMConfig(ctx context.Context, data model.LLMConfigUpdateIn) (*model.LLMConfigOut, error) {
	st, err := s.repos.System.UpdateLLMConfig(ctx, data.BaseURL, data.APIKey, data.Model, data.Timeout, data.MaxTokens)
	if err != nil {
		return nil, model.NewAppError(model.ErrInternal, "更新大模型配置失败", 500)
	}

	return &model.LLMConfigOut{
		BaseURL:   st.LLMBaseURL,
		Model:     st.LLMModel,
		Timeout:   st.LLMTimeout,
		MaxTokens: st.LLMMaxTokens,
		HasAPIKey: st.LLMAPIKey != "",
	}, nil
}

func (s *AdminService) TestLLMConfig(ctx context.Context, data model.LLMConfigTestIn) (*model.LLMTestOut, error) {
	st, err := s.repos.System.GetStatus(ctx)
	if err != nil || st == nil {
		return nil, model.NewAppError(model.ErrNotFound, "系统状态未初始化", 500)
	}

	baseURL := st.LLMBaseURL
	if data.BaseURL != nil && *data.BaseURL != "" {
		baseURL = *data.BaseURL
	}
	apiKey := st.LLMAPIKey
	if data.APIKey != nil && *data.APIKey != "" {
		apiKey = *data.APIKey
	}
	modelName := st.LLMModel
	if data.Model != nil && *data.Model != "" {
		modelName = *data.Model
	}
	timeout := st.LLMTimeout
	if data.Timeout != nil && *data.Timeout > 0 {
		timeout = *data.Timeout
	}

	reply, err := s.llmClient.TestLLM(ctx, baseURL, apiKey, modelName, timeout)
	if err != nil {
		return &model.LLMTestOut{
			Success: false,
			Message: fmt.Sprintf("测试失败：%v", err),
		}, nil
	}

	return &model.LLMTestOut{
		Success: true,
		Message: fmt.Sprintf("测试成功，模型回复：%s", reply),
	}, nil
}

func (s *AdminService) buildAdminAuthorOut(u *model.User) model.AdminAuthorOut {
	if u == nil {
		return model.AdminAuthorOut{
			ID:            0,
			Email:         "",
			Nickname:      "未知",
			AvatarURL:     "/api/v1/avatars/default",
			IsDeactivated: false,
		}
	}
	if u.Status == "deactivated" {
		return model.AdminAuthorOut{
			ID:            u.ID,
			Email:         u.Email,
			Nickname:      "已注销",
			AvatarURL:     "/api/v1/avatars/default",
			IsDeactivated: true,
		}
	}
	avatarURL := "/api/v1/avatars/default"
	if u.AvatarPath != nil && *u.AvatarPath != "" {
		avatarURL = fmt.Sprintf("/api/v1/avatars/%d", u.ID)
	}
	return model.AdminAuthorOut{
		ID:            u.ID,
		Email:         u.Email,
		Nickname:      u.Nickname,
		AvatarURL:     avatarURL,
		IsDeactivated: false,
	}
}
