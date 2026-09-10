package repository

import (
	"context"
	"errors"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type MediaRepo struct {
	pool *pgxpool.Pool
}

func NewMediaRepo(pool *pgxpool.Pool) *MediaRepo {
	return &MediaRepo{pool: pool}
}

func (r *MediaRepo) CreateMedia(ctx context.Context, m *model.PostMedia) error {
	query := `
INSERT INTO post_media (post_id, owner_id, file_path, thumb_path, large_path, filename, size, mime, format, kind, sort_order, created_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
RETURNING id, created_at
`
	return r.pool.QueryRow(ctx, query,
		m.PostID, m.OwnerID, m.FilePath, m.ThumbPath, m.LargePath,
		m.Filename, m.Size, m.Mime, m.Format, m.Kind, m.SortOrder,
	).Scan(&m.ID, &m.CreatedAt)
}

func (r *MediaRepo) GetMediaByID(ctx context.Context, id int) (*model.PostMedia, error) {
	query := `
SELECT id, post_id, owner_id, file_path, thumb_path, large_path, filename, size, mime, format, kind, sort_order, created_at
FROM post_media
WHERE id = $1
`
	var m model.PostMedia
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&m.ID, &m.PostID, &m.OwnerID, &m.FilePath, &m.ThumbPath, &m.LargePath,
		&m.Filename, &m.Size, &m.Mime, &m.Format, &m.Kind, &m.SortOrder, &m.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &m, nil
}

func (r *MediaRepo) GetPostMedia(ctx context.Context, postID, mediaID int) (*model.PostMedia, error) {
	query := `
SELECT id, post_id, owner_id, file_path, thumb_path, large_path, filename, size, mime, format, kind, sort_order, created_at
FROM post_media
WHERE id = $1 AND post_id = $2
`
	var m model.PostMedia
	err := r.pool.QueryRow(ctx, query, mediaID, postID).Scan(
		&m.ID, &m.PostID, &m.OwnerID, &m.FilePath, &m.ThumbPath, &m.LargePath,
		&m.Filename, &m.Size, &m.Mime, &m.Format, &m.Kind, &m.SortOrder, &m.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &m, nil
}

func (r *MediaRepo) UpdateMediaPaths(ctx context.Context, id int, thumbPath, largePath *string) error {
	query := `
UPDATE post_media
SET thumb_path = $1, large_path = $2
WHERE id = $3
`
	_, err := r.pool.Exec(ctx, query, thumbPath, largePath, id)
	return err
}

func (r *MediaRepo) DeleteMedia(ctx context.Context, id int) error {
	query := `DELETE FROM post_media WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *MediaRepo) CreateFileMetadata(ctx context.Context, f *model.FileMetadata) error {
	query := `
INSERT INTO file_metadata (storage_path, original_name, filename, size, mime, format, kind, owner_id, created_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
ON CONFLICT (storage_path) DO NOTHING
RETURNING id, created_at
`
	err := r.pool.QueryRow(ctx, query,
		f.StoragePath, f.OriginalName, f.Filename, f.Size, f.Mime, f.Format, f.Kind, f.OwnerID,
	).Scan(&f.ID, &f.CreatedAt)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil
	}
	return err
}
