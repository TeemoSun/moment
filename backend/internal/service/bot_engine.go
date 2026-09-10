package service

import (
	"context"
	"encoding/base64"
	"fmt"
	"math/rand"
	"os"
	"strings"
	"time"

	"backend/internal/config"
	"backend/internal/model"
	"backend/internal/repository"
	"backend/internal/util"
)

type BotEngine struct {
	cfg       *config.Config
	repos     *repository.Repositories
	llmClient *LLMClient
}

func NewBotEngine(cfg *config.Config, repos *repository.Repositories, llmClient *LLMClient) *BotEngine {
	return &BotEngine{
		cfg:       cfg,
		repos:     repos,
		llmClient: llmClient,
	}
}

func (e *BotEngine) RunBot(ctx context.Context, botUserID int) error {
	bot, err := e.repos.Bot.GetByUserID(ctx, botUserID)
	if err != nil {
		return err
	}
	if bot == nil || !bot.Enabled || bot.AutoPaused {
		return nil
	}

	user, err := e.repos.User.GetByID(ctx, botUserID)
	if err != nil {
		return err
	}
	if user == nil || user.Status != "active" || user.Role != "bot" {
		return nil
	}

	systemStatus, err := e.repos.System.GetStatus(ctx)
	if err != nil {
		return err
	}
	if systemStatus == nil {
		return nil
	}

	innerErr := e.runBotInner(ctx, bot, user, systemStatus)

	n := bot.PollIntervalN
	x := bot.PollIntervalX
	minDelay := n - x
	if minDelay < 1 {
		minDelay = 1
	}
	maxDelay := n + x
	if maxDelay < minDelay {
		maxDelay = minDelay
	}

	delaySecs := minDelay
	if maxDelay > minDelay {
		delaySecs = minDelay + rand.Intn(maxDelay-minDelay+1)
	}

	nextRun := time.Now().UTC().Add(time.Duration(delaySecs) * time.Second)

	if innerErr != nil {
		_ = e.repos.Bot.UpdateRunFailure(ctx, bot.ID, bot.MaxConsecutiveFailures, nextRun)
		return innerErr
	}

	return e.repos.Bot.UpdateRunSuccess(ctx, bot.ID, nextRun)
}

