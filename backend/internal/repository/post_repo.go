package repository

import (
	"context"
	"errors"
	"fmt"
	"time"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PostRepo struct {
	pool *pgxpool.Pool
}

func NewPostRepo(pool *pgxpool.Pool) *PostRepo {
	return &PostRepo{pool: pool}
}

func (r *PostRepo) Create(ctx context.Context, p *model.Post, mediaIDs []int) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer tx.Rollback(ctx)

	query := `
INSERT INTO posts (user_id, content, visibility, created_at, updated_at)
VALUES ($1, $2, $3, NOW(), NOW())
RETURNING id, created_at, updated_at
`
	if err := tx.QueryRow(ctx, query, p.UserID, p.Content, p.Visibility).Scan(&p.ID, &p.CreatedAt, &p.UpdatedAt); err != nil {
		return err
	}

	if len(mediaIDs) > 0 {
		for i, mid := range mediaIDs {
			mediaQuery := `
UPDATE post_media
SET post_id = $1, sort_order = $2
WHERE id = $3 AND owner_id = $4 AND post_id IS NULL
`
			ct, err := tx.Exec(ctx, mediaQuery, p.ID, i, mid, p.UserID)
			if err != nil {
				return err
			}
			if ct.RowsAffected() == 0 {
				return errors.New("media not owned or already used")
			}
		}
	}

	return tx.Commit(ctx)
}

func (r *PostRepo) GetByID(ctx context.Context, id int) (*model.Post, error) {
	query := `
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE id = $1 AND deleted_at IS NULL
`
	var p model.Post
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&p.ID, &p.UserID, &p.Content, &p.Visibility, &p.DeletedAt, &p.CreatedAt, &p.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &p, nil
}

func (r *PostRepo) GetByIDIncludeDeleted(ctx context.Context, id int) (*model.Post, error) {
	query := `
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE id = $1
`
	var p model.Post
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&p.ID, &p.UserID, &p.Content, &p.Visibility, &p.DeletedAt, &p.CreatedAt, &p.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &p, nil
}

func (r *PostRepo) SoftDelete(ctx context.Context, id int) error {
	query := `
UPDATE posts
SET deleted_at = NOW(), updated_at = NOW()
WHERE id = $1 AND deleted_at IS NULL
`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

// Feed queries visible posts for viewer with cursor pagination.
// Visible if: public OR viewer is author OR author is a friend.
func (r *PostRepo) Feed(ctx context.Context, viewerID int, friendIDs []int, cursorTime *time.Time, cursorID *int, limit int) ([]*model.Post, error) {
	// Filter logic:
	// deleted_at IS NULL AND (visibility = 'public' OR user_id = $1 OR user_id = ANY($2))
	// plus cursor filter if set
	var query string
	var args []any

	baseCond := `
deleted_at IS NULL AND (
    visibility = 'public' 
    OR user_id = $1 
    OR user_id = ANY($2)
)
`
	args = append(args, viewerID, friendIDs)

	if cursorTime != nil && cursorID != nil {
		cursorCond := fmt.Sprintf(`
AND (
    created_at < $%d 
    OR (created_at >= $%d AND created_at < $%d + INTERVAL '1 second' AND id < $%d)
)
`, len(args)+1, len(args)+1, len(args)+1, len(args)+2)
		query = fmt.Sprintf(`
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE %s %s
ORDER BY created_at DESC, id DESC
LIMIT $%d
`, baseCond, cursorCond, len(args)+3)
		args = append(args, *cursorTime, *cursorID, limit)
	} else {
		query = fmt.Sprintf(`
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE %s
ORDER BY created_at DESC, id DESC
LIMIT $%d
`, baseCond, len(args)+1)
		args = append(args, limit)
	}

	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("feed query failed: %w", err)
	}
	defer rows.Close()

	var posts []*model.Post
	for rows.Next() {
		var p model.Post
		if err := rows.Scan(
			&p.ID, &p.UserID, &p.Content, &p.Visibility, &p.DeletedAt, &p.CreatedAt, &p.UpdatedAt,
		); err != nil {
			return nil, err
		}
		posts = append(posts, &p)
	}
	return posts, nil
}

