package repository

import (
	"context"
	"errors"
	"fmt"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type SystemRepo struct {
	pool *pgxpool.Pool
}

func NewSystemRepo(pool *pgxpool.Pool) *SystemRepo {
	return &SystemRepo{pool: pool}
}

func (r *SystemRepo) GetStatus(ctx context.Context) (*model.SystemStatus, error) {
	query := `
SELECT id, initialized, admin_user_id, llm_base_url, llm_api_key, llm_model, llm_timeout, llm_max_tokens, created_at, updated_at
FROM system_status
WHERE id = 1
`
	var s model.SystemStatus
	err := r.pool.QueryRow(ctx, query).Scan(
		&s.ID, &s.Initialized, &s.AdminUserID, &s.LLMBaseURL, &s.LLMAPIKey,
		&s.LLMModel, &s.LLMTimeout, &s.LLMMaxTokens, &s.CreatedAt, &s.UpdatedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get system status: %w", err)
	}
	return &s, nil
}

func (r *SystemRepo) SetInitialized(ctx context.Context, adminUserID int) error {
	query := `
UPDATE system_status
SET initialized = true,
    admin_user_id = $1,
    updated_at = NOW()
WHERE id = 1
`
	_, err := r.pool.Exec(ctx, query, adminUserID)
	return err
}

func (r *SystemRepo) UpdateLLMConfig(ctx context.Context, baseURL, apiKey, llmModel *string, timeout, maxTokens *int) (*model.SystemStatus, error) {
	query := `
UPDATE system_status
SET llm_base_url = COALESCE($1, llm_base_url),
    llm_api_key = COALESCE($2, llm_api_key),
    llm_model = COALESCE($3, llm_model),
    llm_timeout = COALESCE($4, llm_timeout),
    llm_max_tokens = COALESCE($5, llm_max_tokens),
    updated_at = NOW()
WHERE id = 1
RETURNING id, initialized, admin_user_id, llm_base_url, llm_api_key, llm_model, llm_timeout, llm_max_tokens, created_at, updated_at
`
	var s model.SystemStatus
	err := r.pool.QueryRow(ctx, query, baseURL, apiKey, llmModel, timeout, maxTokens).Scan(
		&s.ID, &s.Initialized, &s.AdminUserID, &s.LLMBaseURL, &s.LLMAPIKey,
		&s.LLMModel, &s.LLMTimeout, &s.LLMMaxTokens, &s.CreatedAt, &s.UpdatedAt,
	)
	if err != nil {
		return nil, err
	}
	return &s, nil
}
