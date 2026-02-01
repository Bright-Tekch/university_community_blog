"""
Main application routes (one blueprint).
Provides:
- index (feed)
- create new post (GET / POST) with thumbnail upload
- post detail view (comments and display)
"""
import os
import uuid
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.models import User, Tag, Post, Comment, followers_assoc

# Rename blueprint to 'main' for consistency with __init__.py
main = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.context_processor
def inject_current_user():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    return {'current_user': user}

def get_default_user():
    """Simple helper: return the first user or create a default demo user."""
    user = User.query.first()
    if not user:
        user = User(username='faculty_admin', email='admin@example.edu')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    return user

@main.route('/')
@main.route('/home')
def index():
    """Render the main feed with posts and tags."""
    feed_type = request.args.get('feed', 'discover')
    search_query = request.args.get('q')
    tag_query = request.args.get('tag')
    topic_query = request.args.get('topic')

    if search_query:
        posts = Post.query.filter(
            (Post.title.ilike(f'%{search_query}%')) | 
            (Post.content.ilike(f'%{search_query}%'))
        ).order_by(Post.date_posted.desc()).all()
    elif tag_query:
        posts = Post.query.join(Post.tags).filter(Tag.name == tag_query).order_by(Post.date_posted.desc()).all()
        flash(f'Showing posts tagged with "{tag_query}"', 'info')
    elif topic_query:
         posts = Post.query.join(Post.tags).filter(Tag.name == topic_query).order_by(Post.date_posted.desc()).all()
         flash(f'Showing posts for topic "{topic_query}"', 'info')
    elif feed_type == 'following':
        if 'user_id' not in session:
            flash('Please log in to view your following feed.', 'info')
            return redirect(url_for('main.login'))
        
        current_user = User.query.get(session['user_id'])
        posts = Post.query.join(followers_assoc, (followers_assoc.followed_id == Post.author_id))\
            .filter(followers_assoc.follower_id == current_user.id)\
            .order_by(Post.date_posted.desc()).all()
    else:
        # Default 'discover' feed
        posts = Post.query.order_by(Post.date_posted.desc()).all()
    tags = Tag.query.order_by(Tag.name).all()

    # simple trending calculation (tags with most posts)
    tag_counts = [(t, len(t.posts)) for t in tags]
    tag_counts.sort(key=lambda x: x[1], reverse=True)
    trending = [t.name for t,c in tag_counts[:6]]

    # Discuss sidebar data
    discussSidebar = {
        'trending': trending,
        'tags': [t.name for t in tags],
        'related': posts[:5]  # or any logic for related posts
    }

    # Get current user from session
    current_user = User.query.get(session.get('user_id')) if session.get('user_id') else None
    bookmarked_post_ids = {post.id for post in current_user.bookmarks} if current_user else set()
    liked_post_ids = {post.id for post in current_user.liked_posts} if current_user else set()

    return render_template('index.html', posts=posts, discussSidebar=discussSidebar, current_user=current_user, bookmarked_post_ids=bookmarked_post_ids, liked_post_ids=liked_post_ids, feed_type=feed_type, search_query=search_query)

