package v1

import (
	"backend/internal/api/middleware"
	"backend/internal/config"
	"backend/internal/service"
)

type ApiHandler struct {
	cfg         *config.Config
	services    *service.Services
	rateLimiter *middleware.RateLimiter
	submitMedia func(mediaID int, kind string)
}

func NewApiHandler(
	cfg *config.Config,
	services *service.Services,
	rateLimiter *middleware.RateLimiter,
	submitMedia func(mediaID int, kind string),
) *ApiHandler {
	return &ApiHandler{
		cfg:         cfg,
		services:    services,
		rateLimiter: rateLimiter,
		submitMedia: submitMedia,
	}
}
