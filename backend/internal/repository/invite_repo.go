package repository

import (
	"context"
	"errors"
	"time"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type InviteRepo struct {
	pool *pgxpool.Pool
}

func NewInviteRepo(pool *pgxpool.Pool) *InviteRepo {
	return &InviteRepo{pool: pool}
}

func (r *InviteRepo) SyncExpired(ctx context.Context, creatorID int) error {
	query := `
UPDATE invite_codes
SET status = 'expired'
WHERE creator_id = $1 AND status = 'active' AND expires_at IS NOT NULL AND expires_at <= NOW()
`
	_, err := r.pool.Exec(ctx, query, creatorID)
	return err
}

func (r *InviteRepo) Create(ctx context.Context, inv *model.InviteCode) error {
	query := `
INSERT INTO invite_codes (code, creator_id, status, expires_at, created_at)
VALUES ($1, $2, 'active', $3, NOW())
RETURNING id, created_at
`
	return r.pool.QueryRow(ctx, query, inv.Code, inv.CreatorID, inv.ExpiresAt).Scan(&inv.ID, &inv.CreatedAt)
}

func (r *InviteRepo) GetByID(ctx context.Context, id int) (*model.InviteCode, error) {
	query := `
SELECT id, code, creator_id, status, expires_at, used_by_id, created_at
FROM invite_codes
WHERE id = $1
`
	var inv model.InviteCode
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&inv.ID, &inv.Code, &inv.CreatorID, &inv.Status, &inv.ExpiresAt, &inv.UsedByID, &inv.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &inv, nil
}

func (r *InviteRepo) GetByCode(ctx context.Context, code string) (*model.InviteCode, error) {
	query := `
SELECT id, code, creator_id, status, expires_at, used_by_id, created_at
FROM invite_codes
WHERE code = $1
`
	var inv model.InviteCode
	err := r.pool.QueryRow(ctx, query, code).Scan(
		&inv.ID, &inv.Code, &inv.CreatorID, &inv.Status, &inv.ExpiresAt, &inv.UsedByID, &inv.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &inv, nil
}

func (r *InviteRepo) GetActiveByCreator(ctx context.Context, creatorID int) (*model.InviteCode, error) {
	query := `
SELECT id, code, creator_id, status, expires_at, used_by_id, created_at
FROM invite_codes
WHERE creator_id = $1 AND status = 'active'
`
	var inv model.InviteCode
	err := r.pool.QueryRow(ctx, query, creatorID).Scan(
		&inv.ID, &inv.Code, &inv.CreatorID, &inv.Status, &inv.ExpiresAt, &inv.UsedByID, &inv.CreatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &inv, nil
}

func (r *InviteRepo) ListByCreator(ctx context.Context, creatorID int) ([]*model.InviteCode, error) {
	query := `
SELECT id, code, creator_id, status, expires_at, used_by_id, created_at
FROM invite_codes
WHERE creator_id = $1
ORDER BY created_at DESC
`
	rows, err := r.pool.Query(ctx, query, creatorID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*model.InviteCode
	for rows.Next() {
		var inv model.InviteCode
		if err := rows.Scan(
			&inv.ID, &inv.Code, &inv.CreatorID, &inv.Status, &inv.ExpiresAt, &inv.UsedByID, &inv.CreatedAt,
		); err != nil {
			return nil, err
		}
		list = append(list, &inv)
	}
	return list, nil
}

func (r *InviteRepo) Revoke(ctx context.Context, id int) error {
	query := `UPDATE invite_codes SET status = 'revoked' WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *InviteRepo) MarkUsed(ctx context.Context, id, usedByID int) error {
	query := `UPDATE invite_codes SET status = 'used', used_by_id = $1 WHERE id = $2`
	_, err := r.pool.Exec(ctx, query, usedByID, id)
	return err
}

func (r *InviteRepo) Renew(ctx context.Context, id int, expiresAt *time.Time) error {
	query := `UPDATE invite_codes SET expires_at = $1 WHERE id = $2`
	_, err := r.pool.Exec(ctx, query, expiresAt, id)
	return err
}

func (r *InviteRepo) ListAdmin(ctx context.Context, offset, limit int) ([]*model.InviteCode, int, error) {
	var total int
	if err := r.pool.QueryRow(ctx, "SELECT COUNT(*) FROM invite_codes").Scan(&total); err != nil {
		return nil, 0, err
	}

	query := `
SELECT id, code, creator_id, status, expires_at, used_by_id, created_at
FROM invite_codes
ORDER BY created_at DESC
OFFSET $1 LIMIT $2
`
	rows, err := r.pool.Query(ctx, query, offset, limit)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var list []*model.InviteCode
	for rows.Next() {
		var inv model.InviteCode
		if err := rows.Scan(
			&inv.ID, &inv.Code, &inv.CreatorID, &inv.Status, &inv.ExpiresAt, &inv.UsedByID, &inv.CreatedAt,
		); err != nil {
			return nil, 0, err
		}
		list = append(list, &inv)
	}
	return list, total, nil
}

func (r *InviteRepo) CountAll(ctx context.Context) (total int, used int, err error) {
	query := `
SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'used')
FROM invite_codes
`
	err = r.pool.QueryRow(ctx, query).Scan(&total, &used)
	return total, used, err
}
