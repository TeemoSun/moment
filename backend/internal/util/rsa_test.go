package util

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"testing"
)

func TestRSA_GenerateAndDecrypt(t *testing.T) {
	pubPEM, privPEM, err := GenerateRSAKeyPair()
	if err != nil {
		t.Fatalf("GenerateRSAKeyPair failed: %v", err)
	}

	block, _ := pem.Decode([]byte(pubPEM))
	if block == nil {
		t.Fatalf("failed to decode public key PEM")
	}
	pubInterface, err := x509.ParsePKIXPublicKey(block.Bytes)
	if err != nil {
		t.Fatalf("failed to parse PKIX public key: %v", err)
	}
	pubKey, ok := pubInterface.(*rsa.PublicKey)
	if !ok {
		t.Fatalf("key is not rsa.PublicKey")
	}

	originalMessage := "HelloMoments2026!#"
	cipherBytes, err := rsa.EncryptPKCS1v15(rand.Reader, pubKey, []byte(originalMessage))
	if err != nil {
		t.Fatalf("EncryptPKCS1v15 failed: %v", err)
	}

	cipherB64 := base64.StdEncoding.EncodeToString(cipherBytes)

	decrypted, err := RSADecrypt(privPEM, cipherB64)
	if err != nil {
		t.Fatalf("RSADecrypt failed: %v", err)
	}

	if decrypted != originalMessage {
		t.Errorf("decrypted message mismatch: got %q, want %q", decrypted, originalMessage)
	}
}

func TestRSA_InvalidCiphertext(t *testing.T) {
	_, privPEM, err := GenerateRSAKeyPair()
	if err != nil {
		t.Fatalf("GenerateRSAKeyPair failed: %v", err)
	}

	// Invalid base64
	_, err = RSADecrypt(privPEM, "!!not-valid-base64!!")
	if err == nil {
		t.Errorf("expected error for invalid base64, got nil")
	}

	// Corrupted ciphertext
	badCipher := base64.StdEncoding.EncodeToString([]byte("short-invalid-ciphertext"))
	_, err = RSADecrypt(privPEM, badCipher)
	if err == nil {
		t.Errorf("expected error for corrupted ciphertext, got nil")
	}
}
