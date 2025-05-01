from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import event, Index, CheckConstraint, Enum
from sqlalchemy.orm import validates, declarative_mixin
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum as PyEnum

db = SQLAlchemy()

# --------------------------- MIXINS ---------------------------

class SerializableMixin:
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

@declarative_mixin
class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)

@declarative_mixin
class SoftDeleteMixin:
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    @classmethod
    def query(cls):
        return super().query.filter_by(is_deleted=False)

# --------------------------- ENUMS ---------------------------

class UserRole(PyEnum):
    USER = "user"
    TECHWRITER = "techwriter"
    ADMIN = "admin"

class ContentType(PyEnum):
    ARTICLE = "article"
    VIDEO = "video"
    PODCAST = "podcast"
    DOCUMENT = "document"

class ApprovalStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class LikeType(PyEnum):
    LIKE = "like"
    DISLIKE = "dislike"

# --------------------------- USER ---------------------------

class User(db.Model, SerializableMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = 'users'
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        CheckConstraint('length(username) >= 3', name='check_username_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    profile = db.relationship("Profile", back_populates="user", uselist=False,
                             cascade="all, delete-orphan")
    content_posts = db.relationship(
        "Content", 
        back_populates="author",
        foreign_keys="Content.author_id"
    )
    comments = db.relationship("Comment", back_populates="user")
    notifications = db.relationship("Notification", back_populates="user")
    category_subscriptions = db.relationship("Subscription", back_populates="user")
    wishlists = db.relationship("Wishlist", back_populates="user")
    shares = db.relationship("Share", back_populates="user")
    likes = db.relationship("Like", back_populates="user")
    flags = db.relationship("Flag", back_populates="flagged_by")
    approvals = db.relationship(
        "Content", 
        foreign_keys="Content.approved_by_id"
    )

    @validates("email")
    def validate_email(self, key, email):
        allowed_domains = [
            '@moringa.student.com',
            '@moringa.admin.com',
            '@moringa.techwriter.com'
        ]
        if not any(email.endswith(domain) for domain in allowed_domains):
            raise ValueError("Invalid email domain. Allowed domains: " + 
                             ", ".join(allowed_domains))
        return email

    @validates("username")
    def validate_username(self, key, username):
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return username

    @property
    def password(self):
        raise AttributeError('Password is not readable')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt', salt_length=16)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

# --------------------------- PROFILE ---------------------------

class Profile(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'profiles'
    __table_args__ = (
        CheckConstraint('length(bio) <= 500', name='check_bio_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))
    website = db.Column(db.String(255))

    user = db.relationship("User", back_populates="profile")

# --------------------------- CONTENT ---------------------------

class Content(db.Model, SerializableMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = 'content'
    __table_args__ = (
        Index('idx_content_author', 'author_id'),
        Index('idx_content_category', 'category_id'),
        CheckConstraint('length(title) >= 5', name='check_title_length'),
        CheckConstraint('length(body) >= 10', name='check_body_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.Enum(ContentType), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    approval_status = db.Column(db.Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    rejection_reason = db.Column(db.Text)
    view_count = db.Column(db.Integer, default=0)
    is_flagged = db.Column(db.Boolean, default=False)

    # Relationships
    author = db.relationship(
        "User", 
        back_populates="content_posts", 
        foreign_keys=[author_id]
    )
    approved_by = db.relationship(
        "User", 
        foreign_keys=[approved_by_id]
    )
    category = db.relationship("Category", back_populates="content")
    comments = db.relationship("Comment", back_populates="content")
    likes = db.relationship("Like", back_populates="content")
    shares = db.relationship("Share", back_populates="content")
    wishlists = db.relationship("Wishlist", back_populates="content")
    flags = db.relationship("Flag", back_populates="content")

    @validates("content_type")
    def validate_content_type(self, key, value):
        if not isinstance(value, ContentType):
            raise ValueError("Invalid content type")
        return value

# --------------------------- CATEGORY ---------------------------

class Category(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'categories'
    __table_args__ = (
        Index('idx_category_name', 'name'),
        CheckConstraint('length(name) >= 3', name='check_category_name_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_featured = db.Column(db.Boolean, default=False)

    content = db.relationship("Content", back_populates="category")
    subscriptions = db.relationship("Subscription", back_populates="category")

# --------------------------- SUBSCRIPTION ---------------------------

class Subscription(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'subscriptions'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category_id', name='uq_user_category'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    user = db.relationship("User", back_populates="category_subscriptions")
    category = db.relationship("Category", back_populates="subscriptions")

# --------------------------- WISHLIST ---------------------------

class Wishlist(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'wishlists'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'content_id', name='uq_user_content'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)

    user = db.relationship("User", back_populates="wishlists")
    content = db.relationship("Content", back_populates="wishlists")

# --------------------------- COMMENT ---------------------------

class Comment(db.Model, SerializableMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = 'comments'
    __table_args__ = (
        CheckConstraint('length(body) >= 2', name='check_comment_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    body = db.Column(db.Text, nullable=False)

    user = db.relationship("User", back_populates="comments")
    content = db.relationship("Content", back_populates="comments")
    replies = db.relationship("Comment", backref=db.backref('parent', remote_side=[id]))

# --------------------------- LIKE ---------------------------

class Like(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'likes'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'content_id', name='uq_user_like'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    like_type = db.Column(db.Enum(LikeType), nullable=False)

    user = db.relationship("User", back_populates="likes")
    content = db.relationship("Content", back_populates="likes")

    @validates("like_type")
    def validate_like_type(self, key, value):
        if not isinstance(value, LikeType):
            raise ValueError("Invalid like type")
        return value

# --------------------------- NOTIFICATION ---------------------------

class Notification(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'notifications'
    __table_args__ = (
        CheckConstraint('length(message) >= 5', name='check_notification_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), default='system')

    user = db.relationship("User", back_populates="notifications")

# --------------------------- SHARE ---------------------------

class Share(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'shares'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    shared_with = db.Column(db.String(255), nullable=False)
    share_method = db.Column(db.String(50))  # email, social media, etc.

    user = db.relationship("User", back_populates="shares")
    content = db.relationship("Content", back_populates="shares")

    @validates("shared_with")
    def validate_shared_with(self, key, value):
        if not value or '@' not in value:
            raise ValueError("Invalid email address for sharing")
        return value

# --------------------------- FLAG ---------------------------

class Flag(db.Model, SerializableMixin, TimestampMixin):
    __tablename__ = 'flags'

    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    flagged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='reported')  # reported, reviewed, resolved

    content = db.relationship("Content", back_populates="flags")
    flagged_by = db.relationship("User", back_populates="flags")

# --------------------------- EVENT LISTENERS ---------------------------

@event.listens_for(User, 'before_insert')
def assign_user_role(mapper, connection, target):
    if '@moringa.admin.com' in target.email:
        target.role = UserRole.ADMIN
    elif '@moringa.techwriter.com' in target.email:
        target.role = UserRole.TECHWRITER
    else:
        target.role = UserRole.USER

@event.listens_for(Content, 'before_update')
def update_approval_status(mapper, connection, target):
    if target.approval_status == ApprovalStatus.APPROVED and not target.approved_by_id:
        raise ValueError("Approved content must have an approver")