func (e *BotEngine) runBotInner(ctx context.Context, bot *model.Bot, user *model.User, systemStatus *model.SystemStatus) error {
	friendIDs, err := e.repos.Friend.GetFriendIDs(ctx, user.ID)
	if err != nil {
		return err
	}
	if len(friendIDs) == 0 {
		return nil
	}

	oneHourAgo := time.Now().UTC().Add(-1 * time.Hour)
	rateUsed, err := e.repos.Bot.CountRecentComments(ctx, user.ID, oneHourAgo)
	if err != nil {
		return err
	}
	rateLimit := bot.CommentsPerHour

	cutoff := time.Now().UTC().Add(-time.Duration(bot.LookbackDays) * 24 * time.Hour)

	// Fetch recent posts by friends
	cursorTime := time.Now().UTC()
	cursorID := int(2e9)
	posts, err := e.repos.Post.Feed(ctx, user.ID, friendIDs, &cursorTime, &cursorID, 50)
	if err != nil {
		return err
	}

	for _, p := range posts {
		if rateUsed >= rateLimit {
			break
		}
		if p.CreatedAt.Before(cutoff) {
			continue
		}

		already, err := e.repos.Bot.AlreadyRepliedPost(ctx, user.ID, p.ID)
		if err != nil || already {
			continue
		}

		author, err := e.repos.User.GetByID(ctx, p.UserID)
		if err != nil || author == nil {
			continue
		}

		imagesB64 := e.getPostImagesB64(ctx, p.ID)
		authorContext := e.buildAuthorContext(ctx, author.ID, p.ID)

		content, err := e.llmClient.GenerateComment(ctx, systemStatus, bot.Persona, p.Content, author.Nickname, bot.LLMModel, authorContext, imagesB64)
		if err != nil {
			return fmt.Errorf("generate comment error: %w", err)
		}
		if content == "" {
			continue
		}

		comment := &model.Comment{
			PostID:  p.ID,
			UserID:  user.ID,
			Content: &content,
		}
		if err := e.repos.Comment.Create(ctx, comment); err != nil {
			continue
		}

		_ = e.repos.Bot.CreateReplyLog(ctx, &model.BotReplyLog{
			BotUserID:       user.ID,
			PostID:          p.ID,
			Kind:            "post_reply",
			TargetCommentID: nil,
			ReplyCommentID:  comment.ID,
		})

		rateUsed++
	}

	// 2. Check replies to bot's comments
	postIDs, err := e.repos.Bot.GetBotCommentedPostIDs(ctx, user.ID)
	if err != nil || len(postIDs) == 0 {
		return nil
	}

	for _, pid := range postIDs {
		if rateUsed >= rateLimit {
			break
		}

		comments, _, err := e.repos.Comment.ListByPost(ctx, pid, nil, 0, 100)
		if err != nil {
			continue
		}

		for _, tc := range comments {
			if rateUsed >= rateLimit {
				break
			}
			if tc.ReplyToUserID == nil || *tc.ReplyToUserID != user.ID || tc.UserID == user.ID {
				continue
			}

			already, err := e.repos.Bot.AlreadyRepliedComment(ctx, user.ID, tc.ID)
			if err != nil || already {
				continue
			}

			tcAuthor, err := e.repos.User.GetByID(ctx, tc.UserID)
			if err != nil || tcAuthor == nil || tcAuthor.Role == "bot" {
				continue
			}

			areFriends, err := e.repos.Friend.AreFriends(ctx, user.ID, tc.UserID)
			if err != nil || !areFriends {
				continue
			}

			innerPost, err := e.repos.Post.GetByID(ctx, pid)
			if err != nil || innerPost == nil {
				continue
			}

			postAuthor, _ := e.repos.User.GetByID(ctx, innerPost.UserID)
			postAuthorName := "未知"
			if postAuthor != nil {
				postAuthorName = postAuthor.Nickname
			}

			authorContext := e.buildAuthorContext(ctx, innerPost.UserID, innerPost.ID)
			myReplyContent := e.getBotReplyText(ctx, user.ID, tc)
			imagesB64 := e.getCommentImageB64(tc)

			replyToContent := ""
			if tc.Content != nil {
				replyToContent = *tc.Content
			}

			replyContent, err := e.llmClient.GenerateReply(
				ctx, systemStatus, bot.Persona, innerPost.Content,
				postAuthorName, tcAuthor.Nickname, replyToContent,
				bot.LLMModel, authorContext, myReplyContent, imagesB64,
			)
			if err != nil {
				return fmt.Errorf("generate reply error: %w", err)
			}
			if replyContent == "" {
				continue
			}

			comment := &model.Comment{
				PostID:          pid,
				UserID:          user.ID,
				ParentCommentID: &tc.ID,
				ReplyToUserID:   &tc.UserID,
				Content:         &replyContent,
			}
			if err := e.repos.Comment.Create(ctx, comment); err != nil {
				continue
			}

			_ = e.repos.Bot.CreateReplyLog(ctx, &model.BotReplyLog{
				BotUserID:       user.ID,
				PostID:          pid,
				Kind:            "comment_reply",
				TargetCommentID: &tc.ID,
				ReplyCommentID:  comment.ID,
			})

			rateUsed++
		}
	}

	return nil
}

func (e *BotEngine) getPostImagesB64(ctx context.Context, postID int) []string {
	mediaMap, err := e.repos.Post.BatchPreloadMedia(ctx, []int{postID})
	if err != nil {
		return nil
	}
	mediaList := mediaMap[postID]
	var res []string
	for _, m := range mediaList {
		if m.Kind != "image" || m.ThumbPath == nil || *m.ThumbPath == "" {
			continue
		}
		abs, ok := util.ResolveWithinStorage(e.cfg.StorageRoot, *m.ThumbPath)
		if !ok {
			continue
		}
		data, err := os.ReadFile(abs)
		if err == nil {
			res = append(res, base64.StdEncoding.EncodeToString(data))
		}
	}
	return res
}

