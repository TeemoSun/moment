import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, Tag, Modal, Button } from "animal-island-ui";
import type { PostOut } from "@/api/posts";
import { deletePost } from "@/api/posts";
import { likePost } from "@/api/comments";
import { formatRelativeTime } from "@/utils/time";
import { ApiError } from "@/api/client";
import { notify } from "@/utils/notify";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import Lightbox, { type LightboxImage } from "@/components/Lightbox";

export default function PostCard({
  post,
  onDelete,
}: {
  post: PostOut;
  onDelete?: (id: number) => void;
}) {
  const navigate = useNavigate();
  const isMobile = useMediaQuery("(max-width: 639px)");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [likeCount, setLikeCount] = useState(post.like_count);
  const [liked, setLiked] = useState(post.liked_by_me);
  const [likeLoading, setLikeLoading] = useState(false);
  const [lightbox, setLightbox] = useState<{ images: LightboxImage[]; index: number } | null>(null);

  const getGridColumns = (count: number): string => {
    if (count === 1) return "minmax(0, 300px)";
    return `repeat(${Math.min(count, 3)}, minmax(0, 300px))`;
  };

  const handleLike = async () => {
    if (likeLoading) return;
    const prevLiked = liked;
    const prevCount = likeCount;
    setLiked(!prevLiked);
    setLikeCount(prevLiked ? prevCount - 1 : prevCount + 1);
    setLikeLoading(true);
    try {
      const res = await likePost(post.id);
      setLiked(res.liked_by_me);
      setLikeCount(res.like_count);
    } catch {
      setLiked(prevLiked);
      setLikeCount(prevCount);
      notify.error("操作失败");
    } finally {
      setLikeLoading(false);
    }
  };

  const openLightbox = (clickedIndex: number) => {
    const images: LightboxImage[] = post.media
      .map((m) => {
        const url = m.original_url || m.large_url || m.thumb_url;
        if (!url) return null;
        return { url, kind: m.kind === "video" ? "video" : "image" };
      })
      .filter((v): v is LightboxImage => v !== null);
    if (images.length === 0) return;
    const idx = Math.min(clickedIndex, images.length - 1);
    setLightbox({ images, index: idx });
  };

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError("");
    try {
      await deletePost(post.id);
      setShowDeleteModal(false);
      notify.success("已删除");
      onDelete?.(post.id);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card
      style={{ marginBottom: 16, cursor: "pointer" }}
      onClick={() => navigate(`/posts/${post.id}`)}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 12,
        }}
      >
        <Link
          to={`/users/${post.author.id}`}
          style={{ textDecoration: "none", flexShrink: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          <img
            src={post.author.avatar_url}
            alt={post.author.nickname}
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              objectFit: "cover",
              border: "2px solid #c4b89e",
            }}
          />
        </Link>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Link
              to={`/users/${post.author.id}`}
              style={{
                textDecoration: "none",
                fontWeight: 600,
                color: "#794f27",
                fontSize: 15,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {post.author.nickname}
            </Link>
            <span style={{ color: "#9f927d", fontSize: 13 }}>
              {formatRelativeTime(post.created_at)}
            </span>
            {post.visibility === "friends" && (
              <Tag color="app-yellow" size="small" variant="solid">
                仅好友
              </Tag>
            )}
          </div>
        </div>
      </div>

      {post.content && (
        <div
          style={{
            color: "#725d42",
            fontSize: 15,
            lineHeight: 1.6,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            marginBottom: post.media.length > 0 ? 12 : 0,
            cursor: "pointer",
          }}
          onClick={() => navigate(`/posts/${post.id}`)}
        >
          {post.content}
        </div>
      )}

      {post.media.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: getGridColumns(post.media.length),
            gap: 4,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {post.media.map((media, idx) => (
            <div
              key={media.id}
              style={{
                aspectRatio: "1",
                borderRadius: 12,
                overflow: "hidden",
                cursor: "pointer",
                background: "#f0e8d8",
                position: "relative",
              }}
              onClick={() => openLightbox(idx)}
            >
              {media.thumb_url ? (
                <img
                  src={media.thumb_url}
                  alt=""
                  style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                />
              ) : (
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    background: "#e8dcc8",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#c4b89e",
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                >
                  处理中
                </div>
              )}
              {media.kind === "video" && (
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    background: "rgba(0,0,0,0.5)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    fontSize: 12,
                  }}
                >
                  ▶
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: isMobile ? 12 : 16,
          marginTop: 12,
          paddingTop: 12,
          borderTop: "1.5px solid #e8dcc8",
          flexWrap: "wrap",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <span
          style={{
            color: liked ? "#e05a5a" : "#9f927d",
            fontSize: 14,
            fontWeight: 500,
            cursor: "pointer",
            userSelect: "none",
          }}
          onClick={handleLike}
        >
          {liked ? "♥" : "♡"} {likeCount}
        </span>
        <span
          style={{
            color: "#9f927d",
            fontSize: 14,
            fontWeight: 500,
            cursor: "pointer",
            userSelect: "none",
          }}
          onClick={() => navigate(`/posts/${post.id}`)}
        >
          评论 {post.comment_count}
        </span>
        {post.is_owner && (
          <Button type="default" size="small" danger onClick={() => setShowDeleteModal(true)}>
            删除
          </Button>
        )}
      </div>

      {likeCount > 0 && post.like_authors.length > 0 && (
        <div
          style={{
            marginTop: 8,
            color: "#9f927d",
            fontSize: 13,
            fontWeight: 500,
            cursor: "pointer",
            userSelect: "none",
          }}
          onClick={() => navigate(`/posts/${post.id}`)}
        >
          {post.like_authors.length <= 3
            ? `${post.like_authors.map((a) => a.nickname).join("、")} 赞过`
            : `${post.like_authors
                .slice(0, 2)
                .map((a) => a.nickname)
                .join("、")} 等${likeCount}人赞过`}
        </div>
      )}

      {post.preview_comments.length > 0 && (
        <div
          style={{
            marginTop: 12,
            paddingTop: 12,
            borderTop: "1.5px solid #e8dcc8",
          }}
        >
          {post.preview_comments.map((comment) => (
            <div
              key={comment.id}
              style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}
            >
              <Link
                to={`/users/${comment.author.id}`}
                style={{ textDecoration: "none", flexShrink: 0 }}
              >
                <img
                  src={comment.author.avatar_url}
                  alt={comment.author.nickname}
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: "50%",
                    objectFit: "cover",
                    border: "1.5px solid #c4b89e",
                  }}
                />
              </Link>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap" }}>
                  <Link
                    to={`/users/${comment.author.id}`}
                    style={{
                      textDecoration: "none",
                      fontWeight: 600,
                      color: "#794f27",
                      fontSize: 13,
                    }}
                  >
                    {comment.author.nickname}
                  </Link>
                  {comment.reply_to && (
                    <span style={{ color: "#9f927d", fontSize: 12 }}>
                      回复 @{comment.reply_to.nickname}
                    </span>
                  )}
                </div>
                {comment.content && (
                  <div
                    style={{
                      color: "#725d42",
                      fontSize: 13,
                      lineHeight: 1.5,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      marginTop: 2,
                    }}
                  >
                    {comment.content}
                  </div>
                )}
                {comment.image_thumb_url && (
                  <div style={{ marginTop: 4 }}>
                    <img
                      src={comment.image_thumb_url}
                      alt=""
                      style={{ maxWidth: 120, maxHeight: 120, borderRadius: 8, objectFit: "cover" }}
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
          {post.comment_count > 3 && (
            <div
              style={{
                marginTop: 4,
                color: "#9f927d",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                userSelect: "none",
              }}
              onClick={() => navigate(`/posts/${post.id}`)}
            >
              查看全部 {post.comment_count} 条评论
            </div>
          )}
        </div>
      )}

      <Modal
        open={showDeleteModal}
        title="确认删除"
        onClose={() => setShowDeleteModal(false)}
        onOk={handleDelete}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要删除这条动态吗？此操作不可撤销。</p>
        {deleteError && (
          <p style={{ color: "#e05a5a", fontWeight: 500, marginTop: 8 }}>{deleteError}</p>
        )}
        {deleting && <p style={{ color: "#9f927d", fontWeight: 600, marginTop: 8 }}>正在删除...</p>}
      </Modal>
      {lightbox && (
        <Lightbox
          images={lightbox.images}
          index={lightbox.index}
          onClose={() => setLightbox(null)}
          onIndexChange={(i) => setLightbox((prev) => (prev ? { ...prev, index: i } : null))}
        />
      )}
    </Card>
  );
}
