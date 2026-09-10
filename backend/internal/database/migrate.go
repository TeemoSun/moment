package database

import (
	"context"
	_ "embed"
	"fmt"
	"os"
	"path/filepath"
	"syscall"

	"github.com/jackc/pgx/v5/pgxpool"
)

//go:embed migrations/schema.sql
var schemaSQL string

// RunMigrations executes schema.sql, ensures alembic_version has 0003_user_token_version,
// and ensures system_status has row id=1.
func RunMigrations(ctx context.Context, pool *pgxpool.Pool, projectRoot string) error {
	// Startup lock to prevent concurrency conflict between multiple processes
	lockPath := filepath.Join(projectRoot, "data", ".startup.lock")
	_ = os.MkdirAll(filepath.Dir(lockPath), 0755)

	lockFd, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0600)
	if err == nil {
		defer func() {
			_ = syscall.Flock(int(lockFd.Fd()), syscall.LOCK_UN)
			_ = lockFd.Close()
		}()
		_ = syscall.Flock(int(lockFd.Fd()), syscall.LOCK_EX)
	}

	// 1. Run schema DDL
	if _, err := pool.Exec(ctx, schemaSQL); err != nil {
		return fmt.Errorf("failed to execute schema DDL: %w", err)
	}

	// 2. Ensure alembic_version contains 0003_user_token_version
	ensureAlembic := `
INSERT INTO alembic_version (version_num) 
VALUES ('0003_user_token_version') 
ON CONFLICT (version_num) DO NOTHING;
`
	if _, err := pool.Exec(ctx, ensureAlembic); err != nil {
		return fmt.Errorf("failed to ensure alembic_version: %w", err)
	}

	// 3. Ensure system_status has row id=1
	ensureStatus := `
INSERT INTO system_status (id, initialized, admin_user_id, created_at, updated_at)
SELECT 1, false, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
WHERE NOT EXISTS (SELECT 1 FROM system_status WHERE id = 1);
`
	if _, err := pool.Exec(ctx, ensureStatus); err != nil {
		return fmt.Errorf("failed to ensure system_status row 1: %w", err)
	}

	return nil
}
