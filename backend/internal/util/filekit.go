package util

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/h2non/filetype"
)

var (
	DangerousMIMEs = map[string]bool{
		"application/x-dosexec":       true,
		"application/x-executable":    true,
		"application/x-msdos-program": true,
		"application/x-elf":           true,
		"application/x-mach-binary":   true,
	}

	SupportedImageFormats = map[string]bool{
		"jpeg": true,
		"jpg":  true,
		"png":  true,
		"webp": true,
		"gif":  true,
	}

	SupportedVideoFormats = map[string]bool{
		"mp4":  true,
		"mov":  true,
		"webm": true,
		"avi":  true,
	}
)

// DetectKind detects kind ("image" or "video"), extension, and MIME type from file header.
func DetectKind(header []byte) (kind string, ext string, mime string, err error) {
	t, err := filetype.Match(header)
	if err != nil || t == filetype.Unknown {
		return "", "", "", errors.New("unsupported file type")
	}

	if DangerousMIMEs[t.MIME.Value] {
		return "", "", "", errors.New("dangerous file type rejected")
	}

	mime = t.MIME.Value
	ext = strings.ToLower(t.Extension)

	if strings.HasPrefix(mime, "image/") {
		if ext == "jpg" {
			ext = "jpeg"
		}
		if !SupportedImageFormats[ext] {
			return "", "", "", fmt.Errorf("unsupported image format: %s", ext)
		}
		return "image", ext, mime, nil
	}

	if strings.HasPrefix(mime, "video/") {
		if !SupportedVideoFormats[ext] {
			return "", "", "", fmt.Errorf("unsupported video format: %s", ext)
		}
		return "video", ext, mime, nil
	}

	return "", "", "", errors.New("unsupported file type")
}

// GenerateFilename generates a filename: timestamp_6hex.ext
func GenerateFilename(ext string) string {
	b := make([]byte, 3)
	_, _ = rand.Read(b)
	hexStr := hex.EncodeToString(b)
	ext = strings.TrimPrefix(ext, ".")
	return fmt.Sprintf("%d_%s.%s", time.Now().Unix(), hexStr, ext)
}

// GetMediaDir returns storage/media/YYYY-MM/ and ensures directory exists.
func GetMediaDir(storageRoot string) (string, error) {
	dir := filepath.Join(storageRoot, "media", time.Now().Format("2006-01"))
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", err
	}
	return dir, nil
}

// GetAvatarsDir returns storage/avatars/ and ensures directory exists.
func GetAvatarsDir(storageRoot string) (string, error) {
	dir := filepath.Join(storageRoot, "avatars")
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", err
	}
	return dir, nil
}

// SafeSaveBytes saves content to directory with filename.
// If file exists, re-generates filename with new random hex.
func SafeSaveBytes(dir, filename string, content []byte) (absPath string, finalName string, err error) {
	ext := filepath.Ext(filename)
	ext = strings.TrimPrefix(ext, ".")
	target := filepath.Join(dir, filename)
	curName := filename

	for {
		if _, err := os.Stat(target); os.IsNotExist(err) {
			break
		}
		curName = GenerateFilename(ext)
		target = filepath.Join(dir, curName)
	}

	if err := os.WriteFile(target, content, 0644); err != nil {
		return "", "", err
	}
	return target, curName, nil
}

// ResolveWithinStorage validates relPath is within storageRoot and exists as a regular file.
// Protects against path traversal attacks.
func ResolveWithinStorage(storageRoot, relPath string) (string, bool) {
	absRoot, err := filepath.Abs(storageRoot)
	if err != nil {
		return "", false
	}
	target := filepath.Clean(filepath.Join(absRoot, relPath))
	rel, err := filepath.Rel(absRoot, target)
	if err != nil || strings.HasPrefix(rel, "..") || rel == "." {
		return "", false
	}
	info, err := os.Stat(target)
	if err != nil || info.IsDir() {
		return "", false
	}
	return target, true
}

// StreamToFile streams from reader to destPath, enforcing maxBytes limit.
func StreamToFile(r io.Reader, destPath string, maxBytes int64, storageRoot string) (int64, error) {
	absRoot, err := filepath.Abs(storageRoot)
	if err != nil {
		return 0, errors.New("invalid storage root")
	}
	absDest, err := filepath.Abs(destPath)
	if err != nil {
		return 0, errors.New("invalid destination path")
	}
	rel, err := filepath.Rel(absRoot, absDest)
	if err != nil || strings.HasPrefix(rel, "..") {
		return 0, errors.New("destination escapes storage root")
	}

	out, err := os.Create(absDest)
	if err != nil {
		return 0, err
	}
	defer out.Close()

	var total int64
	buf := make([]byte, 1024*1024) // 1MB buffer
	for {
		n, err := r.Read(buf)
		if n > 0 {
			total += int64(n)
			if total > maxBytes {
				_ = out.Close()
				_ = os.Remove(absDest)
				return total, errors.New("file too large")
			}
			if _, werr := out.Write(buf[:n]); werr != nil {
				_ = os.Remove(absDest)
				return total, werr
			}
		}
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			_ = os.Remove(absDest)
			return total, err
		}
	}

	return total, nil
}
