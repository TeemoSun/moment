import { upload } from "./client";

export interface MediaUploadOut {
  media_id: number;
  kind: string;
  format: string;
  size: number;
  status: string;
  created_at: string;
}

export function uploadMedia(file: File): Promise<MediaUploadOut> {
  const formData = new FormData();
  formData.append("file", file);
  return upload<MediaUploadOut>("/api/v1/media/upload", formData);
}

export function mediaUrl(
  postId: number,
  mediaId: number,
  spec: "thumb" | "large" | "original",
): string {
  return `/api/v1/posts/${postId}/media/${mediaId}/${spec}`;
}
