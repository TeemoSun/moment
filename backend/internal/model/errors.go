package model

import "fmt"

// Error codes matching app.schemas.common.ErrorCode
const (
	ErrAuthRequired          = "AUTH_REQUIRED"
	ErrInvalidCredentials    = "INVALID_CREDENTIALS"
	ErrAccountLocked         = "ACCOUNT_LOCKED"
	ErrAccountDeactivated    = "ACCOUNT_DEACTIVATED"
	ErrAccountDisabled       = "ACCOUNT_DISABLED"
	ErrAdminRequired         = "ADMIN_REQUIRED"
	ErrCSRFFailed            = "CSRF_FAILED"
	ErrNotInitializedNeeded  = "NOT_INITIALIZED_NEEDED"
	ErrAlreadyInitialized    = "ALREADY_INITIALIZED"
	ErrRSADecryptFailed      = "RSA_DECRYPT_FAILED"
	ErrInvalidInvite         = "INVALID_INVITE"
	ErrInviteNotFound        = "INVITE_NOT_FOUND"
	ErrInviteDisabled        = "INVITE_DISABLED"
	ErrActiveInviteExists    = "ACTIVE_INVITE_EXISTS"
	ErrInviteAlreadyUsed     = "INVITE_ALREADY_USED"
	ErrEmailExists           = "EMAIL_EXISTS"
	ErrValidationError       = "VALIDATION_ERROR"
	ErrNotFound              = "NOT_FOUND"
	ErrForbidden             = "FORBIDDEN"
	ErrPasswordTooWeak       = "PASSWORD_TOO_WEAK"
	ErrFileTooLarge          = "FILE_TOO_LARGE"
	ErrUnsupportedMedia      = "UNSUPPORTED_MEDIA"
	ErrMediaNotReady         = "MEDIA_NOT_READY"
	ErrMediaNotOwned         = "MEDIA_NOT_OWNED"
	ErrMediaAlreadyUsed      = "MEDIA_ALREADY_USED"
	ErrInvalidCursor         = "INVALID_CURSOR"
	ErrDuplicateLike         = "DUPLICATE_LIKE"
	ErrAlreadyLiked          = "ALREADY_LIKED"
	ErrNotLiked              = "NOT_LIKED"
	ErrCommentNotFound       = "COMMENT_NOT_FOUND"
	ErrEmptyComment          = "EMPTY_COMMENT"
	ErrFriendRequestExists   = "FRIEND_REQUEST_EXISTS"
	ErrAlreadyFriends        = "ALREADY_FRIENDS"
	ErrCannotFriendSelf      = "CANNOT_FRIEND_SELF"
	ErrUserNotFound          = "USER_NOT_FOUND"
	ErrFriendRequestNotFound = "FRIEND_REQUEST_NOT_FOUND"
	ErrNotFriends            = "NOT_FRIENDS"
	ErrBotNotFound           = "BOT_NOT_FOUND"
	ErrBotLoginForbidden     = "BOT_LOGIN_FORBIDDEN"
	ErrRateLimited           = "RATE_LIMITED"
	ErrInternal              = "INTERNAL"
)

// ErrorOut represents the standard JSON error structure:
// {"code": "...", "message": "...", "detail": {}}
type ErrorOut struct {
	Code    string         `json:"code"`
	Message string         `json:"message"`
	Detail  map[string]any `json:"detail"`
}

// AppError is the custom application error with HTTP status code and details.
type AppError struct {
	Code       string         `json:"code"`
	Message    string         `json:"message"`
	StatusCode int            `json:"-"`
	Detail     map[string]any `json:"detail"`
}

func (e *AppError) Error() string {
	return fmt.Sprintf("[%s] %s (HTTP %d)", e.Code, e.Message, e.StatusCode)
}

// NewAppError creates a new AppError with an empty detail map if nil.
func NewAppError(code, message string, statusCode int, detail ...map[string]any) *AppError {
	var d map[string]any
	if len(detail) > 0 && detail[0] != nil {
		d = detail[0]
	} else {
		d = make(map[string]any)
	}
	return &AppError{
		Code:       code,
		Message:    message,
		StatusCode: statusCode,
		Detail:     d,
	}
}

// ToResponse returns an ErrorOut with Detail guaranteed non-nil.
func (e *AppError) ToResponse() ErrorOut {
	d := e.Detail
	if d == nil {
		d = make(map[string]any)
	}
	return ErrorOut{
		Code:    e.Code,
		Message: e.Message,
		Detail:  d,
	}
}
