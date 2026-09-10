package repository

import (
	"context"
	"errors"
	"fmt"

	"backend/internal/model"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type FriendRepo struct {
	pool *pgxpool.Pool
}

func NewFriendRepo(pool *pgxpool.Pool) *FriendRepo {
	return &FriendRepo{pool: pool}
}

func minMax(a, b int) (int, int) {
	if a < b {
		return a, b
	}
	return b, a
}

func (r *FriendRepo) AreFriends(ctx context.Context, userA, userB int) (bool, error) {
	if userA == userB {
		return true, nil
	}
	lo, hi := minMax(userA, userB)
	query := `
SELECT 1 FROM friendships
WHERE user_a_id = $1 AND user_b_id = $2 AND status = 'accepted'
`
	var one int
	err := r.pool.QueryRow(ctx, query, lo, hi).Scan(&one)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return false, nil
		}
		return false, err
	}
	return true, nil
}

func (r *FriendRepo) GetFriendIDs(ctx context.Context, userID int) ([]int, error) {
	query := `
SELECT CASE WHEN user_a_id = $1 THEN user_b_id ELSE user_a_id END
FROM friendships
WHERE status = 'accepted' AND (user_a_id = $1 OR user_b_id = $1)
`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("failed to get friend ids: %w", err)
	}
	defer rows.Close()

	var friendIDs []int
	for rows.Next() {
		var id int
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		friendIDs = append(friendIDs, id)
	}
	return friendIDs, nil
}

func (r *FriendRepo) GetFriendship(ctx context.Context, userA, userB int) (*model.Friendship, error) {
	lo, hi := minMax(userA, userB)
	query := `
SELECT id, user_a_id, user_b_id, status, requester_id, created_at, accepted_at
FROM friendships
WHERE user_a_id = $1 AND user_b_id = $2
`
	var f model.Friendship
	err := r.pool.QueryRow(ctx, query, lo, hi).Scan(
		&f.ID, &f.UserAID, &f.UserBID, &f.Status, &f.RequesterID, &f.CreatedAt, &f.AcceptedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &f, nil
}

func (r *FriendRepo) GetRequestByID(ctx context.Context, id int) (*model.Friendship, error) {
	query := `
SELECT id, user_a_id, user_b_id, status, requester_id, created_at, accepted_at
FROM friendships
WHERE id = $1
`
	var f model.Friendship
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&f.ID, &f.UserAID, &f.UserBID, &f.Status, &f.RequesterID, &f.CreatedAt, &f.AcceptedAt,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return nil, nil
		}
		return nil, err
	}
	return &f, nil
}

func (r *FriendRepo) CreateRequest(ctx context.Context, requesterID, userA, userB int) error {
	lo, hi := minMax(userA, userB)
	query := `
INSERT INTO friendships (user_a_id, user_b_id, status, requester_id, created_at)
VALUES ($1, $2, 'pending', $3, NOW())
`
	_, err := r.pool.Exec(ctx, query, lo, hi, requesterID)
	return err
}

func (r *FriendRepo) AcceptRequest(ctx context.Context, id int) error {
	query := `
UPDATE friendships
SET status = 'accepted', accepted_at = NOW()
WHERE id = $1
`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *FriendRepo) RejectRequest(ctx context.Context, id int) error {
	query := `DELETE FROM friendships WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	return err
}

func (r *FriendRepo) RemoveFriendship(ctx context.Context, userA, userB int) error {
	lo, hi := minMax(userA, userB)
	query := `
DELETE FROM friendships
WHERE user_a_id = $1 AND user_b_id = $2 AND status = 'accepted'
`
	_, err := r.pool.Exec(ctx, query, lo, hi)
	return err
}

func (r *FriendRepo) ListPendingRequests(ctx context.Context, userID int) ([]*model.Friendship, error) {
	query := `
SELECT id, user_a_id, user_b_id, status, requester_id, created_at, accepted_at
FROM friendships
WHERE status = 'pending' AND requester_id != $1 AND (user_a_id = $1 OR user_b_id = $1)
ORDER BY created_at DESC
`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*model.Friendship
	for rows.Next() {
		var f model.Friendship
		if err := rows.Scan(
			&f.ID, &f.UserAID, &f.UserBID, &f.Status, &f.RequesterID, &f.CreatedAt, &f.AcceptedAt,
		); err != nil {
			return nil, err
		}
		list = append(list, &f)
	}
	return list, nil
}

func (r *FriendRepo) ListFriends(ctx context.Context, userID int) ([]*model.Friendship, error) {
	query := `
SELECT id, user_a_id, user_b_id, status, requester_id, created_at, accepted_at
FROM friendships
WHERE status = 'accepted' AND (user_a_id = $1 OR user_b_id = $1)
ORDER BY COALESCE(accepted_at, created_at) DESC
`
	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var list []*model.Friendship
	for rows.Next() {
		var f model.Friendship
		if err := rows.Scan(
			&f.ID, &f.UserAID, &f.UserBID, &f.Status, &f.RequesterID, &f.CreatedAt, &f.AcceptedAt,
		); err != nil {
			return nil, err
		}
		list = append(list, &f)
	}
	return list, nil
}

func (r *FriendRepo) AddDirectFriend(ctx context.Context, userA, userB, requesterID int) error {
	lo, hi := minMax(userA, userB)
	query := `
INSERT INTO friendships (user_a_id, user_b_id, status, requester_id, created_at, accepted_at)
VALUES ($1, $2, 'accepted', $3, NOW(), NOW())
ON CONFLICT (user_a_id, user_b_id) DO UPDATE
SET status = 'accepted', accepted_at = NOW()
`
	_, err := r.pool.Exec(ctx, query, lo, hi, requesterID)
	return err
}
