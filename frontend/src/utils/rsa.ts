import JSEncrypt from "jsencrypt";

export function encryptPassword(publicKeyPem: string, password: string): string {
  const enc = new JSEncrypt();
  enc.setPublicKey(publicKeyPem);
  const out = enc.encrypt(password);
  if (out === false) {
    throw new Error("RSA encrypt failed");
  }
  return out;
}