// UserPosts queries posts authored by target user.
// If canViewFriends is false, only public posts are returned.
func (r *PostRepo) UserPosts(ctx context.Context, targetUserID int, canViewFriends bool, cursorTime *time.Time, cursorID *int, limit int) ([]*model.Post, error) {
	var query string
	var args []any

	baseCond := `deleted_at IS NULL AND user_id = $1`
	args = append(args, targetUserID)

	if !canViewFriends {
		baseCond += ` AND visibility = 'public'`
	}

	if cursorTime != nil && cursorID != nil {
		cursorCond := fmt.Sprintf(`
AND (
    created_at < $%d 
    OR (created_at >= $%d AND created_at < $%d + INTERVAL '1 second' AND id < $%d)
)
`, len(args)+1, len(args)+1, len(args)+1, len(args)+2)
		query = fmt.Sprintf(`
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE %s %s
ORDER BY created_at DESC, id DESC
LIMIT $%d
`, baseCond, cursorCond, len(args)+3)
		args = append(args, *cursorTime, *cursorID, limit)
	} else {
		query = fmt.Sprintf(`
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE %s
ORDER BY created_at DESC, id DESC
LIMIT $%d
`, baseCond, len(args)+1)
		args = append(args, limit)
	}

	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("user posts query failed: %w", err)
	}
	defer rows.Close()

	var posts []*model.Post
	for rows.Next() {
		var p model.Post
		if err := rows.Scan(
			&p.ID, &p.UserID, &p.Content, &p.Visibility, &p.DeletedAt, &p.CreatedAt, &p.UpdatedAt,
		); err != nil {
			return nil, err
		}
		posts = append(posts, &p)
	}
	return posts, nil
}

func (r *PostRepo) ListAdmin(ctx context.Context, userID *int, visibility *string, offset, limit int) ([]*model.Post, int, error) {
	baseCond := "1=1"
	var args []any

	if userID != nil {
		args = append(args, *userID)
		baseCond += fmt.Sprintf(" AND user_id = $%d", len(args))
	}
	if visibility != nil {
		args = append(args, *visibility)
		baseCond += fmt.Sprintf(" AND visibility = $%d", len(args))
	}

	countQuery := fmt.Sprintf("SELECT COUNT(*) FROM posts WHERE %s", baseCond)
	var total int
	if err := r.pool.QueryRow(ctx, countQuery, args...).Scan(&total); err != nil {
		return nil, 0, err
	}

	selectQuery := fmt.Sprintf(`
SELECT id, user_id, content, visibility, deleted_at, created_at, updated_at
FROM posts
WHERE %s
ORDER BY created_at DESC, id DESC
OFFSET $%d LIMIT $%d
`, baseCond, len(args)+1, len(args)+2)

	queryArgs := append(args, offset, limit)
	rows, err := r.pool.Query(ctx, selectQuery, queryArgs...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var posts []*model.Post
	for rows.Next() {
		var p model.Post
		if err := rows.Scan(
			&p.ID, &p.UserID, &p.Content, &p.Visibility, &p.DeletedAt, &p.CreatedAt, &p.UpdatedAt,
		); err != nil {
			return nil, 0, err
		}
		posts = append(posts, &p)
	}
	return posts, total, nil
}

func (r *PostRepo) CountActive(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, "SELECT COUNT(*) FROM posts WHERE deleted_at IS NULL").Scan(&count)
	return count, err
}

// ===== Batch Preload Methods to eliminate N+1 =====

