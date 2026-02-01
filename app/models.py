"""
Database models using Flask-SQLAlchemy.
Includes:
- User
- Tag
- Post
- Comment
- post_tags association table
"""
from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

# Association table for many-to-many relationship: Post <-> Tag
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

post_upvotes = db.Table(
    'post_upvotes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True)
)

bookmark = db.Table(
    'bookmark',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('post_id', db.Integer, db.ForeignKey('post.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class followers_assoc(db.Model):
    __tablename__ = 'followers_assoc'
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    """Simple user model (no authentication system built-in).
    For demo purposes, we'll create a default user if none exists.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(256), nullable=True)  # path to profile image

    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)
    followers = db.relationship(
        'User', secondary='followers_assoc',
        primaryjoin=(followers_assoc.followed_id == id),
        secondaryjoin=(followers_assoc.follower_id == id),
        backref=db.backref('following', lazy='dynamic'), lazy='dynamic')
    bookmarks = db.relationship('Post', secondary='bookmark', backref=db.backref('bookmarked_users', lazy='dynamic'))
    liked_posts = db.relationship('Post', secondary='post_upvotes', backref=db.backref('liked_by', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

    def followers_count(self):
        return followers_assoc.query.filter_by(followed_id=self.id).count()

    def following_count(self):
        return followers_assoc.query.filter_by(follower_id=self.id).count()

    def is_followed_by(self, user):
        if not user:
            return False
        return followers_assoc.query.filter_by(follower_id=user.id, followed_id=self.id).count() > 0

    def is_following(self, user):
        if not user:
            return False
        return followers_assoc.query.filter_by(follower_id=self.id, followed_id=user.id).count() > 0

    def has_bookmarked(self, post):
        if not post:
            return False
        return post in self.bookmarks

    def has_liked(self, post):
        if not post:
            return False
        return self.liked_posts.filter_by(id=post.id).count() > 0

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Recipient
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Actor
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False) # 'like', 'comment', 'follow'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    recipient = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    sender = db.relationship('User', foreign_keys=[sender_id])
    post = db.relationship('Post')

    @property
    def message(self):
        if self.action == 'like':
            return f"{self.sender.username} liked your post '{self.post.title}'"
        elif self.action == 'comment':
            return f"{self.sender.username} commented on your post '{self.post.title}'"
        elif self.action == 'follow':
            return f"{self.sender.username} started following you"
        return "New Notification"

    @property
    def link(self):
        if self.post_id:
            return f"/post/{self.post_id}"
        if self.action == 'follow':
            return f"/profile/{self.sender_id}"
        return "#"

class Tag(db.Model):
    """Tag or department/topic for filtering posts."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)

    posts = db.relationship('Post', secondary=post_tags, back_populates='tags')

    def __repr__(self):
        return f'<Tag {self.name}>'

class Post(db.Model):
    """Blog post model with optional thumbnail filename."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    thumbnail = db.Column(db.String(256), nullable=True)  # filename stored in static/images/
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    upvotes = db.Column(db.Integer, default=0)
    tags = db.relationship('Tag', secondary=post_tags, back_populates='posts')
    comments = db.relationship('Comment', backref='post', lazy=True)

    def __repr__(self):
        return f'<Post {self.title}>'

class Comment(db.Model):
    """Comment on a post."""
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    date_commented = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'
