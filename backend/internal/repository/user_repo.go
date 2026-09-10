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

type UserRepo struct {
	pool *pgxpool.Pool
}

func NewUserRepo(pool *pgxpool.Pool) *UserRepo {
	return &UserRepo{pool: pool}
}

func (r *UserRepo) GetByID(ctx context.Context, id int) (*model.User, error) {
	query := `
SELECT id, email, password_hash, nickname, signature, avatar_path, role, status,
       can_invite, failed_login_count, locked_until, last_login_at, token_version, created_at, updated_at
FROM users
WHERE id = $1
`
	var u model.User
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&u.ID, &u.Email, &u.PasswordHash, &u.Nickname, &u.Signature, &u.AvatarPath,
		&u.Role, &u.Status, &u.CanInvite, &u.FailedLoginCount, &u.LockedUntil,
		&u.LastLoginAt, &u.TokenVersion, &u.CreatedAt, &u.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get user by id: %w", err)
	}
	return &u, nil
}

func (r *UserRepo) GetByEmail(ctx context.Context, email string) (*model.User, error) {
	query := `
SELECT id, email, password_hash, nickname, signature, avatar_path, role, status,
       can_invite, failed_login_count, locked_until, last_login_at, token_version, created_at, updated_at
FROM users
WHERE email = $1
`
	var u model.User
	err := r.pool.QueryRow(ctx, query, email).Scan(
		&u.ID, &u.Email, &u.PasswordHash, &u.Nickname, &u.Signature, &u.AvatarPath,
		&u.Role, &u.Status, &u.CanInvite, &u.FailedLoginCount, &u.LockedUntil,
		&u.LastLoginAt, &u.TokenVersion, &u.CreatedAt, &u.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get user by email: %w", err)
	}
	return &u, nil
}

