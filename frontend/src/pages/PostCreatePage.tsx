import { useState, useRef, useEffect, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Title, Radio } from "animal-island-ui";
import { usePostsStore } from "@/stores/posts";
import { createPost } from "@/api/posts";
import { uploadMedia } from "@/api/media";
import { ApiError } from "@/api/client";
import { notify } from "@/utils/notify";

interface MediaItem {
  id: string;
  mediaId: number | null;
  previewUrl: string;
  kind: string;
  uploading: boolean;
}

export default function PostCreatePage() {
  const navigate = useNavigate();
  const { prependPost } = usePostsStore();

  const [content, setContent] = useState("");
  const [visibility, setVisibility] = useState<"public" | "friends">("public");
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaItemsRef = useRef(mediaItems);
  mediaItemsRef.current = mediaItems;

  useEffect(() => {
    return () => {
      mediaItemsRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl));
    };
  }, []);

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const remaining = 9 - mediaItems.length;
    if (remaining <= 0) return;

    const filesToUpload = Array.from(files).slice(0, remaining);
    setUploading(true);
    setError("");

    for (const file of filesToUpload) {
      const previewUrl = URL.createObjectURL(file);
      const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const kind = file.type.startsWith("video/") ? "video" : "image";

      setMediaItems((prev) => [
        ...prev,
        { id: tempId, mediaId: null, previewUrl, kind, uploading: true },
      ]);

      try {
        const res = await uploadMedia(file);
        setMediaItems((prev) =>
          prev.map((item) =>
            item.id === tempId ? { ...item, mediaId: res.media_id, uploading: false } : item,
          ),
        );
      } catch {
        setMediaItems((prev) => prev.filter((item) => item.id !== tempId));
        URL.revokeObjectURL(previewUrl);
        setError("部分文件上传失败");
      }
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleRemoveMedia = (id: string) => {
    const item = mediaItems.find((m) => m.id === id);
    if (item) URL.revokeObjectURL(item.previewUrl);
    setMediaItems((prev) => prev.filter((m) => m.id !== id));
  };

  const handleSubmit = async () => {
    const validMediaIds = mediaItems.filter((m) => m.mediaId !== null).map((m) => m.mediaId!);

    if (!content.trim()) {
      setError("请输入文字内容");
      return;
    }

    if (mediaItems.some((m) => m.uploading)) {
      setError("请等待文件上传完成");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const post = await createPost({
        content: content.trim(),
        media_ids: validMediaIds,
        visibility,
      });
      prependPost(post);
      notify.success("发布成功");
      navigate("/feed");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "发布失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
      <Title color="app-green">发动态</Title>

      <Card style={{ marginTop: 24 }}>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="分享你的想法..."
          maxLength={2000}
          style={{
            width: "100%",
            minHeight: 120,
            padding: "14px 18px",
            background: "rgb(247, 243, 223)",
            border: "2.5px solid #c4b89e",
            borderRadius: 18,
            color: "#725d42",
            fontWeight: 500,
            fontSize: 15,
            lineHeight: 1.6,
            resize: "vertical",
            outline: "none",
            fontFamily: "Nunito, 'Noto Sans SC', sans-serif",
            boxSizing: "border-box",
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "#ffcc00";
            e.target.style.boxShadow =
              "0 3px 0 0 #e0b800, 0 0 0 3px rgba(255, 204, 0, 0.15)";
          }}
          onBlur={(e) => {
            e.target.style.borderColor = "#c4b89e";
            e.target.style.boxShadow = "none";
          }}
        />
        <div
          style={{
            textAlign: "right",
            color: content.length > 1900 ? "#e05a5a" : "#9f927d",
            fontSize: 13,
            fontWeight: 500,
            marginTop: 4,
          }}
        >
          {content.length} / 2000
        </div>

        <div style={{ marginTop: 16 }}>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp,image/gif,video/mp4,video/quicktime"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
          <Button
            type="dashed"
            size="small"
            onClick={() => fileInputRef.current?.click()}
            disabled={mediaItems.length >= 9 || uploading}
          >
            添加图片/视频 ({mediaItems.length}/9)
          </Button>
        </div>

        {mediaItems.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: mediaItems.length <= 4 ? "repeat(2, 1fr)" : "repeat(3, 1fr)",
              gap: 8,
              marginTop: 12,
            }}
          >
            {mediaItems.map((item) => (
              <div
                key={item.id}
                style={{
                  aspectRatio: "1",
                  borderRadius: 12,
                  overflow: "hidden",
                  position: "relative",
                  background: "#f0e8d8",
                }}
              >
                {item.kind === "image" ? (
                  <img
                    src={item.previewUrl}
                    alt=""
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                ) : (
                  <video
                    src={item.previewUrl}
                    muted
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                )}
                {item.uploading && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      background: "rgba(0,0,0,0.3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#fff",
                      fontWeight: 600,
                      fontSize: 13,
                    }}
                  >
                    上传中...
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => handleRemoveMedia(item.id)}
                  style={{
                    position: "absolute",
                    top: 4,
                    right: 4,
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    background: "rgba(0,0,0,0.5)",
                    color: "#fff",
                    border: "none",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 14,
                    fontWeight: 700,
                    lineHeight: 1,
                    padding: 0,
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontWeight: 600, color: "#794f27", fontSize: 14 }}>可见范围：</span>
          <Radio
            options={[
              { label: "公开", value: "public" },
              { label: "仅好友", value: "friends" },
            ]}
            value={visibility}
            onChange={(v) => setVisibility(v as "public" | "friends")}
          />
        </div>

        {error && (
          <div style={{ marginTop: 12, color: "#e05a5a", fontWeight: 500, fontSize: 14 }}>
            {error}
          </div>
        )}

        <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
          <Button type="primary" onClick={handleSubmit} loading={submitting} disabled={uploading}>
            发布
          </Button>
          <Button type="default" onClick={() => navigate(-1)}>
            取消
          </Button>
        </div>
      </Card>
    </div>
  );
}
