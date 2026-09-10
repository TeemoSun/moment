package middleware

import (
	"encoding/json"
	"log"
	"net/http"
	"runtime/debug"

	"backend/internal/model"
)

func Recover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rvr := recover(); rvr != nil {
				log.Printf("[Panic Recovered] %v\nStack: %s", rvr, string(debug.Stack()))
				w.Header().Set("Content-Type", "application/json; charset=utf-8")
				w.WriteHeader(http.StatusInternalServerError)
				errResp := model.ErrorOut{
					Code:    model.ErrInternal,
					Message: "服务器内部错误",
					Detail:  make(map[string]any),
				}
				_ = json.NewEncoder(w).Encode(errResp)
			}
		}()
		next.ServeHTTP(w, r)
	})
}