func (r *UserRepo) GetByIDs(ctx context.Context, ids []int) (map[int]*model.User, error) {
	result := make(map[int]*model.User)
	if len(ids) == 0 {
		return result, nil
	}
	query := `
SELECT id, email, password_hash, nickname, signature, avatar_path, role, status,
       can_invite, failed_login_count, locked_until, last_login_at, token_version, created_at, updated_at
FROM users
WHERE id = ANY($1)
`
	rows, err := r.pool.Query(ctx, query, ids)
	if err != nil {
		return nil, fmt.Errorf("failed to batch get users: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var u model.User
		if err := rows.Scan(
			&u.ID, &u.Email, &u.PasswordHash, &u.Nickname, &u.Signature, &u.AvatarPath,
			&u.Role, &u.Status, &u.CanInvite, &u.FailedLoginCount, &u.LockedUntil,
			&u.LastLoginAt, &u.TokenVersion, &u.CreatedAt, &u.UpdatedAt,
		); err != nil {
			return nil, err
		}
		result[u.ID] = &u
	}
	return result, nil
}

func (r *UserRepo) Create(ctx context.Context, u *model.User) error {
	query := `
INSERT INTO users (email, password_hash, nickname, signature, avatar_path, role, status, can_invite, failed_login_count, token_version, created_at, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
RETURNING id, created_at, updated_at
`
	return r.pool.QueryRow(ctx, query,
		u.Email, u.PasswordHash, u.Nickname, u.Signature, u.AvatarPath,
		u.Role, u.Status, u.CanInvite, u.FailedLoginCount, u.TokenVersion,
	).Scan(&u.ID, &u.CreatedAt, &u.UpdatedAt)
}

func (r *UserRepo) Update(ctx context.Context, u *model.User) error {
	query := `
UPDATE users
SET email = $1, nickname = $2, signature = $3, avatar_path = $4, role = $5,
    status = $6, can_invite = $7, failed_login_count = $8, locked_until = $9,
    last_login_at = $10, token_version = $11, updated_at = NOW()
WHERE id = $12
`
	_, err := r.pool.Exec(ctx, query,
		u.Email, u.Nickname, u.Signature, u.AvatarPath, u.Role,
		u.Status, u.CanInvite, u.FailedLoginCount, u.LockedUntil,
		u.LastLoginAt, u.TokenVersion, u.ID,
	)
	return err
}

func (r *UserRepo) UpdateProfile(ctx context.Context, id int, nickname, signature *string) error {
	query := `
UPDATE users
SET nickname = COALESCE($1, nickname),
    signature = COALESCE($2, signature),
    updated_at = NOW()
WHERE id = $3
`
	_, err := r.pool.Exec(ctx, query, nickname, signature, id)
	return err
}

func (r *UserRepo) UpdateAvatar(ctx context.Context, id int, avatarPath string) error {
	query := `
UPDATE users
SET avatar_path = $1, updated_at = NOW()
WHERE id = $2
`
	_, err := r.pool.Exec(ctx, query, avatarPath, id)
	return err
}

func (r *UserRepo) UpdatePasswordAndBumpToken(ctx context.Context, id int, passwordHash string) error {
	query := `
UPDATE users
SET password_hash = $1,
    token_version = token_version + 1,
    updated_at = NOW()
WHERE id = $2
`
	_, err := r.pool.Exec(ctx, query, passwordHash, id)
	return err
}

func (r *UserRepo) RecordLoginSuccess(ctx context.Context, id int) error {
	query := `
UPDATE users
SET failed_login_count = 0,
    locked_until = NULL,
    last_login_at = NOW(),
    updated_at = NOW()
WHERE id = $1
`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *UserRepo) RecordLoginFailure(ctx context.Context, id int) (failedCount int, lockedUntil *time.Time, err error) {
	// Increment failed_login_count
	var count int
	query := `
UPDATE users
SET failed_login_count = failed_login_count + 1,
    updated_at = NOW()
WHERE id = $1
RETURNING failed_login_count
`
	if err := r.pool.QueryRow(ctx, query, id).Scan(&count); err != nil {
		return 0, nil, err
	}

	if count >= 5 {
		lockTime := time.Now().UTC().Add(15 * time.Minute)
		lockQuery := `
UPDATE users
SET locked_until = $1
WHERE id = $2
`
		if _, err := r.pool.Exec(ctx, lockQuery, lockTime, id); err != nil {
			return count, nil, err
		}
		return count, &lockTime, nil
	}

	return count, nil, nil
}

func (r *UserRepo) Deactivate(ctx context.Context, id int) error {
	query := `
UPDATE users
SET status = 'deactivated', updated_at = NOW()
WHERE id = $1
`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *UserRepo) ListAdmin(ctx context.Context, search string, offset, limit int) ([]*model.User, int, error) {
	countQuery := `SELECT COUNT(*) FROM users`
	selectQuery := `
SELECT id, email, password_hash, nickname, signature, avatar_path, role, status,
       can_invite, failed_login_count, locked_until, last_login_at, token_version, created_at, updated_at
FROM users
`
	var total int
	var rows pgx.Rows
	var err error

	if search != "" {
		pattern := "%" + search + "%"
		countQuery += ` WHERE email ILIKE $1 OR nickname ILIKE $1`
		selectQuery += ` WHERE email ILIKE $1 OR nickname ILIKE $1 ORDER BY id ASC OFFSET $2 LIMIT $3`
		if err := r.pool.QueryRow(ctx, countQuery, pattern).Scan(&total); err != nil {
			return nil, 0, err
		}
		rows, err = r.pool.Query(ctx, selectQuery, pattern, offset, limit)
	} else {
		selectQuery += ` ORDER BY id ASC OFFSET $1 LIMIT $2`
		if err := r.pool.QueryRow(ctx, countQuery).Scan(&total); err != nil {
			return nil, 0, err
		}
		rows, err = r.pool.Query(ctx, selectQuery, offset, limit)
	}
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var users []*model.User
	for rows.Next() {
		var u model.User
		if err := rows.Scan(
			&u.ID, &u.Email, &u.PasswordHash, &u.Nickname, &u.Signature, &u.AvatarPath,
			&u.Role, &u.Status, &u.CanInvite, &u.FailedLoginCount, &u.LockedUntil,
			&u.LastLoginAt, &u.TokenVersion, &u.CreatedAt, &u.UpdatedAt,
		); err != nil {
			return nil, 0, err
		}
		users = append(users, &u)
	}
	return users, total, nil
}

func (r *UserRepo) CountAll(ctx context.Context) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx, "SELECT COUNT(*) FROM users").Scan(&count)
	return count, err
}
