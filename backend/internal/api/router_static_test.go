package api

import (
	"bytes"
	"compress/gzip"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"backend/internal/config"
)

func TestStaticAssetsServing(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "frontend_dist_*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// index.html
	indexHTML := []byte("<!DOCTYPE html><html><head><title>Moments</title></head><body><div id='root'></div></body></html>")
	if err := os.WriteFile(filepath.Join(tmpDir, "index.html"), indexHTML, 0644); err != nil {
		t.Fatal(err)
	}

	assetsDir := filepath.Join(tmpDir, "assets")
	if err := os.MkdirAll(assetsDir, 0755); err != nil {
		t.Fatal(err)
	}

	jsContent := []byte("console.log('hello world from js'); " + string(bytes.Repeat([]byte("var x = 123; "), 50)))
	jsPath := filepath.Join(assetsDir, "app.js")
	if err := os.WriteFile(jsPath, jsContent, 0644); err != nil {
		t.Fatal(err)
	}

	// Create gz version
	var gzBuf bytes.Buffer
	gw := gzip.NewWriter(&gzBuf)
	gw.Write(jsContent)
	gw.Close()
	if err := os.WriteFile(jsPath+".gz", gzBuf.Bytes(), 0644); err != nil {
		t.Fatal(err)
	}

	// Create br version
	brContent := append([]byte("BROTLI_DATA:"), jsContent...)
	if err := os.WriteFile(jsPath+".br", brContent, 0644); err != nil {
		t.Fatal(err)
	}

	// CSS file
	cssContent := []byte("body { background: red; margin: 0; padding: 0; }")
	cssPath := filepath.Join(assetsDir, "style.css")
	if err := os.WriteFile(cssPath, cssContent, 0644); err != nil {
		t.Fatal(err)
	}
	cssBrContent := append([]byte("BR_CSS:"), cssContent...)
	if err := os.WriteFile(cssPath+".br", cssBrContent, 0644); err != nil {
		t.Fatal(err)
	}

	// Font file (binary)
	woff2Content := []byte("wOF2\x00\x01\x00\x00fontdatahere")
	woff2Path := filepath.Join(assetsDir, "font.woff2")
	if err := os.WriteFile(woff2Path, woff2Content, 0644); err != nil {
		t.Fatal(err)
	}

	cfg := &config.Config{
		FrontendDist: tmpDir,
	}

	router := NewRouter(cfg, nil, nil, nil, nil)

	// 1. Request JS with Accept-Encoding: gzip, deflate, br
	t.Run("JS with Accept-Encoding: gzip, deflate, br", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/assets/app.js", nil)
		req.Header.Set("Accept-Encoding", "gzip, deflate, br")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		res := rec.Result()
		body, _ := io.ReadAll(res.Body)
		t.Logf("Status: %d, Content-Encoding: %s, Content-Type: %s, Length: %d",
			res.StatusCode, res.Header.Get("Content-Encoding"), res.Header.Get("Content-Type"), len(body))

		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", res.StatusCode)
		}

		enc := res.Header.Get("Content-Encoding")
		if enc == "br" {
			if !bytes.Equal(body, brContent) {
				t.Fatalf("body does not match br content! body prefix: %x (expected: %x)", body[:min(len(body), 20)], brContent[:min(len(brContent), 20)])
			}
		}
	})

	// 2. Request CSS with Accept-Encoding: gzip, deflate, br
	t.Run("CSS with Accept-Encoding: gzip, deflate, br", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/assets/style.css", nil)
		req.Header.Set("Accept-Encoding", "gzip, deflate, br")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		res := rec.Result()
		body, _ := io.ReadAll(res.Body)

		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", res.StatusCode)
		}

		enc := res.Header.Get("Content-Encoding")
		if enc == "br" {
			if !bytes.Equal(body, cssBrContent) {
				t.Fatalf("body does not match br content!")
			}
		}
	})

	// 3. Request JS with Accept-Encoding: gzip
	t.Run("JS with Accept-Encoding: gzip", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/assets/app.js", nil)
		req.Header.Set("Accept-Encoding", "gzip")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		res := rec.Result()
		body, _ := io.ReadAll(res.Body)

		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", res.StatusCode)
		}

		enc := res.Header.Get("Content-Encoding")
		if enc == "gzip" {
			gr, err := gzip.NewReader(bytes.NewReader(body))
			if err != nil {
				t.Fatalf("failed to create gzip reader: %v", err)
			}
			decompressed, err := io.ReadAll(gr)
			if err != nil {
				t.Fatalf("failed to decompress gzip body: %v", err)
			}
			if !bytes.Equal(decompressed, jsContent) {
				t.Fatalf("decompressed content does not match original js content!")
			}
		}
	})

	// 4. Request font.woff2
	t.Run("Font file woff2", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/assets/font.woff2", nil)
		req.Header.Set("Accept-Encoding", "gzip, deflate, br")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		res := rec.Result()
		body, _ := io.ReadAll(res.Body)

		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", res.StatusCode)
		}

		// Font must not be corrupted
		if !bytes.Equal(body, woff2Content) {
			t.Fatalf("woff2 body corrupted!")
		}
	})

	// 5. SPA Fallback route: /feed -> index.html
	t.Run("SPA Fallback /feed", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/feed", nil)
		req.Header.Set("Accept-Encoding", "gzip, deflate, br")
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		res := rec.Result()
		body, _ := io.ReadAll(res.Body)

		if res.StatusCode != http.StatusOK {
			t.Fatalf("expected 200, got %d", res.StatusCode)
		}

		// If gzipped by Chi dynamic compression, decompress it
		if res.Header.Get("Content-Encoding") == "gzip" {
			gr, err := gzip.NewReader(bytes.NewReader(body))
			if err != nil {
				t.Fatalf("invalid gzip: %v", err)
			}
			body, _ = io.ReadAll(gr)
		}

		if !bytes.Equal(body, indexHTML) {
			t.Fatalf("expected index.html, got: %s", string(body))
		}
	})

	// 6. API 404 should NOT fallback to SPA
	t.Run("API 404 not fallback to SPA", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/unknown_endpoint", nil)
		rec := httptest.NewRecorder()

		router.ServeHTTP(rec, req)

		res := rec.Result()
		if res.StatusCode != http.StatusNotFound {
			t.Fatalf("expected 404, got %d", res.StatusCode)
		}
	})
}
