package service

import (
	"backend/internal/config"
	"backend/internal/repository"
)

type Services struct {
	Config     *config.Config
	Repos      *repository.Repositories
	System     *SystemService
	Auth       *AuthService
	User       *UserService
	Post       *PostService
	Comment    *CommentService
	Like       *LikeService
	Friend     *FriendService
	Invite     *InviteService
	Media      *MediaService
	Admin      *AdminService
	Bot        *BotService
	BotEngine  *BotEngine
	LLMClient  *LLMClient
}

func NewServices(cfg *config.Config, repos *repository.Repositories, botTriggerFunc func(botUserID int)) *Services {
	userService := NewUserService(cfg, repos)
	llmClient := NewLLMClient()
	botEngine := NewBotEngine(cfg, repos, llmClient)
	botService := NewBotService(cfg, repos, userService, botTriggerFunc)

	return &Services{
		Config:     cfg,
		Repos:      repos,
		System:     NewSystemService(cfg, repos),
		Auth:       NewAuthService(cfg, repos),
		User:       userService,
		Post:       NewPostService(cfg, repos),
		Comment:    NewCommentService(cfg, repos),
		Like:       NewLikeService(repos),
		Friend:     NewFriendService(repos),
		Invite:     NewInviteService(repos),
		Media:      NewMediaService(cfg, repos),
		Admin:      NewAdminService(cfg, repos, userService, llmClient),
		Bot:        botService,
		BotEngine:  botEngine,
		LLMClient:  llmClient,
	}
}
