package util

import (
	"strings"
	"testing"
)

func TestPassword_Validation(t *testing.T) {
	tests := []struct {
		name      string
		password  string
		wantValid bool
	}{
		{"Too short", "12345", false},
		{"Too long", strings.Repeat("a", 129), false},
		{"Only digits", "12345678", false},
		{"Only letters", "abcdefgh", false},
		{"Letters and digits", "secret123", true},
		{"Letters and symbols", "secret!@#", true},
		{"Digits and symbols", "12345!@#", true},
		{"All three", "Secret123!", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			errs := ValidatePassword(tt.password)
			isValid := len(errs) == 0
			if isValid != tt.wantValid {
				t.Errorf("ValidatePassword(%q) valid = %v, want %v (errors: %v)", tt.password, isValid, tt.wantValid, errs)
			}
		})
	}
}

func TestPassword_HashAndVerify(t *testing.T) {
	plain := "ValidPass123!"
	hashed, err := HashPassword(plain)
	if err != nil {
		t.Fatalf("HashPassword failed: %v", err)
	}

	if !VerifyPassword(plain, hashed) {
		t.Errorf("VerifyPassword failed for correct password")
	}

	if VerifyPassword("WrongPass123!", hashed) {
		t.Errorf("VerifyPassword returned true for wrong password")
	}
}
