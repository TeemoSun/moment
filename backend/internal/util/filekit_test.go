package util

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFilekit_DetectKind(t *testing.T) {
	// PNG signature
	pngHeader := []byte{0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52}
	kind, ext, mime, err := DetectKind(pngHeader)
	if err != nil {
		t.Fatalf("DetectKind failed for PNG: %v", err)
	}
	if kind != "image" || ext != "png" || mime != "image/png" {
		t.Errorf("DetectKind PNG mismatch: got kind=%s, ext=%s, mime=%s", kind, ext, mime)
	}

	// JPEG signature
	jpegHeader := []byte{0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01}
	kind, ext, _, err = DetectKind(jpegHeader)
	if err != nil {
		t.Fatalf("DetectKind failed for JPEG: %v", err)
	}
	if kind != "image" || (ext != "jpeg" && ext != "jpg") {
		t.Errorf("DetectKind JPEG mismatch: got kind=%s, ext=%s", kind, ext)
	}

	// Dangerous executable (ELF)
	elfHeader := []byte{0x7F, 0x45, 0x4C, 0x46, 0x02, 0x01, 0x01, 0x00}
	_, _, _, err = DetectKind(elfHeader)
	if err == nil {
		t.Errorf("expected error for ELF dangerous file, got nil")
	}

	// Random text / unsupported
	_, _, _, err = DetectKind([]byte("Hello world plain text"))
	if err == nil {
		t.Errorf("expected error for plain text, got nil")
	}
}

func TestFilekit_GenerateFilename(t *testing.T) {
	name := GenerateFilename("png")
	if !strings.HasSuffix(name, ".png") {
		t.Errorf("expected suffix .png, got %s", name)
	}
	if !strings.Contains(name, "_") {
		t.Errorf("expected filename containing underscore: %s", name)
	}
}

func TestFilekit_ResolveWithinStorage(t *testing.T) {
	tempDir, err := os.MkdirTemp("", "storage_test_*")
	if err != nil {
		t.Fatalf("failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tempDir)

	testFile := filepath.Join(tempDir, "test.txt")
	if err := os.WriteFile(testFile, []byte("ok"), 0644); err != nil {
		t.Fatalf("failed to write test file: %v", err)
	}

	// Valid path within storage
	resolved, ok := ResolveWithinStorage(tempDir, "test.txt")
	if !ok || resolved != testFile {
		t.Errorf("ResolveWithinStorage valid file failed: got %v, %v", resolved, ok)
	}

	// Traversal attempt
	_, ok = ResolveWithinStorage(tempDir, "../../../etc/passwd")
	if ok {
		t.Errorf("ResolveWithinStorage allowed path traversal!")
	}

	// Non-existent file
	_, ok = ResolveWithinStorage(tempDir, "doesnotexist.txt")
	if ok {
		t.Errorf("ResolveWithinStorage returned true for non-existent file")
	}
}
