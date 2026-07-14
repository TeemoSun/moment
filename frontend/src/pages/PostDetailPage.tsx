import { useState, useEffect, useRef, type ChangeEvent } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Button, Card, Modal } from "animal-island-ui";
import type { PostOut } from "@/api/posts";
import { getPost } from "@/api/posts";
import type { CommentOut } from "@/api/comments";
import { createComment, deleteComment, likeComment, uploadCommentImage } from "@/api/comments";
import { useCommentsStore } from "@/stores/comments";
import { formatRelativeTime } from "@/utils/time";
import { ApiError } from "@/api/client";
import { notify } from "@/utils/notify";
import Lightbox, { type LightboxImage } from "@/components/Lightbox";

interface ReplyState {
  parent_comment_id: number;
  reply_to_user_id: number;
  reply_to_nickname: string;
}

export default function PostDetailPage() {
  const { postId } = useParams<{ postId: string }>();
  const navigate = useNavigate();
  const postIdNum = Number(postId);

  const [post, setPost] = useState<PostOut | null>(null);
  const [postLoading, setPostLoading] = useState(true);
  const [postError, setPostError] = useState("");

  const {
    items: comments,
    hasMore,
    loading: commentsLoading,
    loadingMore,
    error: commentsError,
    fetchComments,
    loadMore,
    addComment,
    removeComment,
    updateCommentLike,
    clear: clearComments,
  } = useCommentsStore();

  const [content, setContent] = useState("");
  const [replyState, setReplyState] = useState<ReplyState | null>(null);
  const [commentImage, setCommentImage] = useState<{
    file: File;
    previewUrl: string;
    mediaId: number | null;
    uploading: boolean;
  } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [deleteTarget, setDeleteTarget] = useState<CommentOut | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [lightbox, setLightbox] = useState<{ images: LightboxImage[]; index: number } | null>(null);

  useEffect(() => {
    if (!postIdNum || isNaN(postIdNum)) return;
    setPostLoading(true);
    setPostError("");
    getPost(postIdNum)
      .then(setPost)
      .catch((err) => {
        setPostError(err instanceof ApiError ? err.message : "加载动态失败");
      })
      .finally(() => setPostLoading(false));
  }, [postIdNum]);

  useEffect(() => {
    if (!postIdNum || isNaN(postIdNum)) return;
    clearComments();
    fetchComments(postIdNum);
  }, [postIdNum, clearComments, fetchComments]);

  useEffect(() => {
    return () => {
      if (commentImage) URL.revokeObjectURL(commentImage.previewUrl);
    };
  }, [commentImage]);

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.type.startsWith("image/")) return;

    if (commentImage) URL.revokeObjectURL(commentImage.previewUrl);

    const previewUrl = URL.createObjectURL(file);
    setCommentImage({ file, previewUrl, mediaId: null, uploading: true });
    setSubmitError("");

    try {
      const res = await uploadCommentImage(file);
      setCommentImage((prev) =>
        prev ? { ...prev, mediaId: res.media_id, uploading: false } : null,
      );
    } catch {
      setCommentImage(null);
      URL.revokeObjectURL(previewUrl);
      setSubmitError("图片上传失败");
    }

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleRemoveImage = () => {
    if (commentImage) URL.revokeObjectURL(commentImage.previewUrl);
    setCommentImage(null);
  };

  const handleSubmitComment = async () => {
    if (!postIdNum || isNaN(postIdNum)) return;
    const trimmed = content.trim();
    if (!trimmed && !commentImage?.mediaId) {
      setSubmitError("请输入文字或添加图片");
      return;
    }
    if (commentImage?.uploading) {
      setSubmitError("请等待图片上传完成");
      return;
    }

    setSubmitting(true);
    setSubmitError("");
    try {
      const data = {
        content: trimmed || null,
        media_id: commentImage?.mediaId ?? null,
        parent_comment_id: replyState?.parent_comment_id ?? null,
        reply_to_user_id: replyState?.reply_to_user_id ?? null,
      };
      const comment = await createComment(postIdNum, data);
      addComment(comment);
      setContent("");
      setReplyState(null);
      handleRemoveImage();
      notify.success("评论已发送");
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "发送评论失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLikeComment = async (comment: CommentOut) => {
    const prevLiked = comment.liked_by_me;
    const prevCount = comment.like_count;
    updateCommentLike(comment.id, !prevLiked, prevLiked ? prevCount - 1 : prevCount + 1);
    try {
      const res = await likeComment(comment.id);
      updateCommentLike(comment.id, res.liked_by_me, res.like_count);
    } catch {
      updateCommentLike(comment.id, prevLiked, prevCount);
    }
  };

  const handleDeleteComment = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteComment(deleteTarget.id);
      removeComment(deleteTarget.id);
      setDeleteTarget(null);
      notify.success("已删除");
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "删除评论失败");
    } finally {
      setDeleting(false);
    }
  };

  const openPostLightbox = (clickedIndex: number) => {
    if (!post) return;
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

  const openCommentLightbox = (url: string) => {
    setLightbox({ images: [{ url, kind: "image" }], index: 0 });
  };

  if (postLoading) {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 16,
          }}
        >
          加载中...
        </div>
      </div>
    );
  }

  if (postError || !post) {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
        <div style={{ textAlign: "center", padding: 40 }}>
          <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12 }}>
            {postError || "动态不存在"}
          </div>
          <Button type="default" size="small" onClick={() => navigate(-1)}>
            返回
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "24px 16px" }}>
      <Button type="default" size="small" onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card style={{ marginBottom: 24 }}>
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
            }}
          >
            {post.content}
          </div>
        )}
        {post.media.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                post.media.length === 1
                  ? "minmax(0, 300px)"
                  : post.media.length <= 4
                    ? "repeat(2, 1fr)"
                    : "repeat(3, 1fr)",
              gap: 4,
              marginTop: 12,
            }}
          >
            {post.media.map((m, idx) => (
              <div
                key={m.id}
                style={{
                  aspectRatio: "1",
                  borderRadius: 12,
                  overflow: "hidden",
                  background: "#f0e8d8",
                  cursor: "pointer",
                }}
                onClick={() => openPostLightbox(idx)}
              >
                {m.thumb_url && (
                  <img
                    src={m.thumb_url}
                    alt=""
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      <div style={{ marginBottom: 16, color: "#794f27", fontWeight: 700, fontSize: 16 }}>
        评论 ({comments.length})
      </div>

      {commentsLoading && comments.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          加载评论中...
        </div>
      )}

      {commentsError && comments.length === 0 && (
        <div style={{ textAlign: "center", padding: 40 }}>
          <div style={{ color: "#e05a5a", fontWeight: 500, marginBottom: 12 }}>{commentsError}</div>
          <Button type="default" size="small" onClick={() => fetchComments(postIdNum)}>
            重试
          </Button>
        </div>
      )}

      {!commentsLoading && !commentsError && comments.length === 0 && (
        <div
          style={{
            textAlign: "center",
            padding: 40,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 15,
          }}
        >
          暂无评论，来抢沙发吧！
        </div>
      )}

      {comments.map((comment) => (
        <Card key={comment.id} style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", gap: 12 }}>
            <Link
              to={`/users/${comment.author.id}`}
              style={{ textDecoration: "none", flexShrink: 0 }}
            >
              <img
                src={comment.author.avatar_url}
                alt={comment.author.nickname}
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
                  to={`/users/${comment.author.id}`}
                  style={{
                    textDecoration: "none",
                    fontWeight: 600,
                    color: "#794f27",
                    fontSize: 14,
                  }}
                >
                  {comment.author.nickname}
                </Link>
                <span style={{ color: "#9f927d", fontSize: 12 }}>
                  {formatRelativeTime(comment.created_at)}
                </span>
              </div>
              {comment.reply_to && (
                <div style={{ color: "#9f927d", fontSize: 13, marginTop: 2 }}>
                  回复 @{comment.reply_to.nickname}
                </div>
              )}
              {comment.content && (
                <div
                  style={{
                    color: "#725d42",
                    fontSize: 14,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    marginTop: 6,
                  }}
                >
                  {comment.content}
                </div>
              )}
              {comment.image_thumb_url && (
                <div style={{ marginTop: 8 }}>
                  <img
                    src={comment.image_thumb_url}
                    alt=""
                    style={{
                      maxWidth: 200,
                      maxHeight: 200,
                      borderRadius: 12,
                      cursor: "pointer",
                      objectFit: "cover",
                    }}
                    onClick={() => {
                      const url = comment.image_large_url || comment.image_thumb_url;
                      if (url) openCommentLightbox(url);
                    }}
                  />
                </div>
              )}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  marginTop: 8,
                }}
              >
                <span
                  style={{
                    cursor: "pointer",
                    color: comment.liked_by_me ? "#e05a5a" : "#9f927d",
                    fontSize: 13,
                    fontWeight: 500,
                    userSelect: "none",
                  }}
                  onClick={() => handleLikeComment(comment)}
                >
                  {comment.liked_by_me ? "♥" : "♡"} {comment.like_count}
                </span>
                <span
                  style={{
                    cursor: "pointer",
                    color: "#9f927d",
                    fontSize: 13,
                    fontWeight: 500,
                    userSelect: "none",
                  }}
                  onClick={() =>
                    setReplyState({
                      parent_comment_id: comment.id,
                      reply_to_user_id: comment.author.id,
                      reply_to_nickname: comment.author.nickname,
                    })
                  }
                >
                  回复
                </span>
                {comment.can_delete && (
                  <span
                    style={{
                      cursor: "pointer",
                      color: "#e05a5a",
                      fontSize: 13,
                      fontWeight: 500,
                      userSelect: "none",
                    }}
                    onClick={() => setDeleteTarget(comment)}
                  >
                    删除
                  </span>
                )}
              </div>
            </div>
          </div>
        </Card>
      ))}

      {hasMore && (
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <Button
            type="default"
            size="small"
            onClick={() => loadMore(postIdNum)}
            loading={loadingMore}
          >
            加载更多
          </Button>
        </div>
      )}

      {loadingMore && (
        <div
          style={{
            textAlign: "center",
            padding: 16,
            color: "#9f927d",
            fontWeight: 500,
            fontSize: 14,
          }}
        >
          加载中...
        </div>
      )}

      <Card style={{ marginTop: 24 }}>
        {replyState && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 8,
              color: "#794f27",
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <span>回复 @{replyState.reply_to_nickname}</span>
            <span
              style={{ cursor: "pointer", color: "#9f927d", fontSize: 12 }}
              onClick={() => setReplyState(null)}
            >
              取消
            </span>
          </div>
        )}
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="写下你的评论..."
          maxLength={2000}
          style={{
            width: "100%",
            minHeight: 80,
            padding: "12px 16px",
            background: "rgb(247, 243, 223)",
            border: "2.5px solid #c4b89e",
            borderRadius: 18,
            color: "#725d42",
            fontWeight: 500,
            fontSize: 14,
            lineHeight: 1.6,
            resize: "vertical",
            outline: "none",
            fontFamily: "Nunito, 'Noto Sans SC', sans-serif",
            boxSizing: "border-box",
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "#ffcc00";
            e.target.style.boxShadow = "0 3px 0 0 #e0b800, 0 0 0 3px rgba(255, 204, 0, 0.15)";
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
            fontSize: 12,
            fontWeight: 500,
            marginTop: 4,
          }}
        >
          {content.length} / 2000
        </div>

        <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 12 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />
          <Button
            type="dashed"
            size="small"
            onClick={() => fileInputRef.current?.click()}
            disabled={!!commentImage || submitting}
          >
            添加图片
          </Button>
          {commentImage && (
            <div style={{ position: "relative", display: "inline-block" }}>
              <img
                src={commentImage.previewUrl}
                alt=""
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: 8,
                  objectFit: "cover",
                }}
              />
              {commentImage.uploading && (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background: "rgba(0,0,0,0.3)",
                    borderRadius: 8,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                >
                  上传中
                </div>
              )}
              <button
                type="button"
                onClick={handleRemoveImage}
                style={{
                  position: "absolute",
                  top: -6,
                  right: -6,
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  background: "rgba(0,0,0,0.5)",
                  color: "#fff",
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  lineHeight: 1,
                  padding: 0,
                }}
              >
                ×
              </button>
            </div>
          )}
        </div>

        {submitError && (
          <div style={{ marginTop: 8, color: "#e05a5a", fontWeight: 500, fontSize: 13 }}>
            {submitError}
          </div>
        )}

        <div style={{ marginTop: 12 }}>
          <Button
            type="primary"
            size="small"
            onClick={handleSubmitComment}
            loading={submitting}
            disabled={commentImage?.uploading}
          >
            发送
          </Button>
        </div>
      </Card>

      <Modal
        open={!!deleteTarget}
        title="确认删除"
        onClose={() => {
          setDeleteTarget(null);
          setDeleteError("");
        }}
        onOk={handleDeleteComment}
        typewriter={false}
      >
        <p style={{ margin: 0 }}>确定要删除这条评论吗？此操作不可撤销。</p>
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
    </div>
  );
}
