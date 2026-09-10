package service

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type BotService struct {
	cfg         *config.Config
	repos       *repository.Repositories
	userService *UserService
	triggerFunc func(botUserID int)
}

func NewBotService(cfg *config.Config, repos *repository.Repositories, userService *UserService, triggerFunc func(botUserID int)) *BotService {
	return &BotService{
		cfg:         cfg,
		repos:       repos,
		userService: userService,
		triggerFunc: triggerFunc,
	}
}

func (s *BotService) SetTriggerFunc(f func(botUserID int)) {
	s.triggerFunc = f
}

func (s *BotService) ListBotsAdmin(ctx context.Context) ([]model.BotAdminOut, error) {
	bots, err := s.repos.Bot.ListAll(ctx)
	if err != nil {
		return nil, err
	}

	var userIDs []int
	for _, b := range bots {
		userIDs = append(userIDs, b.UserID)
	}
	usersMap, err := s.repos.User.GetByIDs(ctx, userIDs)
	if err != nil {
		return nil, err
	}

	var result []model.BotAdminOut
	for _, b := range bots {
		u := usersMap[b.UserID]
		result = append(result, s.buildBotAdminOut(b, u))
	}
	if result == nil {
		result = []model.BotAdminOut{}
	}
	return result, nil
}

func (s *BotService) GetBotAdmin(ctx context.Context, id int) (*model.BotAdminOut, error) {
	bot, err := s.repos.Bot.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if bot == nil {
		return nil, model.NewAppError(model.ErrBotNotFound, "机器人不存在", 404)
	}

	u, _ := s.repos.User.GetByID(ctx, bot.UserID)
	res := s.buildBotAdminOut(bot, u)
	return &res, nil
}

func (s *BotService) CreateBot(ctx context.Context, data model.BotCreateIn) (*model.BotAdminOut, error) {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	placeholderEmail := fmt.Sprintf("bot_%s@bot.local", hex.EncodeToString(b))

	pwb := make([]byte, 16)
	_, _ = rand.Read(pwb)
	pwHash, _ := util.HashPassword(hex.EncodeToString(pwb))

	user := &model.User{
		Email:        placeholderEmail,
		PasswordHash: pwHash,
		Nickname:     data.Nickname,
		Role:         "bot",
		Status:       "active",
		CanInvite:    false,
	}

	if err := s.repos.User.Create(ctx, user); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建机器人用户失败", 500)
	}

	user.Email = fmt.Sprintf("bot_%d@bot.local", user.ID)
	_ = s.repos.User.Update(ctx, user)

	pollN := data.PollIntervalN
	if pollN <= 0 {
		pollN = 600
	}
	pollX := data.PollIntervalX
	if pollX < 0 {
		pollX = 60
	}
	lookback := data.LookbackDays
	if lookback <= 0 {
		lookback = 3
	}
	cph := data.CommentsPerHour
	if cph <= 0 {
		cph = 10
	}
	maxFailures := data.MaxConsecutiveFailures
	if maxFailures <= 0 {
		maxFailures = 5
	}

	bot := &model.Bot{
		UserID:                 user.ID,
		Persona:                data.Persona,
		PollIntervalN:          pollN,
		PollIntervalX:          pollX,
		LookbackDays:           lookback,
		CommentsPerHour:        cph,
		MaxConsecutiveFailures: maxFailures,
		LLMModel:               data.LLMModel,
		Enabled:                true,
		AutoPaused:             false,
		ConsecutiveFailures:    0,
	}

	if err := s.repos.Bot.Create(ctx, bot); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建机器人记录失败", 500)
	}

	res := s.buildBotAdminOut(bot, user)
	return &res, nil
}

func (s *BotService) UpdateBot(ctx context.Context, id int, data model.BotUpdateIn) (*model.BotAdminOut, error) {
	bot, err := s.repos.Bot.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if bot == nil {
		return nil, model.NewAppError(model.ErrBotNotFound, "机器人不存在", 404)
	}

	user, _ := s.repos.User.GetByID(ctx, bot.UserID)

	if data.Restore != nil && *data.Restore {
		bot.AutoPaused = false
		bot.ConsecutiveFailures = 0
	}

	if data.Nickname != nil && *data.Nickname != "" && user != nil {
		user.Nickname = *data.Nickname
		_ = s.repos.User.UpdateProfile(ctx, user.ID, data.Nickname, nil)
	}

	if data.Persona != nil {
		bot.Persona = *data.Persona
	}
	if data.PollIntervalN != nil {
		bot.PollIntervalN = *data.PollIntervalN
	}
	if data.PollIntervalX != nil {
		bot.PollIntervalX = *data.PollIntervalX
	}
	if data.LookbackDays != nil {
		bot.LookbackDays = *data.LookbackDays
	}
	if data.CommentsPerHour != nil {
		bot.CommentsPerHour = *data.CommentsPerHour
	}
	if data.MaxConsecutiveFailures != nil {
		bot.MaxConsecutiveFailures = *data.MaxConsecutiveFailures
	}
	if data.LLMModel != nil {
		bot.LLMModel = data.LLMModel
	}
	if data.Enabled != nil {
		bot.Enabled = *data.Enabled
	}

	if err := s.repos.Bot.Update(ctx, bot); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "更新机器人失败", 500)
	}

	res := s.buildBotAdminOut(bot, user)
	return &res, nil
}

