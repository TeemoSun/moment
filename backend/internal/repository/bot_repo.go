package repository

import (
	"context"
	"errors"
	"time"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type BotRepo struct {
	pool *pgxpool.Pool
}

func NewBotRepo(pool *pgxpool.Pool) *BotRepo {
	return &BotRepo{pool: pool}
}

func (r *BotRepo) Create(ctx context.Context, b *model.Bot) error {
	query := `
INSERT INTO bots (user_id, persona, poll_interval_n, poll_interval_x, lookback_days, comments_per_hour, max_consecutive_failures, llm_model, enabled, auto_paused, consecutive_failures, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())
RETURNING id, created_at, updated_at
`
	return r.pool.QueryRow(ctx, query,
		b.UserID, b.Persona, b.PollIntervalN, b.PollIntervalX, b.LookbackDays,
		b.CommentsPerHour, b.MaxConsecutiveFailures, b.LLMModel,
		b.Enabled, b.AutoPaused, b.ConsecutiveFailures,
	).Scan(&b.ID, &b.CreatedAt, &b.UpdatedAt)
}

func (r *BotRepo) GetByID(ctx context.Context, id int) (*model.Bot, error) {
	query := `
SELECT id, user_id, persona, poll_interval_n, poll_interval_x, lookback_days, comments_per_hour,
       max_consecutive_failures, llm_model, enabled, auto_paused, consecutive_failures,
       last_run_at, next_run_at, created_at, updated_at
FROM bots
WHERE id = $1
`
	var b model.Bot
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&b.ID, &b.UserID, &b.Persona, &b.PollIntervalN, &b.PollIntervalX, &b.LookbackDays,
		&b.CommentsPerHour, &b.MaxConsecutiveFailures, &b.LLMModel, &b.Enabled,
		&b.AutoPaused, &b.ConsecutiveFailures, &b.LastRunAt, &b.NextRunAt,
		&b.CreatedAt, &b.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &b, nil
}

func (r *BotRepo) GetByUserID(ctx context.Context, userID int) (*model.Bot, error) {
	query := `
SELECT id, user_id, persona, poll_interval_n, poll_interval_x, lookback_days, comments_per_hour,
       max_consecutive_failures, llm_model, enabled, auto_paused, consecutive_failures,
       last_run_at, next_run_at, created_at, updated_at
FROM bots
WHERE user_id = $1
`
	var b model.Bot
	err := r.pool.QueryRow(ctx, query, userID).Scan(
		&b.ID, &b.UserID, &b.Persona, &b.PollIntervalN, &b.PollIntervalX, &b.LookbackDays,
		&b.CommentsPerHour, &b.MaxConsecutiveFailures, &b.LLMModel, &b.Enabled,
		&b.AutoPaused, &b.ConsecutiveFailures, &b.LastRunAt, &b.NextRunAt,
		&b.CreatedAt, &b.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &b, nil
}

func (r *BotRepo) ListAll(ctx context.Context) ([]*model.Bot, error) {
	query := `
SELECT id, user_id, persona, poll_interval_n, poll_interval_x, lookback_days, comments_per_hour,
       max_consecutive_failures, llm_model, enabled, auto_paused, consecutive_failures,
       last_run_at, next_run_at, created_at, updated_at
FROM bots
ORDER BY id ASC
`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var bots []*model.Bot
	for rows.Next() {
		var b model.Bot
		if err := rows.Scan(
			&b.ID, &b.UserID, &b.Persona, &b.PollIntervalN, &b.PollIntervalX, &b.LookbackDays,
			&b.CommentsPerHour, &b.MaxConsecutiveFailures, &b.LLMModel, &b.Enabled,
			&b.AutoPaused, &b.ConsecutiveFailures, &b.LastRunAt, &b.NextRunAt,
			&b.CreatedAt, &b.UpdatedAt,
		); err != nil {
			return nil, err
		}
		bots = append(bots, &b)
	}
	return bots, nil
}

func (r *BotRepo) ListEnabled(ctx context.Context) ([]*model.Bot, error) {
	query := `
SELECT id, user_id, persona, poll_interval_n, poll_interval_x, lookback_days, comments_per_hour,
       max_consecutive_failures, llm_model, enabled, auto_paused, consecutive_failures,
       last_run_at, next_run_at, created_at, updated_at
FROM bots
WHERE enabled = true AND auto_paused = false
ORDER BY id ASC
`
	rows, err := r.pool.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var bots []*model.Bot
	for rows.Next() {
		var b model.Bot
		if err := rows.Scan(
			&b.ID, &b.UserID, &b.Persona, &b.PollIntervalN, &b.PollIntervalX, &b.LookbackDays,
			&b.CommentsPerHour, &b.MaxConsecutiveFailures, &b.LLMModel, &b.Enabled,
			&b.AutoPaused, &b.ConsecutiveFailures, &b.LastRunAt, &b.NextRunAt,
			&b.CreatedAt, &b.UpdatedAt,
		); err != nil {
			return nil, err
		}
		bots = append(bots, &b)
	}
	return bots, nil
}

func (r *BotRepo) Update(ctx context.Context, b *model.Bot) error {
	query := `
UPDATE bots
SET persona = $1, poll_interval_n = $2, poll_interval_x = $3, lookback_days = $4,
    comments_per_hour = $5, max_consecutive_failures = $6, llm_model = $7,
    enabled = $8, auto_paused = $9, consecutive_failures = $10, updated_at = NOW()
WHERE id = $11
`
	_, err := r.pool.Exec(ctx, query,
		b.Persona, b.PollIntervalN, b.PollIntervalX, b.LookbackDays,
		b.CommentsPerHour, b.MaxConsecutiveFailures, b.LLMModel,
		b.Enabled, b.AutoPaused, b.ConsecutiveFailures, b.ID,
	)
	return err
}

func (r *BotRepo) Delete(ctx context.Context, id int) error {
	query := `
UPDATE bots
SET enabled = false, auto_paused = true, updated_at = NOW()
WHERE id = $1
`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *BotRepo) UpdateRunSuccess(ctx context.Context, botID int, nextRun time.Time) error {
	query := `
UPDATE bots
SET consecutive_failures = 0,
    last_run_at = NOW(),
    next_run_at = $1,
    updated_at = NOW()
WHERE id = $2
`
	_, err := r.pool.Exec(ctx, query, nextRun, botID)
	return err
}

func (r *BotRepo) UpdateRunFailure(ctx context.Context, botID, maxFailures int, nextRun time.Time) error {
	query := `
UPDATE bots
SET consecutive_failures = consecutive_failures + 1,
    auto_paused = CASE WHEN consecutive_failures + 1 >= $1 THEN true ELSE auto_paused END,
    last_run_at = NOW(),
    next_run_at = $2,
    updated_at = NOW()
WHERE id = $3
`
	_, err := r.pool.Exec(ctx, query, maxFailures, nextRun, botID)
	return err
}

func (r *BotRepo) AlreadyRepliedPost(ctx context.Context, botUserID, postID int) (bool, error) {
	query := `
SELECT 1 FROM bot_reply_logs
WHERE bot_user_id = $1 AND post_id = $2 AND kind = 'post_reply'
LIMIT 1
`
	var one int
	err := r.pool.QueryRow(ctx, query, botUserID, postID).Scan(&one)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (r *BotRepo) AlreadyRepliedComment(ctx context.Context, botUserID, targetCommentID int) (bool, error) {
	query := `
SELECT 1 FROM bot_reply_logs
WHERE bot_user_id = $1 AND kind = 'comment_reply' AND target_comment_id = $2
LIMIT 1
`
	var one int
	err := r.pool.QueryRow(ctx, query, botUserID, targetCommentID).Scan(&one)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (r *BotRepo) CreateReplyLog(ctx context.Context, log *model.BotReplyLog) error {
	query := `
INSERT INTO bot_reply_logs (bot_user_id, post_id, kind, target_comment_id, reply_comment_id, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
RETURNING id, created_at, updated_at
`
	return r.pool.QueryRow(ctx, query,
		log.BotUserID, log.PostID, log.Kind, log.TargetCommentID, log.ReplyCommentID,
	).Scan(&log.ID, &log.CreatedAt, &log.UpdatedAt)
}

func (r *BotRepo) CountRecentComments(ctx context.Context, botUserID int, since time.Time) (int, error) {
	query := `
SELECT COUNT(*)
FROM comments
WHERE user_id = $1 AND created_at >= $2 AND deleted_at IS NULL
`
	var count int
	err := r.pool.QueryRow(ctx, query, botUserID, since).Scan(&count)
	return count, err
}

func (r *BotRepo) GetBotCommentedPostIDs(ctx context.Context, botUserID int) ([]int, error) {
	query := `
SELECT DISTINCT post_id
FROM bot_reply_logs
WHERE bot_user_id = $1
`
	rows, err := r.pool.Query(ctx, query, botUserID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var pids []int
	for rows.Next() {
		var pid int
		if err := rows.Scan(&pid); err != nil {
			return nil, err
		}
		pids = append(pids, pid)
	}
	return pids, nil
}

func (r *BotRepo) GetBotReplyLogByTarget(ctx context.Context, botUserID int, targetCommentID int) (*model.BotReplyLog, error) {
	query := `
SELECT id, bot_user_id, post_id, kind, target_comment_id, reply_comment_id, created_at, updated_at
FROM bot_reply_logs
WHERE bot_user_id = $1 AND reply_comment_id = $2
`
	var log model.BotReplyLog
	err := r.pool.QueryRow(ctx, query, botUserID, targetCommentID).Scan(
		&log.ID, &log.BotUserID, &log.PostID, &log.Kind, &log.TargetCommentID, &log.ReplyCommentID,
		&log.CreatedAt, &log.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &log, nil
}
