from dotenv import load_dotenv
from flask import jsonify

load_dotenv()

import os
import sqlite3
from io import BytesIO
from PIL import Image, ImageOps
from flask import Flask, request, redirect, render_template, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "static/uploads")
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_CONTENT_LENGTH", 40 * 1024 * 1024)
)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# 用户模型
class User(UserMixin):
    def __init__(self, id_, username, password_hash):
        self.id = id_
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        if not user:
            return None
        return User(user[0], user[1], user[2])


# 在用户未登录时访问受保护页面，显示自定义提示
@login_manager.unauthorized_handler
def unauthorized_callback():
    flash("请输入用户名和密码。")
    return redirect(url_for("login", next=request.endpoint))


# 加载用户
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# 初始化数据库
def init_db():
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar_path TEXT
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS moments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            image_path TEXT,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            category INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """
    )
    # 检查是否已存在 category 字段，如果不存在则添加
    c.execute("PRAGMA table_info(moments)")
    columns = [col[1] for col in c.fetchall()]
    if "category" not in columns:
        c.execute("ALTER TABLE moments ADD COLUMN category INTEGER DEFAULT 1")

    # 创建图片表，用于存储多张图片
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS moment_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moment_id INTEGER,
            image_path TEXT,
            original_path TEXT,
            upload_order INTEGER DEFAULT 0,
            FOREIGN KEY(moment_id) REFERENCES moments(id) ON DELETE CASCADE
        )
    """
    )

    # ... (comments 表的创建保持不变)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moment_id INTEGER,
            user_id INTEGER,
            comment_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            parent_comment_id INTEGER DEFAULT NULL,  -- 新增字段
            FOREIGN KEY(moment_id) REFERENCES moments(id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(parent_comment_id) REFERENCES comments(id)
        )
    """
    )
    c.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not c.fetchone():
        admin_password_hash = generate_password_hash("admin")
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", admin_password_hash),
        )
    conn.commit()
    conn.close()


# 注册功能
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("用户名和密码不能为空")
            return redirect(url_for("register"))
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            flash("用户名已存在")
            conn.close()
            return redirect(url_for("register"))
        password_hash = generate_password_hash(password)
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        conn.close()
        flash("注册成功，请登录")
        return redirect(url_for("login"))
    return render_template("register.html")


# 登录功能
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            user_obj = User(user[0], username, user[1])
            login_user(user_obj)
            flash("登录成功")
            return redirect(url_for("index"))
        else:
            flash("用户名或密码错误")
            return redirect(url_for("login"))
    return render_template("login.html")


# 登出功能
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已登出")
    return redirect(url_for("login"))


# 首页，显示说说和评论
@app.route("/", methods=["GET"])
@login_required
def index():
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()

    # 获取所有说说
    category_id = request.args.get("category_id", type=int, default=0)

    # 根据 category_id 构建 SQL 查询条件
    sql_condition = "WHERE moments.category = ?" if category_id > 0 else ""
    sql_query = f"""
        SELECT moments.id, moments.text, moments.image_path, datetime(moments.timestamp, "+8 hours"), users.username, users.avatar_path
        FROM moments 
        JOIN users ON moments.user_id = users.id
        {sql_condition}
        ORDER BY moments.timestamp DESC
    """

    if category_id > 0:
        c.execute(sql_query, (category_id,))
    else:
        c.execute(sql_query)

    moments_data = c.fetchall()
    moments = []

    for moment in moments_data:
        moment_id, text, image_path, timestamp, username, avatar_path = moment

        # 查询该说说下的所有图片
        c.execute(
            """
            SELECT image_path, original_path
            FROM moment_images 
            WHERE moment_id = ? 
            ORDER BY upload_order ASC
        """,
            (moment_id,),
        )
        images_data = c.fetchall()

        # 查询该说说下的所有评论
        c.execute(
            """
            SELECT comments.id, comments.comment_text, datetime(comments.timestamp, "+8 hours"), 
                   users.username, users.avatar_path, comments.parent_comment_id
            FROM comments 
            JOIN users ON comments.user_id = users.id 
            WHERE comments.moment_id = ? 
            ORDER BY comments.timestamp ASC
        """,
            (moment_id,),
        )
        comments_data = c.fetchall()

        # 构建评论树
        comments_map = {}
        top_level_comments = []

        # 第一遍：创建所有评论对象
        for comment in comments_data:
            (
                comment_id,
                comment_text,
                comment_timestamp,
                comment_username,
                comment_avatar_path,
                parent_id,
            ) = comment
            comment_obj = {
                "id": comment_id,
                "text": comment_text,
                "timestamp": comment_timestamp,
                "username": comment_username,
                "avatar_path": comment_avatar_path,
                "children": [],  # 用于存储子评论
            }
            comments_map[comment_id] = comment_obj

            # 如果父ID为空，添加到顶级评论列表
            if parent_id is None:
                top_level_comments.append(comment_obj)

        # 第二遍：构建层级关系
        for comment in comments_data:
            comment_id, _, _, _, _, parent_id = comment
            if parent_id is not None and parent_id in comments_map:
                # 将当前评论添加到父评论的children中
                parent_comment = comments_map[parent_id]
                current_comment = comments_map[comment_id]
                parent_comment["children"].append(current_comment)

        # 将评论树添加到说说
        moments.append(
            {
                "id": moment_id,
                "text": text,
                "image_path": image_path,  # 保留原有字段以兼容
                "images": images_data,     # 新增多图片字段
                "timestamp": timestamp,
                "username": username,
                "comments": top_level_comments,  # 只包含顶级评论
                "avatar_path": avatar_path,
            }
        )

    conn.close()
    return render_template(
        "index.html",
        moments=moments,
        current_user=current_user,
        current_category=category_id,
    )


@app.route("/publish_moment", methods=["POST"])
@login_required
def publish_moment():
    text = request.form.get("text")
    images = request.files.getlist("images")  # 改为 getlist 支持多张图片
    category = request.form.get("category", 1)

    if not text and not images:
        return jsonify({"success": False, "message": "内容或图片不能为空"}), 400

    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    
    # 先插入说说记录
    c.execute(
        "INSERT INTO moments (text, user_id, category) VALUES (?, ?, ?)",
        (text, current_user.id, category),
    )
    moment_id = c.lastrowid

    # 处理多张图片
    if images and len(images) > 0:
        for idx, image in enumerate(images):
            if image and image.filename != "":
                filename = secure_filename(image.filename)
                compressed_image = compress_image(image, moment_id=moment_id, idx=idx)
                filename = f"{moment_id}_{idx}_{os.path.splitext(filename)[0]}.jpg"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                
                with open(save_path, "wb") as f:
                    f.write(compressed_image.getvalue())
                
                # 获取原图路径（在compress_image函数中已经保存）
                original_filename = secure_filename(image.filename)
                original_name, ext = os.path.splitext(original_filename)
                if image.filename.endswith(".jpg"):
                    original_path = f"uploads/{moment_id}_{idx}_{original_name}_original{ext}"
                else:
                    original_path = f"uploads/{moment_id}_{idx}_{original_name}_original.jpg"
                
                # 将图片信息保存到图片表
                c.execute(
                    "INSERT INTO moment_images (moment_id, image_path, original_path, upload_order) VALUES (?, ?, ?, ?)",
                    (moment_id, f"uploads/{filename}", original_path, idx),
                )

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "说说发布成功"})


@app.route("/post_comment", methods=["POST"])
@login_required
def post_comment():
    comment_text = request.form.get("comment_text")
    moment_id = request.form.get("moment_id")
    parent_comment_id = request.form.get("parent_comment_id")

    if not comment_text:
        return jsonify({"success": False, "message": "评论内容不能为空"}), 400

    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO comments (moment_id, comment_text, user_id, parent_comment_id) VALUES (?, ?, ?, ?)",
        (
            moment_id,
            comment_text,
            current_user.id,
            parent_comment_id if parent_comment_id else None,
        ),
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "评论提交成功"})


# 用户删除自己的说说
@app.route("/delete_moment/<int:moment_id>", methods=["POST"])
@login_required
def delete_moment(moment_id):
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()

    # 验证用户是否拥有该说说
    c.execute("SELECT user_id FROM moments WHERE id = ?", (moment_id,))
    moment = c.fetchone()
    if not moment:
        conn.close()
        return jsonify({"success": False, "message": "说说不存在"}), 404
    if moment[0] != current_user.id:
        conn.close()
        return jsonify({"success": False, "message": "没有权限删除"}), 403

    # 删除说说及其所有评论和图片
    c.execute("DELETE FROM moment_images WHERE moment_id = ?", (moment_id,))
    c.execute("DELETE FROM comments WHERE moment_id = ?", (moment_id,))
    c.execute("DELETE FROM moments WHERE id = ?", (moment_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "说说已删除"})


# 用户删除自己的评论
@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
@login_required
def delete_comment(comment_id):
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()

    # 验证用户是否拥有该评论
    c.execute("SELECT user_id FROM comments WHERE id = ?", (comment_id,))
    comment = c.fetchone()
    if not comment:
        conn.close()
        return jsonify({"success": False, "message": "评论不存在"}), 404
    if comment[0] != current_user.id:
        conn.close()
        return jsonify({"success": False, "message": "没有权限删除"}), 403

    # 递归删除评论及其所有子评论
    def delete_comment_and_children(comment_id_to_delete):
        # 获取所有子评论
        c.execute(
            "SELECT id FROM comments WHERE parent_comment_id = ?",
            (comment_id_to_delete,),
        )
        children = c.fetchall()
        for child in children:
            delete_comment_and_children(child[0])
        # 删除当前评论
        c.execute("DELETE FROM comments WHERE id = ?", (comment_id_to_delete,))

    delete_comment_and_children(comment_id)
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "评论已删除"})


# 修改密码
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not old_password or not new_password or not confirm_password:
            flash("所有字段均为必填")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("两次新密码不一致")
            return redirect(url_for("change_password"))

        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE id = ?", (current_user.id,))
        user = c.fetchone()
        conn.close()

        if not user or not check_password_hash(user[0], old_password):
            flash("旧密码错误")
            return redirect(url_for("change_password"))

        new_hash = generate_password_hash(new_password)
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute(
            "UPDATE users SET password = ? WHERE id = ?", (new_hash, current_user.id)
        )
        conn.commit()
        conn.close()

        flash("密码修改成功")
        return redirect(url_for("index"))

    return render_template("change_password.html")


# 设置头像
@app.route("/set_avatar", methods=["GET", "POST"])
@login_required
def set_avatar():
    if request.method == "POST":
        avatar = request.files.get("avatar")
        if not avatar or avatar.filename == "":
            flash("请选择一张图片")
            return redirect(url_for("set_avatar"))

        filename = secure_filename(avatar.filename)
        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in {"png", "jpg", "jpeg", "gif"}:
            flash("仅支持 png/jpg/jpeg/gif 格式")
            return redirect(url_for("set_avatar"))

        # 压缩图片
        compressed_image = compress_image(avatar)

        # 用用户 id 做文件名，避免冲突
        filename = f"{current_user.id}.{ext}"
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # 保存压缩后的图片
        with open(save_path, "wb") as f:
            f.write(compressed_image.getvalue())

        # 写入数据库
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute(
            "UPDATE users SET avatar_path = ? WHERE id = ?",
            (f"uploads/{filename}", current_user.id),
        )
        conn.commit()
        conn.close()
        flash("头像更新成功")
        return redirect(url_for("index"))
    return render_template("set_avatar.html")


# 后台管理
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username != "admin":
            flash("仅允许管理员登录")
            return redirect(url_for("admin_login"))
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", ("admin",))
        admin_user = c.fetchone()
        conn.close()
        if admin_user and check_password_hash(admin_user[0], password):
            session["admin_logged_in"] = True
            flash("管理员登录成功")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("用户名或密码错误")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")


# 管理员登出
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("已退出管理员登录")
    return redirect(url_for("admin_login"))


def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("请先登录管理员账号")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated_function


# 管理员后台首页
@app.route("/admin")
@admin_login_required
def admin_dashboard():
    return render_template("admin_dashboard.html")


# 管理员用户管理
@app.route("/admin/users")
@admin_login_required
def admin_users():
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute("SELECT id, username FROM users")
    users = c.fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


# 管理员添加用户
@app.route("/admin/users/add", methods=["GET", "POST"])
@admin_login_required
def admin_add_user():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("用户名和密码不能为空")
            return redirect(url_for("admin_add_user"))
        conn = sqlite3.connect("moments.db")
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ?", (username,))
        if c.fetchone():
            flash("用户名已存在")
            conn.close()
            return redirect(url_for("admin_add_user"))
        password_hash = generate_password_hash(password)
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()
        conn.close()
        flash("用户添加成功")
        return redirect(url_for("admin_users"))
    return render_template("admin_add_user.html")


# 管理员删除用户
@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_login_required
def admin_delete_user(user_id):
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    if user and user[0] == "admin":
        flash("不能删除管理员账号")
        conn.close()
        return redirect(url_for("admin_users"))
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("用户删除成功")
    return redirect(url_for("admin_users"))


# 管理员说说管理
@app.route("/admin/moments")
@admin_login_required
def admin_moments():
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT moments.id, moments.text, moments.image_path, datetime(moments.timestamp, "+8 hours"), users.username, moments.category
        FROM moments 
        JOIN users ON moments.user_id = users.id
        ORDER BY moments.timestamp DESC
    """
    )
    moments = c.fetchall()
    conn.close()
    return render_template("admin_moments.html", moments=moments)


