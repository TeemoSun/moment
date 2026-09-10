package repository

import (
	"context"
	"errors"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type CommentRepo struct {
	pool *pgxpool.Pool
}

func NewCommentRepo(pool *pgxpool.Pool) *CommentRepo {
	return &CommentRepo{pool: pool}
}

func (r *CommentRepo) Create(ctx context.Context, c *model.Comment) error {
	query := `
INSERT INTO comments (post_id, user_id, parent_comment_id, reply_to_user_id, content, image_path, image_thumb_path, image_large_path, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
RETURNING id, created_at, updated_at
`
	return r.pool.QueryRow(ctx, query,
		c.PostID, c.UserID, c.ParentCommentID, c.ReplyToUserID,
		c.Content, c.ImagePath, c.ImageThumbPath, c.ImageLargePath,
	).Scan(&c.ID, &c.CreatedAt, &c.UpdatedAt)
}

func (r *CommentRepo) GetByID(ctx context.Context, id int) (*model.Comment, error) {
	query := `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content,
       image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
WHERE id = $1 AND deleted_at IS NULL
`
	var c model.Comment
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&c.ID, &c.PostID, &c.UserID, &c.ParentCommentID, &c.ReplyToUserID,
		&c.Content, &c.ImagePath, &c.ImageThumbPath, &c.ImageLargePath,
		&c.DeletedAt, &c.CreatedAt, &c.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &c, nil
}

func (r *CommentRepo) GetByIDIncludeDeleted(ctx context.Context, id int) (*model.Comment, error) {
	query := `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content,
       image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
WHERE id = $1
`
	var c model.Comment
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&c.ID, &c.PostID, &c.UserID, &c.ParentCommentID, &c.ReplyToUserID,
		&c.Content, &c.ImagePath, &c.ImageThumbPath, &c.ImageLargePath,
		&c.DeletedAt, &c.CreatedAt, &c.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &c, nil
}

func (r *CommentRepo) SoftDelete(ctx context.Context, id int) error {
	query := `
UPDATE comments
SET deleted_at = NOW(), updated_at = NOW()
WHERE id = $1 AND deleted_at IS NULL
`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *CommentRepo) ListByPost(ctx context.Context, postID int, allowedUserIDs []int, offset, limit int) ([]*model.Comment, int, error) {
	var countQuery, selectQuery string
	var countArgs, selectArgs []any

	if len(allowedUserIDs) > 0 {
		countQuery = `
SELECT COUNT(*) FROM comments
WHERE post_id = $1 AND deleted_at IS NULL AND user_id = ANY($2)
`
		countArgs = []any{postID, allowedUserIDs}

		selectQuery = `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content,
       image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
WHERE post_id = $1 AND deleted_at IS NULL AND user_id = ANY($2)
ORDER BY created_at ASC, id ASC
OFFSET $3 LIMIT $4
`
		selectArgs = []any{postID, allowedUserIDs, offset, limit}
	} else {
		countQuery = `
SELECT COUNT(*) FROM comments
WHERE post_id = $1 AND deleted_at IS NULL
`
		countArgs = []any{postID}

		selectQuery = `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content,
       image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
WHERE post_id = $1 AND deleted_at IS NULL
ORDER BY created_at ASC, id ASC
OFFSET $2 LIMIT $3
`
		selectArgs = []any{postID, offset, limit}
	}

	var total int
	if err := r.pool.QueryRow(ctx, countQuery, countArgs...).Scan(&total); err != nil {
		return nil, 0, err
	}

	rows, err := r.pool.Query(ctx, selectQuery, selectArgs...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var comments []*model.Comment
	for rows.Next() {
		var c model.Comment
		if err := rows.Scan(
			&c.ID, &c.PostID, &c.UserID, &c.ParentCommentID, &c.ReplyToUserID,
			&c.Content, &c.ImagePath, &c.ImageThumbPath, &c.ImageLargePath,
			&c.DeletedAt, &c.CreatedAt, &c.UpdatedAt,
		); err != nil {
			return nil, 0, err
		}
		comments = append(comments, &c)
	}
	return comments, total, nil
}

func (r *CommentRepo) ListAdmin(ctx context.Context, offset, limit int) ([]*model.Comment, int, error) {
	var total int
	if err := r.pool.QueryRow(ctx, "SELECT COUNT(*) FROM comments").Scan(&total); err != nil {
		return nil, 0, err
	}

	query := `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content,
       image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
ORDER BY created_at DESC, id DESC
OFFSET $1 LIMIT $2
`
	rows, err := r.pool.Query(ctx, query, offset, limit)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var comments []*model.Comment
	for rows.Next() {
		var c model.Comment
		if err := rows.Scan(
			&c.ID, &c.PostID, &c.UserID, &c.ParentCommentID, &c.ReplyToUserID,
			&c.Content, &c.ImagePath, &c.ImageThumbPath, &c.ImageLargePath,
			&c.DeletedAt, &c.CreatedAt, &c.UpdatedAt,
		); err != nil {
			return nil, 0, err
		}
		comments = append(comments, &c)
	}
	return comments, total, nil
}

func (r *CommentRepo) CountActive(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, "SELECT COUNT(*) FROM comments WHERE deleted_at IS NULL").Scan(&count)
	return count, err
}

func (r *CommentRepo) BatchPreloadParents(ctx context.Context, parentIDs []int) (map[int]*model.Comment, error) {
	result := make(map[int]*model.Comment)
	if len(parentIDs) == 0 {
		return result, nil
	}
	query := `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content,
       image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
WHERE id = ANY($1) AND deleted_at IS NULL
`
	rows, err := r.pool.Query(ctx, query, parentIDs)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var c model.Comment
		if err := rows.Scan(
			&c.ID, &c.PostID, &c.UserID, &c.ParentCommentID, &c.ReplyToUserID,
			&c.Content, &c.ImagePath, &c.ImageThumbPath, &c.ImageLargePath,
			&c.DeletedAt, &c.CreatedAt, &c.UpdatedAt,
		); err != nil {
			return nil, err
		}
		result[c.ID] = &c
	}
	return result, nil
}

func (r *CommentRepo) BatchPreloadLikeCounts(ctx context.Context, commentIDs []int) (map[int]int, error) {
	result := make(map[int]int)
	if len(commentIDs) == 0 {
		return result, nil
	}
	query := `
SELECT target_id, COUNT(*)
FROM likes
WHERE target_type = 'comment' AND target_id = ANY($1)
GROUP BY target_id
`
	rows, err := r.pool.Query(ctx, query, commentIDs)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var targetID, count int
		if err := rows.Scan(&targetID, &count); err != nil {
			return nil, err
		}
		result[targetID] = count
	}
	return result, nil
}

func (r *CommentRepo) BatchPreloadLikedByMe(ctx context.Context, commentIDs []int, viewerID int) (map[int]bool, error) {
	result := make(map[int]bool)
	if len(commentIDs) == 0 {
		return result, nil
	}
	query := `
SELECT target_id
FROM likes
WHERE target_type = 'comment' AND target_id = ANY($1) AND user_id = $2
`
	rows, err := r.pool.Query(ctx, query, commentIDs, viewerID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var targetID int
		if err := rows.Scan(&targetID); err != nil {
			return nil, err
		}
		result[targetID] = true
	}
	return result, nil
}
