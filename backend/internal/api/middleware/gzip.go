package middleware

import (
	"net/http"

	chimiddleware "github.com/go-chi/chi/v5/middleware"
)

func GZip(next http.Handler) http.Handler {
	return chimiddleware.Compress(5)(next)
}
