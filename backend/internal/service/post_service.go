package service

import (
	"context"
	"fmt"
	"strings"
	"time"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type PostService struct {
	cfg   *config.Config
	repos *repository.Repositories
}

func NewPostService(cfg *config.Config, repos *repository.Repositories) *PostService {
	return &PostService{cfg: cfg, repos: repos}
}

func (s *PostService) CanViewPost(ctx context.Context, viewerID int, post *model.Post) (bool, error) {
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

func (s *PostService) CreatePost(ctx context.Context, user *model.User, data model.PostCreateIn) (*model.PostOut, error) {
	content := strings.TrimSpace(data.Content)
	if content == "" || len([]rune(content)) > 2000 {
		return nil, model.NewAppError(model.ErrValidationError, "动态内容长度需在 1-2000 字之间", 400)
	}

	if len(data.MediaIDs) > 9 {
		return nil, model.NewAppError(model.ErrValidationError, "最多上传 9 个媒体文件", 400)
	}

	visibility := data.Visibility
	if visibility != "public" && visibility != "friends" {
		visibility = "public"
	}

	// Validate media ownership
	for _, mid := range data.MediaIDs {
		m, err := s.repos.Media.GetMediaByID(ctx, mid)
		if err != nil {
			return nil, err
		}
		if m == nil || m.OwnerID == nil || *m.OwnerID != user.ID {
			return nil, model.NewAppError(model.ErrMediaNotOwned, "媒体文件不存在或不属于当前用户", 403)
		}
		if m.PostID != nil {
			return nil, model.NewAppError(model.ErrMediaAlreadyUsed, "媒体文件已被使用", 400)
		}
	}

	post := &model.Post{
		UserID:     user.ID,
		Content:    content,
		Visibility: visibility,
	}

	if err := s.repos.Post.Create(ctx, post, data.MediaIDs); err != nil {
		return nil, model.NewAppError(model.ErrInternal, "创建动态失败", 500)
	}

	return s.GetPost(ctx, user.ID, post.ID)
}

func (s *PostService) GetPost(ctx context.Context, viewerID, postID int) (*model.PostOut, error) {
	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return nil, err
	}
	if post == nil {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	canView, err := s.CanViewPost(ctx, viewerID, post)
	if err != nil {
		return nil, err
	}
	if !canView {
		return nil, model.NewAppError(model.ErrForbidden, "无权查看此动态", 403)
	}

	postsOut, err := s.populatePostsOut(ctx, viewerID, []*model.Post{post})
	if err != nil {
		return nil, err
	}
	if len(postsOut) == 0 {
		return nil, model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	return &postsOut[0], nil
}

func (s *PostService) DeletePost(ctx context.Context, user *model.User, postID int) error {
	post, err := s.repos.Post.GetByID(ctx, postID)
	if err != nil {
		return err
	}
	if post == nil {
		return model.NewAppError(model.ErrNotFound, "动态不存在", 404)
	}

	if post.UserID != user.ID && user.Role != "admin" {
		return model.NewAppError(model.ErrForbidden, "无权删除此动态", 403)
	}

	return s.repos.Post.SoftDelete(ctx, postID)
}

func (s *PostService) GetFeed(ctx context.Context, viewerID int, cursorStr *string, limit int) (*model.FeedOut, error) {
	if limit < 1 {
		limit = 10
	} else if limit > 50 {
		limit = 50
	}

	var cursorTime *time.Time
	var cursorID *int
	if cursorStr != nil && *cursorStr != "" {
		t, id, err := util.DecodeCursor(*cursorStr)
		if err != nil {
			return nil, model.NewAppError(model.ErrInvalidCursor, "游标无效", 400)
		}
		cursorTime = &t
		cursorID = &id
	}

	friendIDs, err := s.repos.Friend.GetFriendIDs(ctx, viewerID)
	if err != nil {
		return nil, err
	}

	// Fetch limit + 1
	posts, err := s.repos.Post.Feed(ctx, viewerID, friendIDs, cursorTime, cursorID, limit+1)
	if err != nil {
		return nil, err
	}

	hasMore := false
	if len(posts) > limit {
		hasMore = true
		posts = posts[:limit]
	}

	var nextCursor *string
	if len(posts) > 0 && hasMore {
		last := posts[len(posts)-1]
		c := util.EncodeCursor(last.CreatedAt, last.ID)
		nextCursor = &c
	}

	items, err := s.populatePostsOut(ctx, viewerID, posts)
	if err != nil {
		return nil, err
	}

	return &model.FeedOut{
		Items:      items,
		NextCursor: nextCursor,
		HasMore:    hasMore,
	}, nil
}

func (s *PostService) GetUserPosts(ctx context.Context, viewerID, targetUserID int, cursorStr *string, limit int) (*model.UserPostsOut, error) {
	if limit < 1 {
		limit = 10
	} else if limit > 50 {
		limit = 50
	}

	var cursorTime *time.Time
	var cursorID *int
	if cursorStr != nil && *cursorStr != "" {
		t, id, err := util.DecodeCursor(*cursorStr)
		if err != nil {
			return nil, model.NewAppError(model.ErrInvalidCursor, "游标无效", 400)
		}
		cursorTime = &t
		cursorID = &id
	}

	canViewFriends := viewerID == targetUserID
	if !canViewFriends {
		areFriends, err := s.repos.Friend.AreFriends(ctx, viewerID, targetUserID)
		if err != nil {
			return nil, err
		}
		canViewFriends = areFriends
	}

	posts, err := s.repos.Post.UserPosts(ctx, targetUserID, canViewFriends, cursorTime, cursorID, limit+1)
	if err != nil {
		return nil, err
	}

	hasMore := false
	if len(posts) > limit {
		hasMore = true
		posts = posts[:limit]
	}

	var nextCursor *string
	if len(posts) > 0 && hasMore {
		last := posts[len(posts)-1]
		c := util.EncodeCursor(last.CreatedAt, last.ID)
		nextCursor = &c
	}

	items, err := s.populatePostsOut(ctx, viewerID, posts)
	if err != nil {
		return nil, err
	}

	return &model.UserPostsOut{
		Items:      items,
		NextCursor: nextCursor,
		HasMore:    hasMore,
	}, nil
}

// populatePostsOut eliminates N+1 by batch loading authors, media, comments, likes.
func (s *PostService) populatePostsOut(ctx context.Context, viewerID int, posts []*model.Post) ([]model.PostOut, error) {
	if len(posts) == 0 {
		return []model.PostOut{}, nil
	}

	postIDs := make([]int, len(posts))
	authorIDSet := make(map[int]bool)
	for i, p := range posts {
		postIDs[i] = p.ID
		authorIDSet[p.UserID] = true
	}

	// 1. Batch preload media
	mediaMap, err := s.repos.Post.BatchPreloadMedia(ctx, postIDs)
	if err != nil {
		return nil, err
	}

	// 2. Batch preload like counts & liked by me
	likeCounts, err := s.repos.Post.BatchPreloadLikeCounts(ctx, postIDs)
	if err != nil {
		return nil, err
	}

	likedByMeMap, err := s.repos.Post.BatchPreloadLikedByMe(ctx, postIDs, viewerID)
	if err != nil {
		return nil, err
	}

	// 3. Batch preload comment counts
	commentCounts, err := s.repos.Post.BatchPreloadCommentCounts(ctx, postIDs)
	if err != nil {
		return nil, err
	}

	// 4. Batch preload preview comments
	allCommentsMap, err := s.repos.Post.BatchPreloadPreviewComments(ctx, postIDs)
	if err != nil {
		return nil, err
	}

	// Collect user IDs from comments and parent comment IDs
	parentCommentIDs := make(map[int]bool)
	for _, comments := range allCommentsMap {
		for _, c := range comments {
			authorIDSet[c.UserID] = true
			if c.ReplyToUserID != nil {
				authorIDSet[*c.ReplyToUserID] = true
			}
			if c.ParentCommentID != nil {
				parentCommentIDs[*c.ParentCommentID] = true
			}
		}
	}

	// Preload parent comments for previews
	var pids []int
	for pid := range parentCommentIDs {
		pids = append(pids, pid)
	}
	parentComments, _ := s.repos.Comment.BatchPreloadParents(ctx, pids)

	// Collect like authors
	likeAuthorsMap, err := s.repos.Post.BatchPreloadLikeAuthors(ctx, postIDs)
	if err != nil {
		return nil, err
	}
	for _, likes := range likeAuthorsMap {
		for _, l := range likes {
			authorIDSet[l.UserID] = true
		}
	}

	// 5. Batch preload all authors
	var allUserIDs []int
	for uid := range authorIDSet {
		allUserIDs = append(allUserIDs, uid)
	}
	usersMap, err := s.repos.User.GetByIDs(ctx, allUserIDs)
	if err != nil {
		return nil, err
	}

	// Viewer friends for friends-only comment visibility check
	viewerFriendIDs, err := s.repos.Friend.GetFriendIDs(ctx, viewerID)
	if err != nil {
		return nil, err
	}
	friendSet := make(map[int]bool)
	for _, fid := range viewerFriendIDs {
		friendSet[fid] = true
	}

	// Viewer is admin check
	viewerUser := usersMap[viewerID]
	isAdmin := viewerUser != nil && viewerUser.Role == "admin"

	// 6. Preload like counts and liked_by_me for comments
	var allCommentIDs []int
	for _, comments := range allCommentsMap {
		for _, c := range comments {
			allCommentIDs = append(allCommentIDs, c.ID)
		}
	}
	commentLikeCounts, _ := s.repos.Comment.BatchPreloadLikeCounts(ctx, allCommentIDs)
	commentLikedByMe, _ := s.repos.Comment.BatchPreloadLikedByMe(ctx, allCommentIDs, viewerID)

	var items []model.PostOut
	for _, p := range posts {
		author := usersMap[p.UserID]
		authorOut := s.buildAuthorOut(author)

		var mediaBriefs []model.MediaBriefOut
		if mediaList, ok := mediaMap[p.ID]; ok {
			for _, m := range mediaList {
				mediaBriefs = append(mediaBriefs, s.buildMediaBriefOut(p.ID, m))
			}
		}
		if mediaBriefs == nil {
			mediaBriefs = []model.MediaBriefOut{}
		}

		// Filter comments by visibility:
		// In public post: all non-deleted comments are visible.
		// In friends post: only comments from {viewerID, post.UserID} | friendsOf(viewerID) are visible.
		var previewComments []model.CommentOut
		if comments, ok := allCommentsMap[p.ID]; ok {
			for _, c := range comments {
				if p.Visibility == "friends" {
					if c.UserID != viewerID && c.UserID != p.UserID && !friendSet[c.UserID] {
						continue
					}
				}

				cAuthor := usersMap[c.UserID]
				cAuthorOut := s.buildCommentAuthorOut(cAuthor)

				var replyToOut *model.ReplyToOut
				if c.ReplyToUserID != nil {
					rtUser := usersMap[*c.ReplyToUserID]
					replyToOut = s.buildReplyToOut(rtUser)
				}

				var replyPreview *string
				if c.ParentCommentID != nil {
					if parent, ok := parentComments[*c.ParentCommentID]; ok && parent.Content != nil {
						lines := strings.Split(*parent.Content, "\n")
						firstLine := lines[0]
						runes := []rune(firstLine)
						if len(runes) > 10 {
							prev := string(runes[:10]) + "..."
							replyPreview = &prev
						} else {
							replyPreview = &firstLine
						}
					}
				}

				var thumbURL, largeURL *string
				if c.ImageThumbPath != nil {
					u := fmt.Sprintf("/api/v1/comments/%d/media/thumb", c.ID)
					thumbURL = &u
				}
				if c.ImageLargePath != nil {
					u := fmt.Sprintf("/api/v1/comments/%d/media/large", c.ID)
					largeURL = &u
				}

				canDelete := c.UserID == viewerID || p.UserID == viewerID || isAdmin

				previewComments = append(previewComments, model.CommentOut{
					ID:                  c.ID,
					PostID:              c.PostID,
					Author:              cAuthorOut,
					ParentCommentID:     c.ParentCommentID,
					ReplyTo:             replyToOut,
					ReplyContentPreview: replyPreview,
					Content:             c.Content,
					ImageThumbURL:       thumbURL,
					ImageLargeURL:       largeURL,
					LikeCount:           commentLikeCounts[c.ID],
					LikedByMe:           commentLikedByMe[c.ID],
					IsOwner:             c.UserID == viewerID,
					CanDelete:           canDelete,
					CreatedAt:           c.CreatedAt,
				})
			}
		}
		if previewComments == nil {
			previewComments = []model.CommentOut{}
		}

		// Filter like authors by visibility (up to 5)
		var likeAuthors []model.LikeAuthorOut
		if likes, ok := likeAuthorsMap[p.ID]; ok {
			count := 0
			for _, l := range likes {
				if p.Visibility == "friends" {
					if l.UserID != viewerID && l.UserID != p.UserID && !friendSet[l.UserID] {
						continue
					}
				}
				lAuthor := usersMap[l.UserID]
				likeAuthors = append(likeAuthors, s.buildLikeAuthorOut(lAuthor))
				count++
				if count >= 5 {
					break
				}
			}
		}
		if likeAuthors == nil {
			likeAuthors = []model.LikeAuthorOut{}
		}

		items = append(items, model.PostOut{
			ID:              p.ID,
			Content:         p.Content,
			Visibility:      p.Visibility,
			Author:          authorOut,
			Media:           mediaBriefs,
			LikeCount:       likeCounts[p.ID],
			CommentCount:    commentCounts[p.ID],
			LikedByMe:       likedByMeMap[p.ID],
			IsOwner:         p.UserID == viewerID,
			CreatedAt:       p.CreatedAt,
			UpdatedAt:       p.UpdatedAt,
			PreviewComments: previewComments,
			LikeAuthors:     likeAuthors,
		})
	}

	return items, nil
}

func (s *PostService) buildAuthorOut(u *model.User) model.AuthorOut {
	if u == nil {
		return model.AuthorOut{
			ID:            0,
			Nickname:      "未知",
			AvatarURL:     "/api/v1/avatars/default",
			IsDeactivated: false,
		}
	}
	if u.Status == "deactivated" {
		return model.AuthorOut{
			ID:            u.ID,
			Nickname:      "已注销",
			AvatarURL:     "/api/v1/avatars/default",
			IsDeactivated: true,
		}
	}
	avatarURL := "/api/v1/avatars/default"
	if u.AvatarPath != nil && *u.AvatarPath != "" {
		avatarURL = fmt.Sprintf("/api/v1/avatars/%d", u.ID)
	}
	return model.AuthorOut{
		ID:            u.ID,
		Nickname:      u.Nickname,
		AvatarURL:     avatarURL,
		IsDeactivated: false,
	}
}

func (s *PostService) buildCommentAuthorOut(u *model.User) model.CommentAuthorOut {
	ao := s.buildAuthorOut(u)
	return model.CommentAuthorOut{
		ID:            ao.ID,
		Nickname:      ao.Nickname,
		AvatarURL:     ao.AvatarURL,
		IsDeactivated: ao.IsDeactivated,
	}
}

func (s *PostService) buildReplyToOut(u *model.User) *model.ReplyToOut {
	if u == nil {
		return nil
	}
	if u.Status == "deactivated" {
		return &model.ReplyToOut{
			ID:            u.ID,
			Nickname:      "已注销",
			IsDeactivated: true,
		}
	}
	return &model.ReplyToOut{
		ID:            u.ID,
		Nickname:      u.Nickname,
		IsDeactivated: false,
	}
}

func (s *PostService) buildLikeAuthorOut(u *model.User) model.LikeAuthorOut {
	ao := s.buildAuthorOut(u)
	return model.LikeAuthorOut{
		ID:            ao.ID,
		Nickname:      ao.Nickname,
		AvatarURL:     ao.AvatarURL,
		IsDeactivated: ao.IsDeactivated,
	}
}

func (s *PostService) buildMediaBriefOut(postID int, m *model.PostMedia) model.MediaBriefOut {
	var thumbURL, largeURL, originalURL *string
	if m.ThumbPath != nil {
		u := fmt.Sprintf("/api/v1/posts/%d/media/%d/thumb", postID, m.ID)
		thumbURL = &u
	}
	if m.LargePath != nil {
		u := fmt.Sprintf("/api/v1/posts/%d/media/%d/large", postID, m.ID)
		largeURL = &u
	}
	if m.FilePath != "" {
		u := fmt.Sprintf("/api/v1/posts/%d/media/%d/original", postID, m.ID)
		originalURL = &u
	}
	return model.MediaBriefOut{
		ID:          m.ID,
		Kind:        m.Kind,
		SortOrder:   m.SortOrder,
		ThumbURL:    thumbURL,
		LargeURL:    largeURL,
		OriginalURL: originalURL,
	}
}
