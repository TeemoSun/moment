package config

import (
	"bufio"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
)

var (
	ensureOnce sync.Once
)

type Config struct {
	AppName                string
	Debug                  bool
	SecureCookies          bool
	RateLimitEnabled       bool
	AllowInsecureClipboard bool

	DBURL            string
	PostgresUser     string
	PostgresPassword string
	PostgresDB       string
	PostgresHost     string
	PostgresPort     int

	JWTSecret      string
	JWTAlgorithm   string
	JWTExpireDays  int
	CookieName     string
	CSRFCookieName string

	PublicBaseURL string

	StorageRoot       string
	MediaImageMaxMB   int
	MediaVideoMaxMB   int
	ThumbSize         int
	LargeSize         int
	WebpThumbQuality  int
	WebpLargeQuality  int

	LogDir   string
	LogLevel string

	BackendHost string
	BackendPort int

	FrontendDist string

	CORSOrigins string

	ProjectRoot string
}

// FindProjectRoot locates the project root containing .env or .env.example or backend-go
func FindProjectRoot() string {
	if root := os.Getenv("PROJECT_ROOT"); root != "" {
		if abs, err := filepath.Abs(root); err == nil {
			return abs
		}
	}
	// Try current working directory and walk up
	cwd, err := os.Getwd()
	if err == nil {
		dir := cwd
		for {
			if _, err := os.Stat(filepath.Join(dir, ".env")); err == nil {
				return dir
			}
			if _, err := os.Stat(filepath.Join(dir, ".env.example")); err == nil {
				return dir
			}
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	// Fallback to /home/teemo/projects/moment
	return "/home/teemo/projects/moment"
}

// EnsureRuntimeEnv ensures .env exists and JWT_SECRET is generated if missing/empty.
func EnsureRuntimeEnv() {
	ensureOnce.Do(func() {
		projectRoot := FindProjectRoot()
		envFile := filepath.Join(projectRoot, ".env")
		envExample := filepath.Join(projectRoot, ".env.example")
		lockFile := envFile + ".lock"

		lockFd, err := os.OpenFile(lockFile, os.O_CREATE|os.O_RDWR, 0600)
		if err == nil {
			defer func() {
				_ = syscall.Flock(int(lockFd.Fd()), syscall.LOCK_UN)
				_ = lockFd.Close()
			}()
			_ = syscall.Flock(int(lockFd.Fd()), syscall.LOCK_EX)
		}

		if _, err := os.Stat(envFile); os.IsNotExist(err) {
			if _, err := os.Stat(envExample); err == nil {
				content, err := os.ReadFile(envExample)
				if err == nil {
					_ = os.WriteFile(envFile, content, 0600)
				}
			} else {
				_ = os.WriteFile(envFile, []byte(""), 0600)
			}
		}

		content, err := os.ReadFile(envFile)
		if err != nil {
			return
		}

		lines := strings.Split(string(content), "\n")
		foundSecretLine := false
		needsSecret := true
		var newLines []string

		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if strings.HasPrefix(trimmed, "JWT_SECRET=") {
				foundSecretLine = true
				val := strings.TrimSpace(strings.TrimPrefix(trimmed, "JWT_SECRET="))
				if val != "" {
					needsSecret = false
					newLines = append(newLines, line)
				} else {
					secret := generateRandomSecret(48)
					newLines = append(newLines, "JWT_SECRET="+secret)
				}
			} else {
				newLines = append(newLines, line)
			}
		}

		if !foundSecretLine {
			secret := generateRandomSecret(48)
			newLines = append(newLines, "JWT_SECRET="+secret)
		}

		if needsSecret || !foundSecretLine {
			newContent := strings.Join(newLines, "\n")
			if !strings.HasSuffix(newContent, "\n") {
				newContent += "\n"
			}
			_ = os.WriteFile(envFile, []byte(newContent), 0600)
		}
		_ = os.Chmod(envFile, 0600)
	})
}

func generateRandomSecret(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}

// Load loads settings from .env and environment variables.
func Load() (*Config, error) {
	EnsureRuntimeEnv()

	projectRoot := FindProjectRoot()
	envFile := filepath.Join(projectRoot, ".env")

	envMap := make(map[string]string)
	if f, err := os.Open(envFile); err == nil {
		scanner := bufio.NewScanner(f)
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line == "" || strings.HasPrefix(line, "#") {
				continue
			}
			parts := strings.SplitN(line, "=", 2)
			if len(parts) == 2 {
				k := strings.TrimSpace(parts[0])
				v := strings.TrimSpace(parts[1])
				envMap[k] = v
			}
		}
		_ = f.Close()
	}

	getEnv := func(key, def string) string {
		if v := os.Getenv(key); v != "" {
			return v
		}
		if v, ok := envMap[key]; ok && v != "" {
			return v
		}
		return def
	}

	getBool := func(key string, def bool) bool {
		val := strings.ToLower(getEnv(key, ""))
		if val == "" {
			return def
		}
		return val == "true" || val == "1" || val == "yes"
	}

	getInt := func(key string, def int) int {
		val := getEnv(key, "")
		if val == "" {
			return def
		}
		if i, err := strconv.Atoi(val); err == nil {
			return i
		}
		return def
	}

	cfg := &Config{
		AppName:                getEnv("APP_NAME", "Moments"),
		Debug:                  getBool("DEBUG", false),
		SecureCookies:          getBool("SECURE_COOKIES", false),
		RateLimitEnabled:       getBool("RATE_LIMIT_ENABLED", true),
		AllowInsecureClipboard: getBool("ALLOW_INSECURE_CLIPBOARD", false),

		DBURL:            getEnv("DB_URL", ""),
		PostgresUser:     getEnv("POSTGRES_USER", "moments"),
		PostgresPassword: getEnv("POSTGRES_PASSWORD", "moments"),
		PostgresDB:       getEnv("POSTGRES_DB", "moments"),
		PostgresHost:     getEnv("POSTGRES_HOST", "localhost"),
		PostgresPort:     getInt("POSTGRES_PORT", 5432),

		JWTSecret:      getEnv("JWT_SECRET", ""),
		JWTAlgorithm:   getEnv("JWT_ALGORITHM", "HS256"),
		JWTExpireDays:  getInt("JWT_EXPIRE_DAYS", 7),
		CookieName:     getEnv("COOKIE_NAME", "moments_token"),
		CSRFCookieName: getEnv("CSRF_COOKIE_NAME", "moments_csrf"),

		PublicBaseURL: getEnv("PUBLIC_BASE_URL", "http://localhost:8000"),

		StorageRoot:      getEnv("STORAGE_ROOT", "storage"),
		MediaImageMaxMB:  getInt("MEDIA_IMAGE_MAX_MB", 40),
		MediaVideoMaxMB:  getInt("MEDIA_VIDEO_MAX_MB", 200),
		ThumbSize:        getInt("THUMB_SIZE", 400),
		LargeSize:        getInt("LARGE_SIZE", 2160),
		WebpThumbQuality: getInt("WEBP_THUMB_QUALITY", 80),
		WebpLargeQuality: getInt("WEBP_LARGE_QUALITY", 90),

		LogDir:   getEnv("LOG_DIR", "logs"),
		LogLevel: getEnv("LOG_LEVEL", "INFO"),

		BackendHost: getEnv("BACKEND_HOST", "0.0.0.0"),
		BackendPort: getInt("BACKEND_PORT", 8000),

		FrontendDist: getEnv("FRONTEND_DIST", "frontend/dist"),

		CORSOrigins: getEnv("CORS_ORIGINS", ""),
		ProjectRoot: projectRoot,
	}

	// Normalize paths relative to projectRoot
	if !filepath.IsAbs(cfg.StorageRoot) {
		cfg.StorageRoot = filepath.Join(projectRoot, cfg.StorageRoot)
	}
	if !filepath.IsAbs(cfg.LogDir) {
		cfg.LogDir = filepath.Join(projectRoot, cfg.LogDir)
	}
	if !filepath.IsAbs(cfg.FrontendDist) {
		cfg.FrontendDist = filepath.Join(projectRoot, cfg.FrontendDist)
	}

	return cfg, nil
}