func (s *BotService) DeleteBot(ctx context.Context, id int) (*model.BotActionOut, error) {
	bot, err := s.repos.Bot.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if bot == nil {
		return nil, model.NewAppError(model.ErrBotNotFound, "机器人不存在", 404)
	}

	if err := s.repos.Bot.Delete(ctx, id); err != nil {
		return nil, err
	}
	return &model.BotActionOut{Message: "机器人已停用"}, nil
}

func (s *BotService) UploadBotAvatar(ctx context.Context, id int, filename string, content []byte) (*model.BotActionOut, error) {
	bot, err := s.repos.Bot.GetByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if bot == nil {
		return nil, model.NewAppError(model.ErrBotNotFound, "机器人不存在", 404)
	}

	user, err := s.repos.User.GetByID(ctx, bot.UserID)
	if err != nil || user == nil {
		return nil, model.NewAppError(model.ErrBotNotFound, "机器人用户不存在", 404)
	}

	if _, err := s.userService.UploadAvatar(ctx, user, filename, content); err != nil {
		return nil, err
	}

	return &model.BotActionOut{Message: "头像已更新"}, nil
}

func (s *BotService) ListBotsPublic(ctx context.Context, user *model.User) ([]model.BotPublicOut, error) {
	bots, err := s.repos.Bot.ListEnabled(ctx)
	if err != nil {
		return nil, err
	}

	var userIDs []int
	for _, b := range bots {
		userIDs = append(userIDs, b.UserID)
	}
	usersMap, err := s.repos.User.GetByIDs(ctx, userIDs)
	if err != nil {
		return nil, err
	}

	var result []model.BotPublicOut
	for _, b := range bots {
		u := usersMap[b.UserID]
		isFriend, _ := s.repos.Friend.AreFriends(ctx, user.ID, b.UserID)

		nickname := ""
		avatarURL := "/api/v1/avatars/default"
		if u != nil {
			nickname = u.Nickname
			avatarURL = s.userService.AvatarURLFor(u)
		}

		brief := b.Persona
		runes := []rune(brief)
		if len(runes) > 80 {
			brief = string(runes[:80])
		}

		result = append(result, model.BotPublicOut{
			ID:           b.ID,
			UserID:       b.UserID,
			Nickname:     nickname,
			AvatarURL:    avatarURL,
			PersonaBrief: brief,
			IsFriend:     isFriend,
		})
	}
	if result == nil {
		result = []model.BotPublicOut{}
	}
	return result, nil
}

func (s *BotService) AddBotFriend(ctx context.Context, user *model.User, botUserID int) (*model.FriendRequestActionOut, error) {
	botUser, err := s.repos.User.GetByID(ctx, botUserID)
	if err != nil || botUser == nil {
		return nil, model.NewAppError(model.ErrUserNotFound, "用户不存在", 404)
	}
	if botUser.Role != "bot" {
		return nil, model.NewAppError(model.ErrUserNotFound, "该用户不是机器人", 404)
	}
	if botUser.Status != "active" {
		return nil, model.NewAppError(model.ErrUserNotFound, "机器人不可用", 404)
	}

	areFriends, err := s.repos.Friend.AreFriends(ctx, user.ID, botUserID)
	if err != nil {
		return nil, err
	}
	if areFriends {
		return nil, model.NewAppError(model.ErrAlreadyFriends, "你们已经是好友了", 400)
	}

	if err := s.repos.Friend.AddDirectFriend(ctx, user.ID, botUserID, user.ID); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "添加好友失败", 500)
	}

	return &model.FriendRequestActionOut{Message: "已添加机器人为好友"}, nil
}

func (s *BotService) TriggerBot(ctx context.Context, botID int) (*model.BotActionOut, error) {
	bot, err := s.repos.Bot.GetByID(ctx, botID)
	if err != nil {
		return nil, err
	}
	if bot == nil {
		return nil, model.NewAppError(model.ErrBotNotFound, "机器人不存在", 404)
	}

	if s.triggerFunc != nil {
		s.triggerFunc(bot.UserID)
	}

	return &model.BotActionOut{Message: "已触发轮询"}, nil
}

func (s *BotService) buildBotAdminOut(b *model.Bot, u *model.User) model.BotAdminOut {
	nickname := ""
	email := ""
	avatarURL := "/api/v1/avatars/default"
	if u != nil {
		nickname = u.Nickname
		email = u.Email
		avatarURL = s.userService.AvatarURLFor(u)
	}

	return model.BotAdminOut{
		ID:                     b.ID,
		UserID:                 b.UserID,
		Nickname:               nickname,
		Email:                  email,
		AvatarURL:              avatarURL,
		Persona:                b.Persona,
		PollIntervalN:          b.PollIntervalN,
		PollIntervalX:          b.PollIntervalX,
		LookbackDays:           b.LookbackDays,
		CommentsPerHour:        b.CommentsPerHour,
		MaxConsecutiveFailures: b.MaxConsecutiveFailures,
		LLMModel:               b.LLMModel,
		Enabled:                b.Enabled,
		AutoPaused:             b.AutoPaused,
		ConsecutiveFailures:    b.ConsecutiveFailures,
		LastRunAt:              b.LastRunAt,
		NextRunAt:              b.NextRunAt,
		CreatedAt:              b.CreatedAt,
	}
}