func (e *BotEngine) getCommentImageB64(comment *model.Comment) []string {
	if comment.ImageThumbPath == nil || *comment.ImageThumbPath == "" {
		return nil
	}
	abs, ok := util.ResolveWithinStorage(e.cfg.StorageRoot, *comment.ImageThumbPath)
	if !ok {
		return nil
	}
	data, err := os.ReadFile(abs)
	if err != nil {
		return nil
	}
	return []string{base64.StdEncoding.EncodeToString(data)}
}

func (e *BotEngine) getBotReplyText(ctx context.Context, botUserID int, targetComment *model.Comment) *string {
	if targetComment.ParentCommentID == nil {
		return nil
	}
	log, err := e.repos.Bot.GetBotReplyLogByTarget(ctx, botUserID, *targetComment.ParentCommentID)
	if err != nil || log == nil {
		return nil
	}
	myComment, err := e.repos.Comment.GetByID(ctx, log.ReplyCommentID)
	if err != nil || myComment == nil {
		return nil
	}
	return myComment.Content
}

func (e *BotEngine) buildAuthorContext(ctx context.Context, authorID, excludePostID int) *string {
	posts, err := e.repos.Post.UserPosts(ctx, authorID, true, nil, nil, 10)
	if err != nil || len(posts) == 0 {
		return nil
	}

	var validPosts []*model.Post
	for _, p := range posts {
		if p.ID != excludePostID {
			validPosts = append(validPosts, p)
		}
	}
	if len(validPosts) == 0 {
		return nil
	}

	nowStr := util.BeijingNow().Format("2006-01-02 15:04")
	header := fmt.Sprintf("当前时间：%s\n以下是作者最近的朋友圈动态：", nowStr)

	postIDs := make([]int, len(validPosts))
	for i, p := range validPosts {
		postIDs[i] = p.ID
	}
	mediaMap, _ := e.repos.Post.BatchPreloadMedia(ctx, postIDs)
	commentsMap, _ := e.repos.Post.BatchPreloadPreviewComments(ctx, postIDs)

	var authorIDs []int
	for _, comments := range commentsMap {
		for _, c := range comments {
			authorIDs = append(authorIDs, c.UserID)
		}
	}
	usersMap, _ := e.repos.User.GetByIDs(ctx, authorIDs)

	var bodyLines []string
	for _, p := range validPosts {
		ts := util.ToBeijing(p.CreatedAt).Format("2006-01-02 15:04")
		body := p.Content

		var mediaTags []string
		if mList, ok := mediaMap[p.ID]; ok {
			for _, m := range mList {
				if m.Kind == "image" {
					mediaTags = append(mediaTags, "[图片]")
				} else if m.Kind == "video" {
					mediaTags = append(mediaTags, "[视频]")
				}
			}
		}
		if len(mediaTags) > 0 {
			tagStr := strings.Join(mediaTags, "")
			if body != "" {
				body = body + " " + tagStr
			} else {
				body = tagStr
			}
		}

		lines := []string{fmt.Sprintf("[%s] %s", ts, body)}
		if cList, ok := commentsMap[p.ID]; ok {
			for _, c := range cList {
				cAuthorName := "未知"
				if u, ok := usersMap[c.UserID]; ok && u != nil {
					cAuthorName = u.Nickname
				}
				cTs := util.ToBeijing(c.CreatedAt).Format("2006-01-02 15:04")
				cBody := ""
				if c.Content != nil {
					cBody = *c.Content
				}
				if c.ImageThumbPath != nil {
					cBody = strings.TrimSpace(cBody + " [图片]")
				}
				lines = append(lines, fmt.Sprintf("  └ %s(%s)：%s", cAuthorName, cTs, cBody))
			}
		}
		bodyLines = append(bodyLines, strings.Join(lines, "\n"))
	}

	result := fmt.Sprintf("%s\n\n%s", header, strings.Join(bodyLines, "\n\n"))
	return &result
}
