package service

import (
	"context"

	"backend/internal/model"
	"backend/internal/repository"
)

type LikeService struct {
	repos *repository.Repositories
}

func NewLikeService(repos *repository.Repositories) *LikeService {
	return &LikeService{repos: repos}
}

func (s *LikeService) TogglePostLike(ctx context.Context, user *model.User, postID int) (*model.LikeCountOut, error) {
	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canView, err := s.canViewPost(ctx, user.ID, post)
	if err != nil {
		return nil, err
	}
	if !canView {
		return nil, model.NewAppError(model.ErrForbidden, "无权点赞此动态", 403)
	}

	liked, count, err := s.repos.Like.Toggle(ctx, "post", postID, user.ID)
	if err != nil {
		return nil, err
	}

	return &model.LikeCountOut{
		TargetType: "post",
		TargetID:   postID,
		LikeCount:  count,
		LikedByMe:  liked,
	}, nil
}

func (s *LikeService) UnlikePost(ctx context.Context, user *model.User, postID int) (*model.LikeCountOut, error) {
	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canView, err := s.canViewPost(ctx, user.ID, post)
	if err != nil {
		return nil, err
	}
	if !canView {
		return nil, model.NewAppError(model.ErrForbidden, "无权操作", 403)
	}

	count, err := s.repos.Like.Unlike(ctx, "post", postID, user.ID)
	if err != nil {
		return nil, err
	}

	return &model.LikeCountOut{
		TargetType: "post",
		TargetID:   postID,
		LikeCount:  count,
		LikedByMe:  false,
	}, nil
}

func (s *LikeService) ToggleCommentLike(ctx context.Context, user *model.User, commentID int) (*model.LikeCountOut, error) {
	comment, err := s.repos.Comment.GetByID(ctx, commentID)
	if err != nil {
		return nil, err
	}
	if comment == nil {
		return nil, model.NewAppError(model.ErrCommentNotFound, "评论不存在", 404)
	}

	post, err := s.repos.Post.GetByID(ctx, comment.PostID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canViewP, err := s.canViewPost(ctx, user.ID, post)
	if err != nil {
		return nil, err
	}
	if !canViewP {
		return nil, model.NewAppError(model.ErrForbidden, "无权点赞此评论", 403)
	}

	canViewC, err := s.canViewComment(ctx, user.ID, comment, post)
	if err != nil {
		return nil, err
	}
	if !canViewC {
		return nil, model.NewAppError(model.ErrForbidden, "无权点赞此评论", 403)
	}

	liked, count, err := s.repos.Like.Toggle(ctx, "comment", commentID, user.ID)
	if err != nil {
		return nil, err
	}

	return &model.LikeCountOut{
		TargetType: "comment",
		TargetID:   commentID,
		LikeCount:  count,
		LikedByMe:  liked,
	}, nil
}

func (s *LikeService) UnlikeComment(ctx context.Context, user *model.User, commentID int) (*model.LikeCountOut, error) {
	comment, err := s.repos.Comment.GetByID(ctx, commentID)
	if err != nil {
		return nil, err
	}
	if comment == nil {
		return nil, model.NewAppError(model.ErrCommentNotFound, "评论不存在", 404)
	}

	post, err := s.repos.Post.GetByID(ctx, comment.PostID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canViewP, err := s.canViewPost(ctx, user.ID, post)
	if err != nil {
		return nil, err
	}
	if !canViewP {
		return nil, model.NewAppError(model.ErrForbidden, "无权操作", 403)
	}

	count, err := s.repos.Like.Unlike(ctx, "comment", commentID, user.ID)
	if err != nil {
		return nil, err
	}

	return &model.LikeCountOut{
		TargetType: "comment",
		TargetID:   commentID,
		LikeCount:  count,
		LikedByMe:  false,
	}, nil
}

func (s *LikeService) canViewPost(ctx context.Context, viewerID int, post *model.Post) (bool, error) {
	if post.DeletedAt != nil {
		return false, nil
	}
	if post.Visibility == "public" {
		return true, nil
	}
	if viewerID == post.UserID {
		return true, nil
	}
	return s.repos.Friend.AreFriends(ctx, viewerID, post.UserID)
}

func (s *LikeService) canViewComment(ctx context.Context, viewerID int, comment *model.Comment, post *model.Post) (bool, error) {
	if comment.DeletedAt != nil || post.DeletedAt != nil {
		return false, nil
	}
	if post.Visibility == "public" {
		return true, nil
	}
	if comment.UserID == viewerID || comment.UserID == post.UserID {
		return true, nil
	}
	return s.repos.Friend.AreFriends(ctx, viewerID, comment.UserID)
}
