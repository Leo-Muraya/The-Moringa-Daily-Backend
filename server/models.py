from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from sqlalchemy import Index, CheckConstraint, Enum
from sqlalchemy.orm import validates, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum as PyEnum
from sqlalchemy.event import listens_for
import json
import re

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

# ========== ENUMS ==========
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
    FLAGGED = "flagged"

class NotificationType(PyEnum):
    NEW_CONTENT = "new_content"
    NEW_COMMENT = "new_comment"
    NEW_REPLY = "new_reply"
    CONTENT_APPROVED = "content_approved"
    CONTENT_DECLINED = "content_declined"
    CONTENT_FLAGGED = "content_flagged"
    NEW_MESSAGE = "new_message"
    SHARED_CONTENT = "shared_content"

# ========== MODELS ==========
class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        Index('idx_users_email', 'email'),
        CheckConstraint('length(username) >= 3', name='check_username_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    content_posts = relationship("Content", back_populates="author", foreign_keys="[Content.author_id]")
    comments = relationship("Comment", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    category_subscriptions = relationship("Subscription", back_populates="user")
    wishlists = relationship("Wishlist", back_populates="user")
    shares = relationship("Share", back_populates="user")
    likes = relationship("Like", back_populates="user")
    flags_created = relationship("Flag", back_populates="flagged_by", foreign_keys="[Flag.flagged_by_id]")
    approved_content = relationship("Content", back_populates="approved_by", foreign_keys="[Content.approved_by_id]")
    conversations = relationship("Conversation", secondary="conversation_participants", back_populates="participants")
    messages_sent = relationship("Message", back_populates="sender", foreign_keys="[Message.sender_id]")

    @validates('email')
    def validate_email(self, key, email):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email format")
        return email

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'is_active': self.is_active,
            'profile': self.profile.to_dict() if self.profile else None
        }

class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))
    website = db.Column(db.String(255))
    interests = db.Column(db.Text)  # JSON string of category interests
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="profile")

    def to_dict(self):
        return {
            'id': self.id,
            'bio': self.bio,
            'profile_picture': self.profile_picture,
            'website': self.website,
            'interests': json.loads(self.interests) if self.interests else []
        }

class Content(db.Model):
    __tablename__ = 'content'
    __table_args__ = (
        Index('idx_content_author', 'author_id'),
        Index('idx_content_category', 'category_id'),
        Index('idx_content_status', 'approval_status'),
        Index('idx_content_created', 'created_at'),
        CheckConstraint('length(title) >= 5', name='check_title_length'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.Enum(ContentType), nullable=False)
    media_url = db.Column(db.String(255))  # For video/audio files
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    approval_status = db.Column(db.Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    is_deleted = db.Column(db.Boolean, default=False)

    # Relationships
    author = relationship("User", back_populates="content_posts", foreign_keys=[author_id], lazy='joined')
    approved_by = relationship("User", back_populates="approved_content", foreign_keys=[approved_by_id])
    category = relationship("Category", back_populates="content")
    comments = relationship("Comment", back_populates="content", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="content", cascade="all, delete-orphan")
    shares = relationship("Share", back_populates="content", cascade="all, delete-orphan")
    wishlists = relationship("Wishlist", back_populates="content", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="content", cascade="all, delete-orphan")

    def delete(self):
        self.is_deleted = True

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'content_type': self.content_type.value,
            'media_url': self.media_url,
            'author': self.author.to_dict(),
            'category': self.category.to_dict(),
            'approval_status': self.approval_status.value,
            'view_count': self.view_count,
            'created_at': self.created_at.isoformat(),
            'comment_count': len(self.comments),
            'like_count': len(self.likes),
            'is_deleted': self.is_deleted
        }

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=utc_now)

    content = relationship("Content", back_populates="category")
    subscriptions = relationship("Subscription", back_populates="category")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'content_count': len(self.content)
        }

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'category_id', name='uq_user_category'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    user = relationship("User", back_populates="category_subscriptions")
    category = relationship("Category", back_populates="subscriptions")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category': self.category.to_dict(),
            'created_at': self.created_at.isoformat()
        }

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships - use lazy='joined' for immediate loading
    user = relationship("User", back_populates="comments", lazy='joined')
    content = relationship("Content", back_populates="comments", lazy='joined')
    replies = relationship("Comment", back_populates="parent", remote_side=[parent_comment_id])
    parent = relationship("Comment", back_populates="replies", remote_side=[id])

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict(),
            'content_id': self.content_id,
            'parent_comment_id': self.parent_comment_id,
            'body': self.body,
            'created_at': self.created_at.isoformat(),
            'replies': [reply.to_dict() for reply in self.replies]
        }