// GetStorageRoot ensures the storage directory exists and returns its path.
func (c *Config) GetStorageRoot() string {
	_ = os.MkdirAll(c.StorageRoot, 0755)
	return c.StorageRoot
}

// GetPGXConnString converts DB_URL or postgres config into a pgx-compatible connection string.
func (c *Config) GetPGXConnString() string {
	raw := c.DBURL
	if raw == "" {
		return fmt.Sprintf("postgres://%s:%s@%s:%d/%s?sslmode=disable",
			c.PostgresUser, c.PostgresPassword, c.PostgresHost, c.PostgresPort, c.PostgresDB)
	}
	// If it starts with postgresql+psycopg:// or postgresql+psycopg2://, replace prefix with postgres://
	if strings.HasPrefix(raw, "postgresql+psycopg://") {
		return "postgres://" + strings.TrimPrefix(raw, "postgresql+psycopg://")
	}
	if strings.HasPrefix(raw, "postgresql+psycopg2://") {
		return "postgres://" + strings.TrimPrefix(raw, "postgresql+psycopg2://")
	}
	if strings.HasPrefix(raw, "postgresql://") {
		return "postgres://" + strings.TrimPrefix(raw, "postgresql://")
	}
	return raw
}

// IsSecureCookies returns true if SECURE_COOKIES is true or PublicBaseURL starts with https
func (c *Config) IsSecureCookies() bool {
	return c.SecureCookies || strings.HasPrefix(strings.ToLower(c.PublicBaseURL), "https://")
}
