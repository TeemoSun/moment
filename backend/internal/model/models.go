package model

import "time"

// ===== Database Entities =====

type SystemStatus struct {
	ID           int       `json:"id"`
	Initialized  bool      `json:"initialized"`
	AdminUserID  *int      `json:"admin_user_id"`
	LLMBaseURL   string    `json:"llm_base_url"`
	LLMAPIKey    string    `json:"llm_api_key"`
	LLMModel     string    `json:"llm_model"`
	LLMTimeout   int       `json:"llm_timeout"`
	LLMMaxTokens int       `json:"llm_max_tokens"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
}

type User struct {
	ID                int        `json:"id"`
	Email             string     `json:"email"`
	PasswordHash      string     `json:"-"`
	Nickname          string     `json:"nickname"`
	Signature         *string    `json:"signature"`
	AvatarPath        *string    `json:"avatar_path"`
	Role              string     `json:"role"`
	Status            string     `json:"status"`
	CanInvite         bool       `json:"can_invite"`
	FailedLoginCount  int        `json:"failed_login_count"`
	LockedUntil       *time.Time `json:"locked_until"`
	LastLoginAt       *time.Time `json:"last_login_at"`
	TokenVersion      int        `json:"token_version"`
	CreatedAt         time.Time  `json:"created_at"`
	UpdatedAt         time.Time  `json:"updated_at"`
}

type Post struct {
	ID         int        `json:"id"`
	UserID     int        `json:"user_id"`
	Content    string     `json:"content"`
	Visibility string     `json:"visibility"`
	DeletedAt  *time.Time `json:"deleted_at"`
	CreatedAt  time.Time  `json:"created_at"`
	UpdatedAt  time.Time  `json:"updated_at"`
}

type PostMedia struct {
	ID        int       `json:"id"`
	PostID    *int      `json:"post_id"`
	OwnerID   *int      `json:"owner_id"`
	FilePath  string    `json:"file_path"`
	ThumbPath *string   `json:"thumb_path"`
	LargePath *string   `json:"large_path"`
	Filename  string    `json:"filename"`
	Size      int       `json:"size"`
	Mime      string    `json:"mime"`
	Format    string    `json:"format"`
	Kind      string    `json:"kind"`
	SortOrder int       `json:"sort_order"`
	CreatedAt time.Time `json:"created_at"`
}

type Comment struct {
	ID              int        `json:"id"`
	PostID          int        `json:"post_id"`
	UserID          int        `json:"user_id"`
	ParentCommentID *int       `json:"parent_comment_id"`
	ReplyToUserID   *int       `json:"reply_to_user_id"`
	Content         *string    `json:"content"`
	ImagePath       *string    `json:"image_path"`
	ImageThumbPath  *string    `json:"image_thumb_path"`
	ImageLargePath  *string    `json:"image_large_path"`
	DeletedAt       *time.Time `json:"deleted_at"`
	CreatedAt       time.Time  `json:"created_at"`
	UpdatedAt       time.Time  `json:"updated_at"`
}

type Like struct {
	ID         int       `json:"id"`
	TargetType string    `json:"target_type"`
	TargetID   int       `json:"target_id"`
	UserID     int       `json:"user_id"`
	CreatedAt  time.Time `json:"created_at"`
}

type Friendship struct {
	ID          int        `json:"id"`
	UserAID     int        `json:"user_a_id"`
	UserBID     int        `json:"user_b_id"`
	Status      string     `json:"status"`
	RequesterID int        `json:"requester_id"`
	CreatedAt   time.Time  `json:"created_at"`
	AcceptedAt  *time.Time `json:"accepted_at"`
}

type InviteCode struct {
	ID        int        `json:"id"`
	Code      string     `json:"code"`
	CreatorID int        `json:"creator_id"`
	Status    string     `json:"status"`
	ExpiresAt *time.Time `json:"expires_at"`
	UsedByID  *int       `json:"used_by_id"`
	CreatedAt time.Time  `json:"created_at"`
}

type Bot struct {
	ID                     int        `json:"id"`
	UserID                 int        `json:"user_id"`
	Persona                string     `json:"persona"`
	PollIntervalN          int        `json:"poll_interval_n"`
	PollIntervalX          int        `json:"poll_interval_x"`
	LookbackDays           int        `json:"lookback_days"`
	CommentsPerHour        int        `json:"comments_per_hour"`
	MaxConsecutiveFailures int        `json:"max_consecutive_failures"`
	LLMModel               *string    `json:"llm_model"`
	Enabled                bool       `json:"enabled"`
	AutoPaused             bool       `json:"auto_paused"`
	ConsecutiveFailures    int        `json:"consecutive_failures"`
	LastRunAt              *time.Time `json:"last_run_at"`
	NextRunAt              *time.Time `json:"next_run_at"`
	CreatedAt              time.Time  `json:"created_at"`
	UpdatedAt              time.Time  `json:"updated_at"`
}

type BotReplyLog struct {
	ID              int       `json:"id"`
	BotUserID       int       `json:"bot_user_id"`
	PostID          int       `json:"post_id"`
	Kind            string    `json:"kind"`
	TargetCommentID *int      `json:"target_comment_id"`
	ReplyCommentID  int       `json:"reply_comment_id"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

type FileMetadata struct {
	ID           int       `json:"id"`
	StoragePath  string    `json:"storage_path"`
	OriginalName string    `json:"original_name"`
	Filename     string    `json:"filename"`
	Size         int       `json:"size"`
	Mime         string    `json:"mime"`
	Format       string    `json:"format"`
	Kind         string    `json:"kind"`
	OwnerID      *int      `json:"owner_id"`
	CreatedAt    time.Time `json:"created_at"`
}

type RSAKey struct {
	ID             int       `json:"id"`
	PublicKeyPEM   string    `json:"public_key_pem"`
	PrivateKeyPEM  string    `json:"private_key_pem"`
	CreatedAt      time.Time `json:"created_at"`
}

// ===== System Schemas =====

type InitializedOut struct {
	Initialized            bool   `json:"initialized"`
	AllowInsecureClipboard bool   `json:"allow_insecure_clipboard"`
	AppName                string `json:"app_name"`
}

type InitIn struct {
	Email    string `json:"email"`
	Nickname string `json:"nickname"`
	Password string `json:"password"`
}

// ===== Auth Schemas =====

type RSAKeyOut struct {
	PublicKey string `json:"public_key"`
}

type RegisterIn struct {
	Email      string `json:"email"`
	Nickname   string `json:"nickname"`
	Password   string `json:"password"`
	InviteCode string `json:"invite_code"`
}

type LoginIn struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type TokenOut struct {
	User MeOut `json:"user"`
}

// ===== User Schemas =====

type MeOut struct {
	ID        int       `json:"id"`
	Email     string    `json:"email"`
	Nickname  string    `json:"nickname"`
	Signature *string   `json:"signature"`
	AvatarURL string    `json:"avatar_url"`
	Role      string    `json:"role"`
	Status    string    `json:"status"`
	CanInvite bool      `json:"can_invite"`
	CreatedAt time.Time `json:"created_at"`
}

type MeUpdateIn struct {
	Nickname  *string `json:"nickname"`
	Signature *string `json:"signature"`
}

type PasswordChangeIn struct {
	OldPassword string `json:"old_password"`
	NewPassword string `json:"new_password"`
}

type OtherUserOut struct {
	ID               int       `json:"id"`
	Nickname         string    `json:"nickname"`
	Signature        *string   `json:"signature"`
	AvatarURL        string    `json:"avatar_url"`
	IsDeactivated    bool      `json:"is_deactivated"`
	CreatedAt        time.Time `json:"created_at"`
	FriendshipStatus string    `json:"friendship_status"`
	IsBot            bool      `json:"is_bot"`
	PersonaBrief     *string   `json:"persona_brief"`
}

type AvatarOut struct {
	AvatarURL string `json:"avatar_url"`
}

// ===== Post Schemas =====

type PostCreateIn struct {
	Content    string `json:"content"`
	MediaIDs   []int  `json:"media_ids"`
	Visibility string `json:"visibility"`
}

type MediaBriefOut struct {
	ID          int     `json:"id"`
	Kind        string  `json:"kind"`
	SortOrder   int     `json:"sort_order"`
	ThumbURL    *string `json:"thumb_url"`
	LargeURL    *string `json:"large_url"`
	OriginalURL *string `json:"original_url"`
}

type AuthorOut struct {
	ID            int    `json:"id"`
	Nickname      string `json:"nickname"`
	AvatarURL     string `json:"avatar_url"`
	IsDeactivated bool   `json:"is_deactivated"`
}

type PostOut struct {
	ID              int             `json:"id"`
	Content         string          `json:"content"`
	Visibility      string          `json:"visibility"`
	Author          AuthorOut       `json:"author"`
	Media           []MediaBriefOut `json:"media"`
	LikeCount       int             `json:"like_count"`
	CommentCount    int             `json:"comment_count"`
	LikedByMe       bool            `json:"liked_by_me"`
	IsOwner         bool            `json:"is_owner"`
	CreatedAt       time.Time       `json:"created_at"`
	UpdatedAt       time.Time       `json:"updated_at"`
	PreviewComments []CommentOut    `json:"preview_comments"`
	LikeAuthors     []LikeAuthorOut `json:"like_authors"`
}

type PostDetailOut = PostOut

type FeedOut struct {
	Items      []PostOut `json:"items"`
	NextCursor *string   `json:"next_cursor"`
	HasMore    bool      `json:"has_more"`
}

type UserPostsOut struct {
	Items      []PostOut `json:"items"`
	NextCursor *string   `json:"next_cursor"`
	HasMore    bool      `json:"has_more"`
}

// ===== Comment Schemas =====

type CommentAuthorOut struct {
	ID            int    `json:"id"`
	Nickname      string `json:"nickname"`
	AvatarURL     string `json:"avatar_url"`
	IsDeactivated bool   `json:"is_deactivated"`
}

type ReplyToOut struct {
	ID            int    `json:"id"`
	Nickname      string `json:"nickname"`
	IsDeactivated bool   `json:"is_deactivated"`
}

type LikeAuthorOut struct {
	ID            int    `json:"id"`
	Nickname      string `json:"nickname"`
	AvatarURL     string `json:"avatar_url"`
	IsDeactivated bool   `json:"is_deactivated"`
}

type CommentOut struct {
	ID                  int              `json:"id"`
	PostID              int              `json:"post_id"`
	Author              CommentAuthorOut `json:"author"`
	ParentCommentID     *int             `json:"parent_comment_id"`
	ReplyTo             *ReplyToOut      `json:"reply_to"`
	ReplyContentPreview *string          `json:"reply_content_preview"`
	Content             *string          `json:"content"`
	ImageThumbURL       *string          `json:"image_thumb_url"`
	ImageLargeURL       *string          `json:"image_large_url"`
	LikeCount           int              `json:"like_count"`
	LikedByMe           bool             `json:"liked_by_me"`
	IsOwner             bool             `json:"is_owner"`
	CanDelete           bool             `json:"can_delete"`
	CreatedAt           time.Time        `json:"created_at"`
}

type CommentListOut struct {
	Items   []CommentOut `json:"items"`
	Total   int          `json:"total"`
	Page    int          `json:"page"`
	PageSize int         `json:"page_size"`
	HasMore bool         `json:"has_more"`
}

type CommentCreateIn struct {
	Content         *string `json:"content"`
	MediaID         *int    `json:"media_id"`
	ParentCommentID *int    `json:"parent_comment_id"`
	ReplyToUserID   *int    `json:"reply_to_user_id"`
}

type LikeCountOut struct {
	TargetType string `json:"target_type"`
	TargetID   int    `json:"target_id"`
	LikeCount  int    `json:"like_count"`
	LikedByMe  bool   `json:"liked_by_me"`
}

type CommentMediaOut struct {
	MediaID       int     `json:"media_id"`
	ImageThumbURL *string `json:"image_thumb_url"`
	ImageLargeURL *string `json:"image_large_url"`
	Status        string  `json:"status"`
}

// ===== Friend Schemas =====

type FriendRequestIn struct {
	Email string `json:"email"`
}

type FriendUserBrief struct {
	ID            int    `json:"id"`
	Nickname      string `json:"nickname"`
	AvatarURL     string `json:"avatar_url"`
	IsDeactivated bool   `json:"is_deactivated"`
}

type FriendRequestOut struct {
	ID        int             `json:"id"`
	Requester FriendUserBrief `json:"requester"`
	CreatedAt time.Time       `json:"created_at"`
}

type FriendOut struct {
	ID          int             `json:"id"`
	User        FriendUserBrief `json:"user"`
	Since       time.Time       `json:"since"`
	RequesterID int             `json:"requester_id"`
}

type FriendRequestActionOut struct {
	Message string `json:"message"`
}

// ===== Invite Schemas =====

type InviteCreateIn struct {
	DurationDays *int `json:"duration_days"`
}

type InviteOut struct {
	ID        int        `json:"id"`
	Code      string     `json:"code"`
	Status    string     `json:"status"`
	ExpiresAt *time.Time `json:"expires_at"`
	CreatedAt time.Time  `json:"created_at"`
	UsedByID  *int       `json:"used_by_id"`
}

type InviteActionOut struct {
	Message string `json:"message"`
}

// ===== Bot Schemas =====

type BotCreateIn struct {
	Nickname               string  `json:"nickname"`
	Persona                string  `json:"persona"`
	PollIntervalN          int     `json:"poll_interval_n"`
	PollIntervalX          int     `json:"poll_interval_x"`
	LookbackDays           int     `json:"lookback_days"`
	CommentsPerHour        int     `json:"comments_per_hour"`
	MaxConsecutiveFailures int     `json:"max_consecutive_failures"`
	LLMModel               *string `json:"llm_model"`
}

type BotUpdateIn struct {
	Nickname               *string `json:"nickname"`
	Persona                *string `json:"persona"`
	PollIntervalN          *int    `json:"poll_interval_n"`
	PollIntervalX          *int    `json:"poll_interval_x"`
	LookbackDays           *int    `json:"lookback_days"`
	CommentsPerHour        *int    `json:"comments_per_hour"`
	MaxConsecutiveFailures *int    `json:"max_consecutive_failures"`
	LLMModel               *string `json:"llm_model"`
	Enabled                *bool   `json:"enabled"`
	Restore                *bool   `json:"restore"`
}

type BotAdminOut struct {
	ID                     int        `json:"id"`
	UserID                 int        `json:"user_id"`
	Nickname               string     `json:"nickname"`
	Email                  string     `json:"email"`
	AvatarURL              string     `json:"avatar_url"`
	Persona                string     `json:"persona"`
	PollIntervalN          int        `json:"poll_interval_n"`
	PollIntervalX          int        `json:"poll_interval_x"`
	LookbackDays           int        `json:"lookback_days"`
	CommentsPerHour        int        `json:"comments_per_hour"`
	MaxConsecutiveFailures int        `json:"max_consecutive_failures"`
	LLMModel               *string    `json:"llm_model"`
	Enabled                bool       `json:"enabled"`
	AutoPaused             bool       `json:"auto_paused"`
	ConsecutiveFailures    int        `json:"consecutive_failures"`
	LastRunAt              *time.Time `json:"last_run_at"`
	NextRunAt              *time.Time `json:"next_run_at"`
	CreatedAt              time.Time  `json:"created_at"`
}

type BotPublicOut struct {
	ID           int    `json:"id"`
	UserID       int    `json:"user_id"`
	Nickname     string `json:"nickname"`
	AvatarURL    string `json:"avatar_url"`
	PersonaBrief string `json:"persona_brief"`
	IsFriend     bool   `json:"is_friend"`
}

type BotActionOut struct {
	Message string `json:"message"`
}

// ===== Admin Schemas =====

type StatsOut struct {
	UserCount       int `json:"user_count"`
	PostCount       int `json:"post_count"`
	CommentCount    int `json:"comment_count"`
	LikeCount       int `json:"like_count"`
	InviteCount     int `json:"invite_count"`
	UsedInviteCount int `json:"used_invite_count"`
}

type AdminUserOut struct {
	ID          int        `json:"id"`
	Email       string     `json:"email"`
	Nickname    string     `json:"nickname"`
	Role        string     `json:"role"`
	Status      string     `json:"status"`
	CanInvite   bool       `json:"can_invite"`
	AvatarURL   string     `json:"avatar_url"`
	CreatedAt   time.Time  `json:"created_at"`
	LastLoginAt *time.Time `json:"last_login_at"`
}

type AdminUserListOut struct {
	Items    []AdminUserOut `json:"items"`
	Total    int            `json:"total"`
	Page     int            `json:"page"`
	PageSize int            `json:"page_size"`
	HasMore  bool           `json:"has_more"`
}

type AdminUserUpdateIn struct {
	Status    *string `json:"status"`
	CanInvite *bool   `json:"can_invite"`
	Restore   *bool   `json:"restore"`
}

type AdminAuthorOut struct {
	ID            int    `json:"id"`
	Email         string `json:"email"`
	Nickname      string `json:"nickname"`
	AvatarURL     string `json:"avatar_url"`
	IsDeactivated bool   `json:"is_deactivated"`
}

type AdminPostOut struct {
	ID           int            `json:"id"`
	Content      string         `json:"content"`
	Visibility   string         `json:"visibility"`
	Deleted      bool           `json:"deleted"`
	Author       AdminAuthorOut `json:"author"`
	LikeCount    int            `json:"like_count"`
	CommentCount int            `json:"comment_count"`
	CreatedAt    time.Time      `json:"created_at"`
	DeletedAt    *time.Time     `json:"deleted_at"`
}

type AdminPostListOut struct {
	Items    []AdminPostOut `json:"items"`
	Total    int            `json:"total"`
	Page     int            `json:"page"`
	PageSize int            `json:"page_size"`
	HasMore  bool           `json:"has_more"`
}

type AdminCommentOut struct {
	ID             int            `json:"id"`
	PostID         int            `json:"post_id"`
	Content        *string        `json:"content"`
	ImageThumbURL  *string        `json:"image_thumb_url"`
	Deleted        bool           `json:"deleted"`
	Author         AdminAuthorOut `json:"author"`
	LikeCount      int            `json:"like_count"`
	CreatedAt      time.Time      `json:"created_at"`
	DeletedAt      *time.Time     `json:"deleted_at"`
}

type AdminCommentListOut struct {
	Items    []AdminCommentOut `json:"items"`
	Total    int               `json:"total"`
	Page     int               `json:"page"`
	PageSize int               `json:"page_size"`
	HasMore  bool              `json:"has_more"`
}

type AdminInviteOut struct {
	ID        int            `json:"id"`
	Code      string         `json:"code"`
	Status    string         `json:"status"`
	ExpiresAt *time.Time     `json:"expires_at"`
	CreatedAt time.Time      `json:"created_at"`
	UsedByID  *int           `json:"used_by_id"`
	Creator   AdminAuthorOut `json:"creator"`
}

type AdminInviteListOut struct {
	Items    []AdminInviteOut `json:"items"`
	Total    int              `json:"total"`
	Page     int              `json:"page"`
	PageSize int              `json:"page_size"`
	HasMore  bool             `json:"has_more"`
}

type LLMConfigOut struct {
	BaseURL    string `json:"base_url"`
	Model      string `json:"model"`
	Timeout    int    `json:"timeout"`
	MaxTokens  int    `json:"max_tokens"`
	HasAPIKey  bool   `json:"has_api_key"`
}

type LLMConfigUpdateIn struct {
	BaseURL   *string `json:"base_url"`
	APIKey    *string `json:"api_key"`
	Model     *string `json:"model"`
	Timeout   *int    `json:"timeout"`
	MaxTokens *int    `json:"max_tokens"`
}

type LLMConfigTestIn struct {
	BaseURL   *string `json:"base_url"`
	APIKey    *string `json:"api_key"`
	Model     *string `json:"model"`
	Timeout   *int    `json:"timeout"`
	MaxTokens *int    `json:"max_tokens"`
}

type LLMTestOut struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// ===== Media Schemas =====

type MediaUploadOut struct {
	MediaID   int       `json:"media_id"`
	Kind      string    `json:"kind"`
	Format    string    `json:"format"`
	Size      int       `json:"size"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
}

type MediaOut struct {
	ID          int       `json:"id"`
	PostID      *int      `json:"post_id"`
	OwnerID     *int      `json:"owner_id"`
	Kind        string    `json:"kind"`
	Format      string    `json:"format"`
	Size        int       `json:"size"`
	ThumbURL    *string   `json:"thumb_url"`
	LargeURL    *string   `json:"large_url"`
	OriginalURL *string   `json:"original_url"`
	SortOrder   int       `json:"sort_order"`
	CreatedAt   time.Time `json:"created_at"`
}
