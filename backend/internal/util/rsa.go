package util

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"errors"
	"fmt"
)

// GenerateRSAKeyPair generates a 2048-bit RSA keypair in PEM format.
// Private key is in PKCS#8 format; public key is in SubjectPublicKeyInfo format.
func GenerateRSAKeyPair() (publicKeyPEM string, privateKeyPEM string, err error) {
	privKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return "", "", fmt.Errorf("failed to generate RSA key: %w", err)
	}

	// Marshal private key to PKCS#8
	privBytes, err := x509.MarshalPKCS8PrivateKey(privKey)
	if err != nil {
		return "", "", fmt.Errorf("failed to marshal PKCS#8 private key: %w", err)
	}
	privPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "PRIVATE KEY",
		Bytes: privBytes,
	})

	// Marshal public key to PKIX SubjectPublicKeyInfo
	pubBytes, err := x509.MarshalPKIXPublicKey(&privKey.PublicKey)
	if err != nil {
		return "", "", fmt.Errorf("failed to marshal PKIX public key: %w", err)
	}
	pubPEM := pem.EncodeToMemory(&pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: pubBytes,
	})

	return string(pubPEM), string(privPEM), nil
}

// RSADecrypt decrypts a base64-encoded ciphertext with RSA PKCS1v15 padding.
// Matches Python `loaded.decrypt(ciphertext, padding.PKCS1v15())` and frontend JSEncrypt.
func RSADecrypt(privateKeyPEM string, ciphertextB64 string) (string, error) {
	// 1. Decode base64 ciphertext
	ciphertext, err := base64.StdEncoding.DecodeString(ciphertextB64)
	if err != nil {
		ciphertext, err = base64.RawStdEncoding.DecodeString(ciphertextB64)
		if err != nil {
			return "", fmt.Errorf("invalid base64 ciphertext: %w", err)
		}
	}

	// 2. Decode PEM private key
	block, _ := pem.Decode([]byte(privateKeyPEM))
	if block == nil {
		return "", errors.New("failed to decode PEM block containing private key")
	}

	// 3. Parse private key (supporting PKCS#8 and PKCS#1)
	var privKey *rsa.PrivateKey
	if key, err := x509.ParsePKCS8PrivateKey(block.Bytes); err == nil {
		var ok bool
		privKey, ok = key.(*rsa.PrivateKey)
		if !ok {
			return "", errors.New("parsed key is not an RSA private key")
		}
	} else if key, err := x509.ParsePKCS1PrivateKey(block.Bytes); err == nil {
		privKey = key
	} else {
		return "", fmt.Errorf("failed to parse private key: %w", err)
	}

	// 4. Decrypt with PKCS#1 v1.5 padding
	plaintext, err := rsa.DecryptPKCS1v15(nil, privKey, ciphertext)
	if err != nil {
		return "", fmt.Errorf("RSA PKCS1v15 decryption failed: %w", err)
	}

	return string(plaintext), nil
}
