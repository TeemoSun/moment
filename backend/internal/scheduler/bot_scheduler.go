package scheduler

import (
	"context"
	"log"
	"math/rand"
	"os"
	"path/filepath"
	"sync"
	"syscall"
	"time"

	"backend/internal/config"
	"backend/internal/repository"
	"backend/internal/service"
)

type BotScheduler struct {
	cfg       *config.Config
	repos     *repository.Repositories
	engine    *service.BotEngine
	lockFd    *os.File
	isMaster  bool
	timers    map[int]*time.Timer
	timersMu  sync.Mutex
	ctx       context.Context
	cancel    context.CancelFunc
}

func NewBotScheduler(cfg *config.Config, repos *repository.Repositories, engine *service.BotEngine) *BotScheduler {
	ctx, cancel := context.WithCancel(context.Background())
	return &BotScheduler{
		cfg:    cfg,
		repos:  repos,
		engine: engine,
		timers: make(map[int]*time.Timer),
		ctx:    ctx,
		cancel: cancel,
	}
}

func (s *BotScheduler) tryAcquireLock() bool {
	lockPath := filepath.Join(s.cfg.ProjectRoot, "data", ".bot_scheduler.lock")
	_ = os.MkdirAll(filepath.Dir(lockPath), 0755)

	fd, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		return false
	}

	if err := syscall.Flock(int(fd.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		_ = fd.Close()
		return false
	}

	s.lockFd = fd
	s.isMaster = true
	return true
}

func (s *BotScheduler) Start() {
	if !s.tryAcquireLock() {
		log.Println("[BotScheduler] another worker holds the lock, skipping scheduling")
		return
	}

	log.Println("[BotScheduler] started (master)")

	// Schedule all enabled, non-paused bots
	ctx := context.Background()
	bots, err := s.repos.Bot.ListEnabled(ctx)
	if err != nil {
		log.Printf("[BotScheduler] failed to list enabled bots: %v", err)
		return
	}

	for _, b := range bots {
		s.ScheduleNext(b.UserID, b.PollIntervalN, b.PollIntervalX)
	}
}

func (s *BotScheduler) Stop() {
	s.cancel()

	s.timersMu.Lock()
	for _, t := range s.timers {
		t.Stop()
	}
	s.timers = make(map[int]*time.Timer)
	s.timersMu.Unlock()

	if s.lockFd != nil {
		_ = syscall.Flock(int(s.lockFd.Fd()), syscall.LOCK_UN)
		_ = s.lockFd.Close()
		s.lockFd = nil
	}
	s.isMaster = false
}

func (s *BotScheduler) ScheduleNext(botUserID, n, x int) {
	if !s.isMaster {
		return
	}

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

	duration := time.Duration(delaySecs) * time.Second

	s.timersMu.Lock()
	defer s.timersMu.Unlock()

	if existing, ok := s.timers[botUserID]; ok {
		existing.Stop()
	}

	timer := time.AfterFunc(duration, func() {
		s.runAndReschedule(botUserID, n, x)
	})
	s.timers[botUserID] = timer
}

func (s *BotScheduler) runAndReschedule(botUserID, n, x int) {
	ctx, cancel := context.WithTimeout(s.ctx, 5*time.Minute)
	defer cancel()

	if err := s.engine.RunBot(ctx, botUserID); err != nil {
		log.Printf("[BotScheduler] runBot %d failed: %v", botUserID, err)
	}

	// Check if bot is still enabled
	bot, err := s.repos.Bot.GetByUserID(ctx, botUserID)
	if err == nil && bot != nil && bot.Enabled && !bot.AutoPaused {
		s.ScheduleNext(botUserID, bot.PollIntervalN, bot.PollIntervalX)
	}
}

func (s *BotScheduler) TriggerNow(botUserID int) {
	go func() {
		ctx, cancel := context.WithTimeout(s.ctx, 5*time.Minute)
		defer cancel()

		if err := s.engine.RunBot(ctx, botUserID); err != nil {
			log.Printf("[BotScheduler] TriggerNow %d failed: %v", botUserID, err)
		}

		bot, err := s.repos.Bot.GetByUserID(ctx, botUserID)
		if err == nil && bot != nil && bot.Enabled && !bot.AutoPaused {
			s.ScheduleNext(botUserID, bot.PollIntervalN, bot.PollIntervalX)
		}
	}()
}
