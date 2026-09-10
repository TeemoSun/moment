package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"backend/internal/api"
	"backend/internal/api/middleware"
	"backend/internal/config"
	"backend/internal/database"
	"backend/internal/repository"
	"backend/internal/scheduler"
	"backend/internal/service"
	"backend/internal/worker"
)

func runHealthCheck() {
	port := 8000
	if pStr := os.Getenv("BACKEND_PORT"); pStr != "" {
		if p, err := strconv.Atoi(pStr); err == nil && p > 0 {
			port = p
		}
	} else if pStr := os.Getenv("PORT"); pStr != "" {
		if p, err := strconv.Atoi(pStr); err == nil && p > 0 {
			port = p
		}
	}

	client := http.Client{
		Timeout: 3 * time.Second,
	}

	url := fmt.Sprintf("http://127.0.0.1:%d/api/health", port)
	resp, err := client.Get(url)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Health check failed: %v\n", err)
		os.Exit(1)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		fmt.Fprintf(os.Stderr, "Health check returned non-200 status: %d\n", resp.StatusCode)
		os.Exit(1)
	}

	os.Exit(0)
}

func main() {
	healthCheckFlag := flag.Bool("healthcheck", false, "Run HTTP health check against local backend and exit")
	flag.Parse()

	if *healthCheckFlag {
		runHealthCheck()
		return
	}

	log.Println("Initializing Moments backend...")

	// 1. Ensure runtime environment (.env, JWT secret, etc.)
	config.EnsureRuntimeEnv()

	// 2. Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	log.Printf("Starting %s in %s (Debug: %v)", cfg.AppName, cfg.ProjectRoot, cfg.Debug)

	// 3. Setup context with cancellation
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// 4. Connect to PostgreSQL
	log.Printf("Connecting to PostgreSQL at %s:%d/%s...", cfg.PostgresHost, cfg.PostgresPort, cfg.PostgresDB)
	pool, err := database.NewPool(ctx, cfg.GetPGXConnString())
	if err != nil {
		log.Fatalf("Failed to initialize database pool: %v", err)
	}
	defer pool.Close()

	// 5. Run DB migrations under file lock
	log.Println("Running database migrations and seed...")
	if err := database.RunMigrations(ctx, pool, cfg.ProjectRoot); err != nil {
		log.Fatalf("Failed to run database migrations: %v", err)
	}

	// 6. Repositories
	repos := repository.NewRepositories(pool)

	// 7. Media Worker Pool
	mediaPool := worker.NewMediaWorkerPool(cfg, repos, 4)
	mediaPool.Start()
	defer mediaPool.Stop()

	// 8. Services & Bot Scheduler
	var botScheduler *scheduler.BotScheduler

	services := service.NewServices(cfg, repos, func(botUserID int) {
		if botScheduler != nil {
			botScheduler.TriggerNow(botUserID)
		}
	})

	// RSA warmup
	if _, err := services.Auth.GetRSAPublicKey(ctx); err != nil {
		log.Printf("RSA warmup warning: %v", err)
	}

	botScheduler = scheduler.NewBotScheduler(cfg, repos, services.BotEngine)
	botScheduler.Start()
	defer botScheduler.Stop()

	// 9. Rate Limiter
	rateLimiter := middleware.NewRateLimiter(cfg)

	// 10. Router & Server
	router := api.NewRouter(cfg, repos, services, rateLimiter, func(mediaID int, kind string) {
		mediaPool.Submit(mediaID, kind)
	})

	addr := fmt.Sprintf("%s:%d", cfg.BackendHost, cfg.BackendPort)
	server := &http.Server{
		Addr:              addr,
		Handler:           router,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      60 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	// 11. Start server in goroutine
	serverErrors := make(chan error, 1)
	go func() {
		log.Printf("Moments backend listening on %s", addr)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			serverErrors <- err
		}
	}()

	// 12. Graceful Shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	select {
	case err := <-serverErrors:
		log.Fatalf("Server error: %v", err)
	case sig := <-quit:
		log.Printf("Received signal %v, shutting down gracefully...", sig)
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("Server forced shutdown: %v", err)
	}

	log.Println("Moments backend stopped.")
}