@main.route('/post/new', methods=['GET', 'POST'])
def new_post():
    """Display form and handle post creation including image upload."""
    current_user = User.query.get(session.get('user_id')) if session.get('user_id') else None
    if not current_user:
        flash('Please log in to create a post.', 'danger')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags_raw = request.form.get('tags', '')
        file = request.files.get('thumbnail')

        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('main.new_post'))

        thumbnail_filename = None
        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash('Invalid image type. Allowed: png, jpg, jpeg, gif', 'danger')
                return redirect(url_for('main.new_post'))
            filename = secure_filename(file.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
            file.save(save_path)
            thumbnail_filename = unique

        post = Post(title=title, content=content, author=current_user, thumbnail=thumbnail_filename)
        db.session.add(post)
        db.session.commit()

        # Handle tags (comma-separated)
        tag_names = [t.strip() for t in tags_raw.split(',') if t.strip()]
        for tn in tag_names:
            tag = Tag.query.filter_by(name=tn).first()
            if not tag:
                tag = Tag(name=tn)
                db.session.add(tag)
            if tag not in post.tags:
                post.tags.append(tag)
        db.session.commit()

        flash('Post created successfully.', 'success')
        return redirect(url_for('main.post_detail', post_id=post.id))

    # GET - render the form
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('new_post.html', tags=tags)

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded thumbnails from the upload folder."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    """Show a single post and allow adding comments (simple)."""
    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        body = request.form.get('comment', '').strip()
        if body:
            user = get_default_user()
            comment = Comment(body=body, user=user, post=post)
            db.session.add(comment)
            db.session.commit()
            flash('Comment added.', 'success')
            return redirect(url_for('main.post_detail', post_id=post.id))
        else:
            flash('Comment cannot be empty.', 'danger')
            return redirect(url_for('main.post_detail', post_id=post.id))

    # Get current user from session
    current_user = User.query.get(session.get('user_id')) if session.get('user_id') else None

    # Fetch related posts (same tags or recent)
    related_posts = []
    if post.tags:
        tag_ids = [t.id for t in post.tags]
        related_posts = Post.query.join(Post.tags).filter(
            Tag.id.in_(tag_ids),
            Post.id != post.id
        ).distinct().order_by(Post.date_posted.desc()).limit(3).all()

    if len(related_posts) < 3:
        needed = 3 - len(related_posts)
        exclude_ids = [p.id for p in related_posts] + [post.id]
        more_posts = Post.query.filter(Post.id.notin_(exclude_ids)).order_by(Post.date_posted.desc()).limit(needed).all()
        related_posts.extend(more_posts)

    return render_template('post_detail.html', post=post, current_user=current_user, related_posts=related_posts)

@main.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('main.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('main.register'))
        user = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    """Log in an existing user."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Logged in successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('main.login'))
    return render_template('login.html')

@main.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    flash('Logged out.', 'success')
    return redirect(url_for('main.index'))

@main.route('/post/<int:post_id>/upvote', methods=['POST'])
def upvote_post(post_id):
    if 'user_id' not in session:
        return {'success': False, 'error': 'Authentication required'}, 401

    current_user = User.query.get(session['user_id'])
    post = Post.query.get_or_404(post_id)
    
    if current_user.has_liked(post):
        current_user.liked_posts.remove(post)
    else:
        current_user.liked_posts.append(post)
    
    db.session.commit()
    # Return actual count from relation
    count = post.liked_by.count()
    # Update the legacy upvotes column just in case some other code relies on it, 
    # though it's better to migrate away from it.
    post.upvotes = count 
    db.session.commit()

    return {'success': True, 'upvotes': count, 'liked': current_user.has_liked(post)}

@main.route('/post/<int:post_id>/bookmark', methods=['POST'])
def toggle_bookmark(post_id):
    if 'user_id' not in session:
        return {'success': False, 'error': 'Authentication required'}, 401
    user = User.query.get(session.get('user_id'))
    if not user:
        return {'success': False, 'error': 'Authentication required'}, 401

    post = Post.query.get_or_404(post_id)
    if user.has_bookmarked(post):
        user.bookmarks.remove(post)
        db.session.commit()
        return {'success': True, 'bookmarked': False}

    user.bookmarks.append(post)
    db.session.commit()
    return {'success': True, 'bookmarked': True}

@main.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    # You may want to get current_user from session or flask-login
    current_user = User.query.get(session.get('user_id')) if session.get('user_id') else None
    return render_template('profile.html', user=user, current_user=current_user)

@main.route('/follow/<int:user_id>', methods=['POST'])
def follow(user_id):
    if 'user_id' not in session:
        flash('Please log in to follow users.', 'warning')
        return redirect(url_for('main.login'))
    user = User.query.get_or_404(user_id)
    current_user = User.query.get(session['user_id'])
    if user != current_user and not current_user.is_following(user):
        assoc = followers_assoc(follower_id=current_user.id, followed_id=user.id)
        db.session.add(assoc)
        db.session.commit()
    return redirect(url_for('main.profile', user_id=user.id))

@main.route('/unfollow/<int:user_id>', methods=['POST'])
def unfollow(user_id):
    if 'user_id' not in session:
        flash('Please log in to unfollow users.', 'warning')
        return redirect(url_for('main.login'))
    user = User.query.get_or_404(user_id)
    current_user = User.query.get(session['user_id'])
    assoc = followers_assoc.query.filter_by(follower_id=current_user.id, followed_id=user.id).first()
    if assoc:
        db.session.delete(assoc)
        db.session.commit()
    return redirect(url_for('main.profile', user_id=user.id))

@main.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        flash('Please log in to edit posts.', 'warning')
        return redirect(url_for('main.login'))
    post = Post.query.get_or_404(post_id)
    current_user = User.query.get(session['user_id'])
    if post.author != current_user:
        flash('You do not have permission to edit this post.', 'danger')
        return redirect(url_for('main.profile', user_id=current_user.id))
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']

        file = request.files.get('thumbnail')
        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash('Invalid image type. Allowed: png, jpg, jpeg, gif', 'danger')
                return redirect(url_for('main.edit_post', post_id=post.id))
            filename = secure_filename(file.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
            file.save(save_path)
            # Optional: Delete old thumbnail if it exists to save space (not implemented here)
            post.thumbnail = unique

        db.session.commit()
        flash('Post updated.', 'success')
        return redirect(url_for('main.profile', user_id=current_user.id))
    return render_template('edit_post.html', post=post)

@main.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user = User.query.get(session.get('user_id'))
    if post.author != current_user:
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('main.profile', user_id=current_user.id))
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted.', 'success')
    return redirect(url_for('main.profile', user_id=current_user.id))

@main.route('/settings', methods=['GET', 'POST'])
def settings():
    current_user = User.query.get(session.get('user_id'))
    if request.method == 'POST':
        current_user.username = request.form['username']
        current_user.email = request.form['email']
        current_user.bio = request.form.get('bio', '')
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename:
            if allowed_file(avatar_file.filename):
                filename = secure_filename(avatar_file.filename)
                unique = f"{uuid.uuid4().hex}_{filename}"
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
                avatar_file.save(save_path)
                current_user.avatar = f"images/{unique}"
            else:
                flash('Invalid image type. Allowed: png, jpg, jpeg, gif', 'danger')
                return redirect(url_for('main.settings'))
        db.session.commit()
        # Reload user from DB to get updated avatar
        current_user = User.query.get(current_user.id)
        flash('Profile updated.', 'success')
        return redirect(url_for('main.settings'))
    return render_template('settings.html', user=current_user, current_user=current_user)

@main.route('/notifications')
def notifications():
    current_user = User.query.get(session.get('user_id'))
    # Example: Fetch notifications for the current user
    notifications = []  # Replace with actual query if notifications are stored
    return render_template('notifications.html', notifications=notifications, user=current_user, current_user=current_user)
