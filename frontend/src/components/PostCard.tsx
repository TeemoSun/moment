import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, Tag, Modal, Button } from "animal-island-ui";
import type { PostOut } from "@/api/posts";
import { deletePost } from "@/api/posts";
import { likePost } from "@/api/comments";
import { formatRelativeTime } from "@/utils/time";
import { ApiError } from "@/api/client";

function getGridColumns(count: number): string {
  if (count === 1) return "minmax(0, 300px)";
  if (count <= 4) return "repeat(2, 1fr)";
  return "repeat(3, 1fr)";
}

export default function PostCard({
  post,
  onDelete,
}: {
  post: PostOut;
  onDelete?: (id: number) => void;
}) {
  const navigate = useNavigate();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [likeCount, setLikeCount] = useState(post.like_count);
  const [liked, setLiked] = useState(post.liked_by_me);
  const [likeLoading, setLikeLoading] = useState(false);

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
    } finally {
      setLikeLoading(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError("");
    try {
      await deletePost(post.id);
      setShowDeleteModal(false);
      onDelete?.(post.id);
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <Link to={`/users/${post.author.id}`} style={{ textDecoration: "none", flexShrink: 0 }}>
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
          }}
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
        >
          {post.media.map((media) => (
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
              onClick={() => {
                const url = media.original_url || media.large_url;
                if (url) window.open(url, "_blank");
              }}
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
          gap: 16,
          marginTop: 12,
          paddingTop: 12,
          borderTop: "1.5px solid #e8dcc8",
        }}
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
        {deleting && (
          <p style={{ color: "#9f927d", fontWeight: 600, marginTop: 8 }}>正在删除...</p>
        )}
      </Modal>
    </Card>
  );
}