func (r *PostRepo) BatchPreloadMedia(ctx context.Context, postIDs []int) (map[int][]*model.PostMedia, error) {
	result := make(map[int][]*model.PostMedia)
	if len(postIDs) == 0 {
		return result, nil
	}
	query := `
SELECT id, post_id, owner_id, file_path, thumb_path, large_path, filename, size, mime, format, kind, sort_order, created_at
FROM post_media
WHERE post_id = ANY($1)
ORDER BY sort_order ASC, id ASC
`
	rows, err := r.pool.Query(ctx, query, postIDs)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var m model.PostMedia
		if err := rows.Scan(
			&m.ID, &m.PostID, &m.OwnerID, &m.FilePath, &m.ThumbPath, &m.LargePath,
			&m.Filename, &m.Size, &m.Mime, &m.Format, &m.Kind, &m.SortOrder, &m.CreatedAt,
		); err != nil {
			return nil, err
		}
		if m.PostID != nil {
			result[*m.PostID] = append(result[*m.PostID], &m)
		}
	}
	return result, nil
}

func (r *PostRepo) BatchPreloadLikeCounts(ctx context.Context, postIDs []int) (map[int]int, error) {
	result := make(map[int]int)
	if len(postIDs) == 0 {
		return result, nil
	}
	query := `
SELECT target_id, COUNT(*)
FROM likes
WHERE target_type = 'post' AND target_id = ANY($1)
GROUP BY target_id
`
	rows, err := r.pool.Query(ctx, query, postIDs)
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

func (r *PostRepo) BatchPreloadLikedByMe(ctx context.Context, postIDs []int, viewerID int) (map[int]bool, error) {
	result := make(map[int]bool)
	if len(postIDs) == 0 {
		return result, nil
	}
	query := `
SELECT target_id
FROM likes
WHERE target_type = 'post' AND target_id = ANY($1) AND user_id = $2
`
	rows, err := r.pool.Query(ctx, query, postIDs, viewerID)
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

func (r *PostRepo) BatchPreloadCommentCounts(ctx context.Context, postIDs []int) (map[int]int, error) {
	result := make(map[int]int)
	if len(postIDs) == 0 {
		return result, nil
	}
	query := `
SELECT post_id, COUNT(*)
FROM comments
WHERE post_id = ANY($1) AND deleted_at IS NULL
GROUP BY post_id
`
	rows, err := r.pool.Query(ctx, query, postIDs)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var postID, count int
		if err := rows.Scan(&postID, &count); err != nil {
			return nil, err
		}
		result[postID] = count
	}
	return result, nil
}

// BatchPreloadPreviewComments preloads preview comments for each post
func (r *PostRepo) BatchPreloadPreviewComments(ctx context.Context, postIDs []int) (map[int][]*model.Comment, error) {
	result := make(map[int][]*model.Comment)
	if len(postIDs) == 0 {
		return result, nil
	}
	query := `
SELECT id, post_id, user_id, parent_comment_id, reply_to_user_id, content, image_path, image_thumb_path, image_large_path, deleted_at, created_at, updated_at
FROM comments
WHERE post_id = ANY($1) AND deleted_at IS NULL
ORDER BY created_at ASC, id ASC
`
	rows, err := r.pool.Query(ctx, query, postIDs)
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
		result[c.PostID] = append(result[c.PostID], &c)
	}
	return result, nil
}

// BatchPreloadLikeAuthors preloads like records for each post ordered by created_at DESC
func (r *PostRepo) BatchPreloadLikeAuthors(ctx context.Context, postIDs []int) (map[int][]*model.Like, error) {
	result := make(map[int][]*model.Like)
	if len(postIDs) == 0 {
		return result, nil
	}
	query := `
SELECT id, target_type, target_id, user_id, created_at
FROM likes
WHERE target_type = 'post' AND target_id = ANY($1)
ORDER BY created_at DESC, id DESC
`
	rows, err := r.pool.Query(ctx, query, postIDs)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var l model.Like
		if err := rows.Scan(&l.ID, &l.TargetType, &l.TargetID, &l.UserID, &l.CreatedAt); err != nil {
			return nil, err
		}
		result[l.TargetID] = append(result[l.TargetID], &l)
	}
	return result, nil
}
