package service

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"backend/internal/model"
)

type LLMClient struct{}

func NewLLMClient() *LLMClient {
	return &LLMClient{}
}

func (c *LLMClient) mockResponse() *string {
	if val, ok := os.LookupEnv("LLM_MOCK_RESPONSE"); ok {
		return &val
	}
	return nil
}

type ChatMessage struct {
	Role    string `json:"role"`
	Content any    `json:"content"` // string or []map[string]any
}

type ChatRequest struct {
	Model     string        `json:"model"`
	MaxTokens int           `json:"max_tokens"`
	Messages  []ChatMessage `json:"messages"`
}

type ChatResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error,omitempty"`
}

func (c *LLMClient) GenerateComment(ctx context.Context, status *model.SystemStatus, persona, postContent, authorName string, modelName *string, authorContext *string, imagesB64 []string) (string, error) {
	if mock := c.mockResponse(); mock != nil {
		return *mock, nil
	}

	if status.LLMAPIKey == "" {
		return "", errors.New("LLM API Key 未配置")
	}

	useModel := status.LLMModel
	if modelName != nil && *modelName != "" {
		useModel = *modelName
	}

	userText := fmt.Sprintf("你是以下人设的角色，用第一人称简短自然地回复朋友圈动态。人设：%s\n要求：中文，不超过100字，像真人评论，不要markdown不要链接。", persona)
	if authorContext != nil && *authorContext != "" {
		userText += "\n\n" + *authorContext
	}
	userText += fmt.Sprintf("\n\n%s 发了一条朋友圈：\n%s", authorName, postContent)

	var contentList []map[string]any
	contentList = append(contentList, map[string]any{
		"type": "text",
		"text": userText,
	})

	for _, b64 := range imagesB64 {
		contentList = append(contentList, map[string]any{
			"type": "image_url",
			"image_url": map[string]any{
				"url": "data:image/webp;base64," + b64,
			},
		})
	}

	payload := ChatRequest{
		Model:     useModel,
		MaxTokens: status.LLMMaxTokens,
		Messages: []ChatMessage{
			{Role: "user", Content: contentList},
		},
	}

	return c.callAPI(ctx, status.LLMBaseURL, status.LLMAPIKey, status.LLMTimeout, payload)
}

func (c *LLMClient) GenerateReply(ctx context.Context, status *model.SystemStatus, persona, postContent, authorName, replyToName, replyToContent string, modelName *string, authorContext *string, myReplyContent *string, imagesB64 []string) (string, error) {
	if mock := c.mockResponse(); mock != nil {
		return *mock, nil
	}

	if status.LLMAPIKey == "" {
		return "", errors.New("LLM API Key 未配置")
	}

	useModel := status.LLMModel
	if modelName != nil && *modelName != "" {
		useModel = *modelName
	}

	userText := fmt.Sprintf("你是以下人设的角色，用第一人称简短自然地回复别人对你评论的回复。人设：%s\n要求：中文，不超过80字，像真人对话，不要markdown。", persona)
	if authorContext != nil && *authorContext != "" {
		userText += "\n\n" + *authorContext
	}
	userText += fmt.Sprintf("\n\n朋友圈原动态(%s发)：%s", authorName, postContent)
	if myReplyContent != nil && *myReplyContent != "" {
		userText += fmt.Sprintf("\n\n你之前的评论：%s", *myReplyContent)
	}
	userText += fmt.Sprintf("\n\n%s 回复了你：%s", replyToName, replyToContent)

	var contentList []map[string]any
	contentList = append(contentList, map[string]any{
		"type": "text",
		"text": userText,
	})

	for _, b64 := range imagesB64 {
		contentList = append(contentList, map[string]any{
			"type": "image_url",
			"image_url": map[string]any{
				"url": "data:image/webp;base64," + b64,
			},
		})
	}

	payload := ChatRequest{
		Model:     useModel,
		MaxTokens: status.LLMMaxTokens,
		Messages: []ChatMessage{
			{Role: "user", Content: contentList},
		},
	}

	return c.callAPI(ctx, status.LLMBaseURL, status.LLMAPIKey, status.LLMTimeout, payload)
}

func (c *LLMClient) TestLLM(ctx context.Context, baseURL, apiKey, modelName string, timeout int) (string, error) {
	if apiKey == "" {
		return "", errors.New("LLM API Key 未配置")
	}

	payload := ChatRequest{
		Model:     modelName,
		MaxTokens: 16,
		Messages: []ChatMessage{
			{Role: "user", Content: "你是测试助手。请回复\"OK\"。"},
		},
	}

	return c.callAPI(ctx, baseURL, apiKey, timeout, payload)
}

func (c *LLMClient) callAPI(ctx context.Context, baseURL, apiKey string, timeout int, payload ChatRequest) (string, error) {
	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}

	url := strings.TrimRight(baseURL, "/") + "/chat/completions"
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(bodyBytes))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{
		Timeout: time.Duration(timeout) * time.Second,
	}

	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return "", fmt.Errorf("LLM API returned HTTP %d: %s", resp.StatusCode, string(respBody))
	}

	var chatResp ChatResponse
	if err := json.Unmarshal(respBody, &chatResp); err != nil {
		return "", err
	}

	if len(chatResp.Choices) == 0 {
		return "", errors.New("empty choices in LLM response")
	}

	return strings.TrimSpace(chatResp.Choices[0].Message.Content), nil
}
