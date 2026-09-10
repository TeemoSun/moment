package util

import (
	"errors"
	"fmt"
	"strconv"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type JWTClaims struct {
	UserID       int    `json:"sub"`
	Role         string `json:"role"`
	TokenVersion int    `json:"ver"`
	jwt.RegisteredClaims
}

// CreateAccessToken creates an HS256 signed JWT.
// Payload matches Python: {"sub": str(user_id), "role": role, "ver": token_version, "iat": now, "exp": now + days}
func CreateAccessToken(secret string, userID int, role string, tokenVersion int, expireDays int) (string, error) {
	now := time.Now().UTC()
	exp := now.Add(time.Duration(expireDays) * 24 * time.Hour)

	claims := jwt.MapClaims{
		"sub":  strconv.Itoa(userID),
		"role": role,
		"ver":  tokenVersion,
		"iat":  now.Unix(),
		"exp":  exp.Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	signed, err := token.SignedString([]byte(secret))
	if err != nil {
		return "", fmt.Errorf("failed to sign token: %w", err)
	}
	return signed, nil
}

// DecodeAccessToken parses and validates an HS256 JWT, returning (userID, role, tokenVersion, error).
func DecodeAccessToken(secret string, tokenStr string) (userID int, role string, tokenVersion int, err error) {
	token, err := jwt.Parse(tokenStr, func(token *jwt.Token) (any, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(secret), nil
	})
	if err != nil {
		return 0, "", 0, err
	}

	if !token.Valid {
		return 0, "", 0, errors.New("invalid token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return 0, "", 0, errors.New("invalid token claims")
	}

	subRaw, ok := claims["sub"]
	if !ok {
		return 0, "", 0, errors.New("missing sub in token")
	}

	var uid int
	switch v := subRaw.(type) {
	case string:
		var err error
		uid, err = strconv.Atoi(v)
		if err != nil {
			return 0, "", 0, errors.New("invalid sub in token")
		}
	case float64:
		uid = int(v)
	default:
		return 0, "", 0, errors.New("unknown sub format in token")
	}

	roleStr, _ := claims["role"].(string)

	var ver int
	if verRaw, ok := claims["ver"]; ok {
		if verFloat, ok := verRaw.(float64); ok {
			ver = int(verFloat)
		} else if verInt, ok := verRaw.(int); ok {
			ver = verInt
		}
	}

	return uid, roleStr, ver, nil
}
