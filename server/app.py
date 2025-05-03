from flask import Flask, jsonify, request, abort
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, 
    get_jwt_identity, create_refresh_token, get_jwt
)
from models import (
    db, User, Profile, Content, Category, Subscription, 
    Wishlist, Comment, Like, Notification, Share, Flag,
    Conversation, ConversationParticipant, Message, SharedContent,
    UserRole, ContentType, ApprovalStatus, NotificationType
)
from datetime import timedelta
import json
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moringa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key-here'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

db.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True, origins=["http://localhost:5173"])
jwt = JWTManager(app)

# ========== HELPER DECORATORS ==========
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or current_user.role != UserRole.ADMIN:
            abort(403, description="Admin access required")
        return fn(*args, **kwargs)
    return wrapper

def techwriter_or_admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or (current_user.role != UserRole.TECHWRITER and current_user.role != UserRole.ADMIN):
            abort(403, description="Tech Writer or Admin access required")
        return fn(*args, **kwargs)
    return wrapper

# ========== AUTH ROUTES ==========
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 400

    try:
        user = User(
            username=data['username'],
            email=data['email'],
            role=UserRole(data.get('role', 'user'))
        )
        user.password = data['password']
        db.session.add(user)
        db.session.commit()

        # Create default profile
        profile = Profile(
            user_id=user.id,
            bio="",
            profile_picture=f"https://ui-avatars.com/api/?name={user.username}",
            website="",
            interests=json.dumps([])
        )
        db.session.add(profile)
        db.session.commit()

        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.verify_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200

@app.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify(access_token=access_token), 200

@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    # In production, add token to blacklist
    return jsonify({"message": "Successfully logged out"}), 200

# ========== USER ROUTES ==========
@app.route('/api/user', methods=['GET'])
@jwt_required()
def get_current_user():
    user = User.query.get_or_404(get_jwt_identity())
    return jsonify(user.to_dict()), 200

@app.route('/api/users', methods=['GET'])
@admin_required
def get_all_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200

@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200

@app.route('/api/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return jsonify({"message": "User deactivated"}), 200

# ========== PROFILE ROUTES ==========
@app.route('/api/profile', methods=['GET', 'PUT'])
@jwt_required()
def profile_operations():
    user_id = get_jwt_identity()
    profile = Profile.query.filter_by(user_id=user_id).first_or_404()
    
    if request.method == 'GET':
        return jsonify(profile.to_dict()), 200
    
    elif request.method == 'PUT':
        data = request.get_json()
        profile.bio = data.get('bio', profile.bio)
        profile.profile_picture = data.get('profile_picture', profile.profile_picture)
        profile.website = data.get('website', profile.website)
        profile.interests = json.dumps(data.get('interests', []))
        
        db.session.commit()
        return jsonify(profile.to_dict()), 200

# ========== CONTENT ROUTES ==========
@app.route('/api/content', methods=['GET'])
def get_all_content():
    content_list = Content.query.filter_by(approval_status=ApprovalStatus.APPROVED).all()
    return jsonify([c.to_dict() for c in content_list]), 200

@app.route('/api/content/pending', methods=['GET'])
@techwriter_or_admin_required
def get_pending_content():
    content_list = Content.query.filter_by(approval_status=ApprovalStatus.PENDING).all()
    return jsonify([c.to_dict() for c in content_list]), 200

@app.route('/api/content/flagged', methods=['GET'])
@techwriter_or_admin_required
def get_flagged_content():
    content_list = Content.query.filter_by(approval_status=ApprovalStatus.FLAGGED).all()
    return jsonify([c.to_dict() for c in content_list]), 200

@app.route('/api/content', methods=['POST'])
@jwt_required()
def create_content():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Auto-approve for tech writers and admins
    approval_status = ApprovalStatus.APPROVED if user.role in [UserRole.TECHWRITER, UserRole.ADMIN] else ApprovalStatus.PENDING
    
    content = Content(
        title=data['title'],
        body=data['body'],
        content_type=ContentType(data['content_type']),
        author_id=user_id,
        category_id=data['category_id'],
        media_url=data.get('media_url'),
        approval_status=approval_status
    )
    
    db.session.add(content)
    db.session.commit()
    
    # Notify admins if pending approval
    if approval_status == ApprovalStatus.PENDING:
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                message=f"New content awaiting approval: {data['title']}",
                notification_type=NotificationType.NEW_CONTENT,
                related_content_id=content.id
            )
            db.session.add(notification)
        db.session.commit()
    
    return jsonify(content.to_dict()), 201

