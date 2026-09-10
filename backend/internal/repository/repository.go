package repository

import "github.com/jackc/pgx/v5/pgxpool"

type Repositories struct {
	User     *UserRepo
	System   *SystemRepo
	RSA      *RSARepo
	Friend   *FriendRepo
	Invite   *InviteRepo
	Post     *PostRepo
	Comment  *CommentRepo
	Like     *LikeRepo
	Bot      *BotRepo
	Media    *MediaRepo
}

func NewRepositories(pool *pgxpool.Pool) *Repositories {
	return &Repositories{
		User:    NewUserRepo(pool),
		System:  NewSystemRepo(pool),
		RSA:     NewRSARepo(pool),
		Friend:  NewFriendRepo(pool),
		Invite:  NewInviteRepo(pool),
		Post:    NewPostRepo(pool),
		Comment: NewCommentRepo(pool),
		Like:    NewLikeRepo(pool),
		Bot:     NewBotRepo(pool),
		Media:   NewMediaRepo(pool),
	}
}
