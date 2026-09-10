package repository

import (
	"context"
	"errors"
	"fmt"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type RSARepo struct {
	pool *pgxpool.Pool
}

func NewRSARepo(pool *pgxpool.Pool) *RSARepo {
	return &RSARepo{pool: pool}
}

func (r *RSARepo) GetFirst(ctx context.Context) (*model.RSAKey, error) {
	query := `
SELECT id, public_key_pem, private_key_pem, created_at
FROM rsa_keys
ORDER BY id ASC
LIMIT 1
`
	var k model.RSAKey
	err := r.pool.QueryRow(ctx, query).Scan(&k.ID, &k.PublicKeyPEM, &k.PrivateKeyPEM, &k.CreatedAt)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get rsa key: %w", err)
	}
	return &k, nil
}

func (r *RSARepo) Create(ctx context.Context, publicPEM, privatePEM string) (*model.RSAKey, error) {
	query := `
INSERT INTO rsa_keys (public_key_pem, private_key_pem, created_at)
VALUES ($1, $2, NOW())
RETURNING id, public_key_pem, private_key_pem, created_at
`
	var k model.RSAKey
	err := r.pool.QueryRow(ctx, query, publicPEM, privatePEM).Scan(
		&k.ID, &k.PublicKeyPEM, &k.PrivateKeyPEM, &k.CreatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to insert rsa key: %w", err)
	}
	return &k, nil
}