@app.route('/api/content/<int:content_id>', methods=['GET'])
def get_content(content_id):
    content = Content.query.get_or_404(content_id)
    content.view_count += 1
    db.session.commit()
    return jsonify(content.to_dict()), 200

@app.route('/api/content/<int:content_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def manage_content(content_id):
    content = Content.query.get_or_404(content_id)
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if request.method == 'PUT':
        if content.author_id != user_id and user.role not in [UserRole.ADMIN, UserRole.TECHWRITER]:
            abort(403, description="Not authorized to edit this content")
        
        data = request.get_json()
        content.title = data.get('title', content.title)
        content.body = data.get('body', content.body)
        content.category_id = data.get('category_id', content.category_id)
        content.media_url = data.get('media_url', content.media_url)
        
        db.session.commit()
        return jsonify(content.to_dict()), 200
    
    elif request.method == 'DELETE':
        if content.author_id != user_id and user.role != UserRole.ADMIN:
            abort(403, description="Not authorized to delete this content")
        
        db.session.delete(content)
        db.session.commit()
        return jsonify({"message": "Content deleted"}), 200

@app.route('/api/content/<int:content_id>/approve', methods=['POST'])
@techwriter_or_admin_required
def approve_content(content_id):
    content = Content.query.get_or_404(content_id)
    user_id = get_jwt_identity()
    
    content.approval_status = ApprovalStatus.APPROVED
    content.approved_by_id = user_id
    db.session.commit()
    
    # Notify author
    notification = Notification(
        user_id=content.author_id,
        message=f"Your content '{content.title}' has been approved!",
        notification_type=NotificationType.CONTENT_APPROVED,
        related_content_id=content_id
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify(content.to_dict()), 200

@app.route('/api/content/<int:content_id>/decline', methods=['POST'])
@techwriter_or_admin_required
def decline_content(content_id):
    content = Content.query.get_or_404(content_id)
    content.approval_status = ApprovalStatus.REJECTED
    db.session.commit()
    
    # Notify author
    notification = Notification(
        user_id=content.author_id,
        message=f"Your content '{content.title}' was declined",
        notification_type=NotificationType.CONTENT_DECLINED,
        related_content_id=content_id
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify(content.to_dict()), 200

@app.route('/api/content/<int:content_id>/flag', methods=['POST'])
@jwt_required()
def flag_content(content_id):
    data = request.get_json()
    user_id = get_jwt_identity()
    
    flag = Flag(
        content_id=content_id,
        flagged_by_id=user_id,
        reason=data.get('reason')
    )
    
    content = Content.query.get(content_id)
    content.approval_status = ApprovalStatus.FLAGGED
    
    db.session.add(flag)
    db.session.commit()
    
    # Notify admins
    admins = User.query.filter_by(role=UserRole.ADMIN).all()
    for admin in admins:
        notification = Notification(
            user_id=admin.id,
            message=f"Content flagged: {content.title}",
            notification_type=NotificationType.CONTENT_FLAGGED,
            related_content_id=content_id
        )
        db.session.add(notification)
    
    db.session.commit()
    return jsonify({"message": "Content flagged for review"}), 201

# ========== CATEGORY ROUTES ==========
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories]), 200

@app.route('/api/categories', methods=['POST'])
@techwriter_or_admin_required
def create_category():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({"error": "Category already exists"}), 400
        
    category = Category(
        name=data['name'],
        description=data.get('description'),
        created_by_id=user_id
    )
    
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201

# ========== SUBSCRIPTION ROUTES ==========
@app.route('/api/subscriptions', methods=['GET'])
@jwt_required()
def get_user_subscriptions():
    user_id = get_jwt_identity()
    subscriptions = Subscription.query.filter_by(user_id=user_id).all()
    return jsonify([s.to_dict() for s in subscriptions]), 200

@app.route('/api/subscriptions', methods=['POST'])
@jwt_required()
def create_subscription():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    if Subscription.query.filter_by(user_id=user_id, category_id=data['category_id']).first():
        return jsonify({"error": "Already subscribed to this category"}), 400
        
    subscription = Subscription(
        user_id=user_id,
        category_id=data['category_id']
    )
    
    db.session.add(subscription)
    db.session.commit()
    return jsonify(subscription.to_dict()), 201

@app.route('/api/subscriptions/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_subscription(category_id):
    user_id = get_jwt_identity()
    subscription = Subscription.query.filter_by(user_id=user_id, category_id=category_id).first_or_404()
    
    db.session.delete(subscription)
    db.session.commit()
    return jsonify({"message": "Subscription removed"}), 200

# ========== WISHLIST ROUTES ==========
@app.route('/api/wishlist', methods=['GET'])
@jwt_required()
def get_user_wishlist():
    user_id = get_jwt_identity()
    wishlist = Wishlist.query.filter_by(user_id=user_id).all()
    return jsonify([w.to_dict() for w in wishlist]), 200

@app.route('/api/wishlist/<int:content_id>', methods=['POST', 'DELETE'])
@jwt_required()
def manage_wishlist(content_id):
    user_id = get_jwt_identity()
    
    if request.method == 'POST':
        if Wishlist.query.filter_by(user_id=user_id, content_id=content_id).first():
            return jsonify({"error": "Content already in wishlist"}), 400
            
        wishlist = Wishlist(
            user_id=user_id,
            content_id=content_id
        )
        db.session.add(wishlist)
        db.session.commit()
        return jsonify(wishlist.to_dict()), 201
    
    elif request.method == 'DELETE':
        wishlist = Wishlist.query.filter_by(user_id=user_id, content_id=content_id).first_or_404()
        db.session.delete(wishlist)
        db.session.commit()
        return jsonify({"message": "Removed from wishlist"}), 200

# ========== COMMENT ROUTES ==========
@app.route('/api/comments', methods=['POST'])
@jwt_required()
def create_comment():
    data = request.get_json()
    user_id = get_jwt_identity()
    
    comment = Comment(
        user_id=user_id,
        content_id=data['content_id'],
        body=data['body'],
        parent_comment_id=data.get('parent_comment_id')
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Notify content author if not self-comment
    content = Content.query.get(data['content_id'])
    if content.author_id != user_id:
        notification = Notification(
            user_id=content.author_id,
            message=f"New comment on your post: {data['body'][:30]}...",
            notification_type=NotificationType.NEW_COMMENT,
            related_content_id=data['content_id']
        )
        db.session.add(notification)
    
    # Notify parent comment author if this is a reply
    if data.get('parent_comment_id'):
        parent = Comment.query.get(data['parent_comment_id'])
        if parent.user_id != user_id:
            notification = Notification(
                user_id=parent.user_id,
                message=f"New reply to your comment: {data['body'][:30]}...",
                notification_type=NotificationType.NEW_REPLY,
                related_content_id=data['content_id']
            )
            db.session.add(notification)
    
    db.session.commit()
    return jsonify(comment.to_dict()), 201

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    user_id = get_jwt_identity()
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != user_id:
        current_user = User.query.get(user_id)
        if current_user.role not in [UserRole.ADMIN, UserRole.TECHWRITER]:
            abort(403, description="Not authorized to delete this comment")
    
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"message": "Comment deleted"}), 200

# ========== LIKE ROUTES ==========
@app.route('/api/likes/<int:content_id>', methods=['GET'])
def get_likes(content_id):
    like_count = Like.query.filter_by(content_id=content_id).count()
    return jsonify({"count": like_count}), 200

@app.route('/api/likes/<int:content_id>', methods=['POST', 'DELETE'])
@jwt_required()
def manage_like(content_id):
    user_id = get_jwt_identity()
    
    if request.method == 'POST':
        if Like.query.filter_by(user_id=user_id, content_id=content_id).first():
            return jsonify({"error": "Already liked this content"}), 400
            
        like = Like(
            user_id=user_id,
            content_id=content_id,
            like_type="like"
        )
        db.session.add(like)
        db.session.commit()
        
        # Notify content author
        content = Content.query.get(content_id)
        if content.author_id != user_id:
            notification = Notification(
                user_id=content.author_id,
                message=f"Someone liked your content: {content.title[:30]}...",
                notification_type=NotificationType.NEW_CONTENT,
                related_content_id=content_id
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify(like.to_dict()), 201
    
    elif request.method == 'DELETE':
        like = Like.query.filter_by(user_id=user_id, content_id=content_id).first_or_404()
        db.session.delete(like)
        db.session.commit()
        return jsonify({"message": "Like removed"}), 200

# ========== NOTIFICATION ROUTES ==========
@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications]), 200

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=get_jwt_identity()
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    return jsonify(notification.to_dict()), 200

