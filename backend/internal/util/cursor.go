package util

import (
	"encoding/base64"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"
)

const CursorTimeFormat = "2006-01-02 15:04:05"

// EncodeCursor encodes (createdAt, postID) into a URL-safe Base64 string: "YYYY-MM-DD HH:MM:SS|id".
func EncodeCursor(createdAt time.Time, postID int) string {
	s := createdAt.Truncate(time.Second).Format(CursorTimeFormat)
	payload := fmt.Sprintf("%s|%d", s, postID)
	return base64.URLEncoding.EncodeToString([]byte(payload))
}

// DecodeCursor decodes a cursor string into (time.Time, postID).
func DecodeCursor(cursor string) (time.Time, int, error) {
	b, err := base64.URLEncoding.DecodeString(cursor)
	if err != nil {
		b, err = base64.RawURLEncoding.DecodeString(cursor)
		if err != nil {
			return time.Time{}, 0, errors.New("invalid base64 in cursor")
		}
	}

	parts := strings.Split(string(b), "|")
	if len(parts) != 2 {
		return time.Time{}, 0, errors.New("invalid cursor format")
	}

	t, err := time.ParseInLocation(CursorTimeFormat, parts[0], time.UTC)
	if err != nil {
		return time.Time{}, 0, errors.New("invalid date in cursor")
	}

	id, err := strconv.Atoi(parts[1])
	if err != nil {
		return time.Time{}, 0, errors.New("invalid id in cursor")
	}

	return t, id, nil
}