class Like(db.Model):
    __tablename__ = 'likes'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'content_id', name='uq_user_like'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    like_type = db.Column(db.String(10), nullable=False)  # like/dislike
    created_at = db.Column(db.DateTime, default=utc_now)

    user = relationship("User", back_populates="likes")
    content = relationship("Content", back_populates="likes")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content_id': self.content_id,
            'like_type': self.like_type,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    notification_type = db.Column(db.Enum(NotificationType), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    related_content_id = db.Column(db.Integer, db.ForeignKey('content.id'))
    created_at = db.Column(db.DateTime, default=utc_now)

    user = relationship("User", back_populates="notifications")
    related_content = relationship("Content")

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'notification_type': self.notification_type.value,
            'is_read': self.is_read,
            'related_content_id': self.related_content_id,
            'created_at': self.created_at.isoformat()
        }

class Share(db.Model):
    __tablename__ = 'shares'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    shared_with = db.Column(db.String(255), nullable=False)  # email or platform name
    share_method = db.Column(db.String(50))  # email, twitter, etc.
    created_at = db.Column(db.DateTime, default=utc_now)

    user = relationship("User", back_populates="shares")
    content = relationship("Content", back_populates="shares")

    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.to_dict(),
            'content': self.content.to_dict(),
            'shared_with': self.shared_with,
            'share_method': self.share_method,
            'created_at': self.created_at.isoformat()
        }

class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'content_id', name='uq_user_wishlist'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    user = relationship("User", back_populates="wishlists")
    content = relationship("Content", back_populates="wishlists")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content.to_dict(),
            'created_at': self.created_at.isoformat()
        }

class Flag(db.Model):
    __tablename__ = 'flags'
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    flagged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='reported')  # reported/reviewed/resolved
    created_at = db.Column(db.DateTime, default=utc_now)

    content = relationship("Content", back_populates="flags")
    flagged_by = relationship("User", back_populates="flags_created", foreign_keys=[flagged_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'flagged_by': self.flagged_by.to_dict(),
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

# ========== CHAT MODELS ==========
class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    participants = relationship("User", secondary="conversation_participants", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    shared_content = relationship("SharedContent", back_populates="conversation", cascade="all, delete-orphan")

    def to_dict(self):
        other_user = next(user for user in self.participants if user.id != getattr(self, 'current_user_id', None))
        last_message = self.messages[-1] if self.messages else None
        
        return {
            'id': self.id,
            'other_user': other_user.to_dict() if other_user else None,
            'last_message': last_message.content if last_message else None,
            'last_message_time': last_message.created_at if last_message else None,
            'unread_count': len([m for m in self.messages if not m.is_read and m.sender_id != getattr(self, 'current_user_id', None)])
        }

class ConversationParticipant(db.Model):
    __tablename__ = 'conversation_participants'
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender': self.sender.to_dict(),
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'is_read': self.is_read
        }

class SharedContent(db.Model):
    __tablename__ = 'shared_content'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    shared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    shared_at = db.Column(db.DateTime, default=utc_now)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="shared_content")
    content = relationship("Content")
    shared_by = relationship("User")

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'content': self.content.to_dict(),
            'shared_by': self.shared_by.to_dict(),
            'shared_at': self.shared_at.isoformat()
        }

# ========== EVENT LISTENERS ==========
@listens_for(Content, 'after_update')
def content_approval_listener(mapper, connection, target):
    try:
        if target.approval_status == ApprovalStatus.APPROVED:
            notification = Notification(
                user_id=target.author_id,
                message=f"Your content '{target.title}' has been approved!",
                notification_type=NotificationType.CONTENT_APPROVED,
                related_content_id=target.id
            )
            db.session.add(notification)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error in content approval notification: {str(e)}")

@listens_for(Comment, 'after_insert')
def comment_notification_listener(mapper, connection, target):
    try:
        # Ensure content and user are loaded
        if not target.content or not target.user:
            return
            
        if target.content.author_id != target.user_id:  # Don't notify for self-comments
            notification = Notification(
                user_id=target.content.author_id,
                message=f"New comment on your post: {target.body[:50]}...",
                notification_type=NotificationType.NEW_COMMENT,
                related_content_id=target.content_id
            )
            db.session.add(notification)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error in comment notification: {str(e)}")