package util

import (
	"testing"
	"time"
)

func TestCursor_EncodeAndDecode(t *testing.T) {
	now := time.Date(2026, 9, 9, 12, 30, 45, 0, time.UTC)
	postID := 42

	encoded := EncodeCursor(now, postID)
	if encoded == "" {
		t.Fatalf("encoded cursor is empty")
	}

	decodedTime, decodedID, err := DecodeCursor(encoded)
	if err != nil {
		t.Fatalf("DecodeCursor failed: %v", err)
	}

	if decodedID != postID {
		t.Errorf("decoded ID mismatch: got %d, want %d", decodedID, postID)
	}

	if !decodedTime.Equal(now) {
		t.Errorf("decoded Time mismatch: got %v, want %v", decodedTime, now)
	}
}

func TestCursor_Invalid(t *testing.T) {
	invalidCursors := []string{
		"",
		"not-base64!",
		"dGVzdA==",             // "test" (no pipe)
		"MjAyNi0wOS0wOXxpZA==", // invalid date format
		"MjAyNi0wOS0wOSAxMjozMDo0NXxub3RpZA==", // non-integer ID
	}

	for _, c := range invalidCursors {
		_, _, err := DecodeCursor(c)
		if err == nil {
			t.Errorf("expected error for invalid cursor %q, got nil", c)
		}
	}
}