# ========== CHAT ROUTES ==========
@app.route('/api/chats', methods=['GET'])
@jwt_required()
def get_user_chats():
    user_id = get_jwt_identity()
    
    # Get all conversations where the user is a participant
    conversations = Conversation.query.join(
        ConversationParticipant,
        Conversation.id == ConversationParticipant.conversation_id
    ).filter(ConversationParticipant.user_id == user_id).all()
    
    results = []
    for conv in conversations:
        # Get the other participant (assuming 1:1 chats)
        other_user = next(
            user for user in conv.participants 
            if user.id != user_id
        )
        
        # Get last message
        last_message = Message.query.filter_by(
            conversation_id=conv.id
        ).order_by(Message.created_at.desc()).first()
        
        # Count unread messages
        unread_count = Message.query.filter_by(
            conversation_id=conv.id,
            is_read=False
        ).filter(Message.sender_id != user_id).count()
        
        results.append({
            "conversation_id": conv.id,
            "other_user": other_user.to_dict(),
            "last_message": last_message.content if last_message else None,
            "last_message_time": last_message.created_at.isoformat() if last_message else None,
            "unread_count": unread_count
        })
    
    return jsonify(results), 200

@app.route('/api/chats/<int:other_user_id>', methods=['GET', 'POST'])
@jwt_required()
def chat_with_user(other_user_id):
    user_id = get_jwt_identity()
    
    # Find or create conversation between these users
    conv = db.session.query(Conversation).join(
        ConversationParticipant,
        Conversation.id == ConversationParticipant.conversation_id
    ).filter(
        ConversationParticipant.user_id == user_id
    ).join(
        ConversationParticipant,
        Conversation.id == ConversationParticipant.conversation_id
    ).filter(
        ConversationParticipant.user_id == other_user_id
    ).first()
    
    if not conv:
        conv = Conversation()
        db.session.add(conv)
        db.session.flush()
        
        db.session.add_all([
            ConversationParticipant(conversation_id=conv.id, user_id=user_id),
            ConversationParticipant(conversation_id=conv.id, user_id=other_user_id)
        ])
        db.session.commit()
    
    if request.method == 'GET':
        # Get all messages in this conversation
        messages = Message.query.filter_by(
            conversation_id=conv.id
        ).order_by(Message.created_at.asc()).all()
        
        # Mark messages as read
        Message.query.filter_by(
            conversation_id=conv.id,
            is_read=False
        ).filter(Message.sender_id != user_id).update({"is_read": True})
        db.session.commit()
        
        # Get shared content in this conversation
        shared = SharedContent.query.filter_by(
            conversation_id=conv.id
        ).order_by(SharedContent.shared_at.desc()).all()
        
        return jsonify({
            "messages": [m.to_dict() for m in messages],
            "shared_content": [s.to_dict() for s in shared]
        }), 200
    
    elif request.method == 'POST':
        data = request.get_json()
        message = Message(
            conversation_id=conv.id,
            sender_id=user_id,
            content=data['content']
        )
        db.session.add(message)
        db.session.commit()
        
        # Create notification for the other user
        notification = Notification(
            user_id=other_user_id,
            message=f"New message from {User.query.get(user_id).username}",
            notification_type=NotificationType.NEW_MESSAGE,
            related_content_id=None
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify(message.to_dict()), 201

@app.route('/api/chats/<int:conversation_id>/share', methods=['POST'])
@jwt_required()
def share_content_in_chat(conversation_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Verify user is part of this conversation
    if not ConversationParticipant.query.filter_by(
        conversation_id=conversation_id,
        user_id=user_id
    ).first():
        abort(403, description="Not part of this conversation")
    
    shared = SharedContent(
        conversation_id=conversation_id,
        content_id=data['content_id'],
        shared_by_id=user_id
    )
    db.session.add(shared)
    db.session.commit()
    
    # Get other participants
    participants = ConversationParticipant.query.filter_by(
        conversation_id=conversation_id
    ).filter(ConversationParticipant.user_id != user_id).all()
    
    # Notify them
    for participant in participants:
        notification = Notification(
            user_id=participant.user_id,
            message=f"{User.query.get(user_id).username} shared content with you",
            notification_type=NotificationType.SHARED_CONTENT,
            related_content_id=data['content_id']
        )
        db.session.add(notification)
    
    db.session.commit()
    return jsonify(shared.to_dict()), 201

# ========== ERROR HANDLER ==========
@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(403)
def forbidden(e):
    return jsonify(error=str(e)), 403

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

if __name__ == '__main__':
    app.run(debug=True)