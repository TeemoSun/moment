package repository

import (
	"context"
	"errors"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type LikeRepo struct {
	pool *pgxpool.Pool
}

func NewLikeRepo(pool *pgxpool.Pool) *LikeRepo {
	return &LikeRepo{pool: pool}
}

func (r *LikeRepo) Toggle(ctx context.Context, targetType string, targetID, userID int) (liked bool, count int, err error) {
	// Check if already liked
	var likeID int
	query := `
SELECT id FROM likes
WHERE target_type = $1 AND target_id = $2 AND user_id = $3
`
	err = r.pool.QueryRow(ctx, query, targetType, targetID, userID).Scan(&likeID)
	if err != nil && !errors.Is(err, pgx.ErrNoRows) {
		return false, 0, err
	}

	if likeID > 0 {
		// Unlike
		_, err = r.pool.Exec(ctx, "DELETE FROM likes WHERE id = $1", likeID)
		if err != nil {
			return false, 0, err
		}
		liked = false
	} else {
		// Like (with ON CONFLICT DO NOTHING to prevent race conditions)
		insertQuery := `
INSERT INTO likes (target_type, target_id, user_id, created_at)
VALUES ($1, $2, $3, NOW())
ON CONFLICT (target_type, target_id, user_id) DO NOTHING
`
		ct, err := r.pool.Exec(ctx, insertQuery, targetType, targetID, userID)
		if err != nil {
			return false, 0, err
		}
		if ct.RowsAffected() == 0 {
			// Already inserted by a concurrent request, so toggle deletes it
			_, _ = r.pool.Exec(ctx, "DELETE FROM likes WHERE target_type = $1 AND target_id = $2 AND user_id = $3", targetType, targetID, userID)
			liked = false
		} else {
			liked = true
		}
	}

	// Count likes
	count, err = r.Count(ctx, targetType, targetID)
	return liked, count, err
}

func (r *LikeRepo) Unlike(ctx context.Context, targetType string, targetID, userID int) (count int, err error) {
	deleteQuery := `
DELETE FROM likes
WHERE target_type = $1 AND target_id = $2 AND user_id = $3
`
	if _, err := r.pool.Exec(ctx, deleteQuery, targetType, targetID, userID); err != nil {
		return 0, err
	}
	return r.Count(ctx, targetType, targetID)
}

func (r *LikeRepo) Count(ctx context.Context, targetType string, targetID int) (int, error) {
	var count int
	query := `
SELECT COUNT(*)
FROM likes
WHERE target_type = $1 AND target_id = $2
`
	err := r.pool.QueryRow(ctx, query, targetType, targetID).Scan(&count)
	return count, err
}

func (r *LikeRepo) IsLikedBy(ctx context.Context, targetType string, targetID, userID int) (bool, error) {
	query := `
SELECT 1
FROM likes
WHERE target_type = $1 AND target_id = $2 AND user_id = $3
`
	var one int
	err := r.pool.QueryRow(ctx, query, targetType, targetID, userID).Scan(&one)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (r *LikeRepo) CountAll(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, "SELECT COUNT(*) FROM likes").Scan(&count)
	return count, err
}
