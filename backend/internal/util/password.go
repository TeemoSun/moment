package util

import (
	"unicode"

	"golang.org/x/crypto/bcrypt"
)

// ValidatePassword validates password complexity:
// - Length 8-128
// - At least 2 categories of: digits, letters, symbols (printable non-alphanumeric)
// Returns list of error messages; empty if valid.
func ValidatePassword(plain string) []string {
	var errors []string
	runes := []rune(plain)
	if len(runes) < 8 {
		errors = append(errors, "密码至少需要 8 个字符")
	}
	if len(runes) > 128 {
		errors = append(errors, "密码最多 128 个字符")
	}

	var hasDigit, hasAlpha, hasSymbol bool
	for _, r := range runes {
		if unicode.IsDigit(r) {
			hasDigit = true
		} else if unicode.IsLetter(r) {
			hasAlpha = true
		} else if unicode.IsPrint(r) && !unicode.IsLetter(r) && !unicode.IsDigit(r) {
			hasSymbol = true
		}
	}

	categories := 0
	if hasDigit {
		categories++
	}
	if hasAlpha {
		categories++
	}
	if hasSymbol {
		categories++
	}

	if categories < 2 {
		errors = append(errors, "密码需至少包含数字、字母、符号中的两类")
	}

	return errors
}

// HashPassword hashes a plain text password using bcrypt with cost 12.
func HashPassword(plain string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(plain), 12)
	if err != nil {
		return "", err
	}
	return string(bytes), nil
}

// VerifyPassword checks whether a plain password matches its bcrypt hash.
func VerifyPassword(plain, hashed string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hashed), []byte(plain)) == nil
}