# 管理员删除说说
@app.route("/admin/moments/delete/<int:moment_id>", methods=["POST"])
@admin_login_required
def admin_delete_moment(moment_id):
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute("DELETE FROM moment_images WHERE moment_id = ?", (moment_id,))
    c.execute("DELETE FROM moments WHERE id = ?", (moment_id,))
    c.execute("DELETE FROM comments WHERE moment_id = ?", (moment_id,))
    conn.commit()
    conn.close()
    flash("说说删除成功")
    return redirect(url_for("admin_moments"))


# 管理员评论管理
@app.route("/admin/comments")
@admin_login_required
def admin_comments():
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute(
        """
        SELECT comments.id, comments.comment_text, datetime(comments.timestamp, "+8 hours"), users.username, moments.id, comments.parent_comment_id
        FROM comments
        JOIN users ON comments.user_id = users.id
        JOIN moments ON comments.moment_id = moments.id
        ORDER BY comments.timestamp DESC
    """
    )
    comments = c.fetchall()
    conn.close()
    return render_template("admin_comments.html", comments=comments)


# 管理员删除评论
@app.route("/admin/comments/delete/<int:comment_id>", methods=["POST"])
@admin_login_required
def admin_delete_comment(comment_id):
    conn = sqlite3.connect("moments.db")
    c = conn.cursor()
    c.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
    flash("评论删除成功")
    return redirect(url_for("admin_comments"))


# 图片压缩函数
def compress_image(image, max_size_kb=200, moment_id=None, idx=None):
    """压缩图片到指定大小以下，返回压缩后的字节数据"""

    # 如果原始图片的后缀为jpg，保存原始图片（不做任何修改，直接写入）
    if image.filename.endswith(".jpg"):
        original_filename = secure_filename(image.filename)
        original_name, ext = os.path.splitext(original_filename)
        if moment_id is not None and idx is not None:
            original_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{moment_id}_{idx}_{original_name}_original{ext}"
            )
        else:
            original_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{original_name}_original{ext}"
            )

    # 否则，保存为jpg后缀
    else:
        original_filename = secure_filename(image.filename)
        original_name, ext = os.path.splitext(original_filename)
        if moment_id is not None and idx is not None:
            original_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{moment_id}_{idx}_{original_name}_original.jpg"
            )
        else:
            original_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{original_name}_original.jpg"
            )

    image.stream.seek(0)
    with open(original_path, "wb") as f:
        f.write(image.read())

    # 重新打开图片并处理 EXIF 旋转
    image.stream.seek(0)
    img = Image.open(image)
    img = ImageOps.exif_transpose(img)  # 按 EXIF 方向旋转

    # 转换为 RGB（防止透明背景问题）
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 设置初始质量
    quality = 95
    buffer = BytesIO()

    # 调整图片尺寸（如果宽度超过 1200px）
    if img.width > 1200:
        ratio = 1200 / img.width
        new_height = int(img.height * ratio)
        img = img.resize((1200, new_height), Image.LANCZOS)

    # 如果调整后已经小于目标大小，直接返回
    img.save(buffer, format="JPEG", quality=quality)
    if len(buffer.getvalue()) / 1024 <= max_size_kb:
        buffer.seek(0)
        return buffer

    # 压缩循环
    while True:
        buffer.seek(0)
        buffer.truncate()
        img.save(buffer, format="JPEG", quality=quality)
        size_kb = len(buffer.getvalue()) / 1024

        if size_kb <= max_size_kb or quality <= 50:
            break

        quality -= 10

    buffer.seek(0)
    return buffer


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db()
    app.run(debug=True, host="0.0.0.0", port=80)
