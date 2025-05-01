from flask import Flask, jsonify, request, Blueprint
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restful import Api
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Profile, Content, Category, Subscription, Wishlist, Comment, Like, Notification, Share, Flag
from datetime import timedelta
from models import UserRole, ApprovalStatus, ContentType, LikeType

app = Flask(__name__)

# ========== CONFIGURATION ==========
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moringa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '4bfbece877bc4c6a9276b4f9f0203a45d722bbfd02728c7d823438120c8b5c91'
app.config['JWT_SECRET_KEY'] = 'd9cbf61a59b0c1e24e9fc62547c3d524c97a35d7e283c902835de5d61b126bde'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=10)

# ========== INITIALIZE EXTENSIONS ==========
db.init_app(app)
migrate = Migrate(app, db)
CORS(app, supports_credentials=True, origins=["http://localhost:5173"])
api = Api(app)
jwt = JWTManager(app)

# ========== BLUEPRINT ==========
resources_bp = Blueprint('resources', __name__)

# ========== ERROR HANDLING ==========
@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({"error": str(error)}), 500

# ========== USER ROUTES ==========
@resources_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_data():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user:
            return jsonify(user.to_dict()), 200
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@resources_bp.route('/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user = User.query.get(get_jwt_identity())
    if not current_user or current_user.role != UserRole.ADMIN:
        return jsonify({"error": "Unauthorized access"}), 403

    users = User.query.all()
    return jsonify([u.to_dict() for u in users]), 200

# ========== AUTH ROUTES ==========
@resources_bp.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    for field in ['username', 'email', 'password']:
        if not data.get(field):
            return jsonify({"error": f"{field.capitalize()} is required"}), 400

    try:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "Email already exists"}), 400
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"error": "Username already exists"}), 400

        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password']  # Password hashing happens in the model
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@resources_bp.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            "access_token": access_token,
            "user": user.to_dict()
        }), 200
    return jsonify({"error": "Invalid credentials"}), 401

# ========== PROFILE ROUTES ==========
@resources_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user = get_jwt_identity()
    profile = Profile.query.filter_by(user_id=current_user).first()
    return jsonify(profile.to_dict() if profile else {"message": "Profile not found"}), 200 if profile else 404

@resources_bp.route('/profile', methods=['POST'])
@jwt_required()
def create_profile():
    data = request.get_json()
    current_user = get_jwt_identity()
    
    if Profile.query.filter_by(user_id=current_user).first():
        return jsonify({"error": "Profile already exists"}), 400
        
    profile = Profile(
        user_id=current_user,
        bio=data.get('bio', ''),
        profile_picture=data.get('profile_picture', ''),
        website=data.get('website', '')
    )
    db.session.add(profile)
    db.session.commit()
    return jsonify(profile.to_dict()), 201

@resources_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    data = request.get_json()
    current_user = get_jwt_identity()
    profile = Profile.query.filter_by(user_id=current_user).first()
    
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
        
    profile.bio = data.get('bio', profile.bio)
    profile.profile_picture = data.get('profile_picture', profile.profile_picture)
    profile.website = data.get('website', profile.website)
    db.session.commit()
    return jsonify(profile.to_dict()), 200

# ========== CONTENT ROUTES ==========
@resources_bp.route('/content', methods=['POST'])
@jwt_required()
def create_content():
    data = request.get_json()
    user_id = get_jwt_identity()

    required_fields = ['title', 'body', 'content_type', 'category_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    try:
        content = Content(
            title=data['title'],
            body=data['body'],
            content_type=data['content_type'],
            category_id=data['category_id'],
            author_id=user_id
        )
        db.session.add(content)
        db.session.commit()
        return jsonify(content.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@resources_bp.route('/content', methods=['GET'])
def get_all_content():
    content = Content.query.filter_by(is_deleted=False).all()
    return jsonify([c.to_dict() for c in content]), 200

@resources_bp.route('/content/<int:content_id>', methods=['GET'])
def get_content_by_id(content_id):
    content = Content.query.filter_by(id=content_id, is_deleted=False).first()
    return jsonify(content.to_dict() if content else {"error": "Content not found"}), 200 if content else 404

# ========== CATEGORY ROUTES ==========
@resources_bp.route('/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([c.to_dict() for c in categories]), 200

# ========== SUBSCRIPTION ROUTES ==========
@resources_bp.route('/subscribe/category/<int:category_id>', methods=['POST'])
@jwt_required()
def subscribe_category(category_id):
    current_user = get_jwt_identity()
    
    if Subscription.query.filter_by(user_id=current_user, category_id=category_id).first():
        return jsonify({"error": "Already subscribed to this category"}), 400
        
    subscription = Subscription(user_id=current_user, category_id=category_id)
    db.session.add(subscription)
    db.session.commit()
    return jsonify(subscription.to_dict()), 201

# ========== WISHLIST ROUTES ==========
@resources_bp.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    data = request.get_json()
    current_user = get_jwt_identity()
    
    if not data.get('content_id'):
        return jsonify({"error": "content_id is required"}), 400
        
    if Wishlist.query.filter_by(user_id=current_user, content_id=data['content_id']).first():
        return jsonify({"error": "Content already in wishlist"}), 400
        
    wishlist = Wishlist(user_id=current_user, content_id=data['content_id'])
    db.session.add(wishlist)
    db.session.commit()
    return jsonify(wishlist.to_dict()), 201

# ========== LIKE ROUTES ==========
@resources_bp.route('/like', methods=['POST'])
@jwt_required()
def like_content():
    data = request.get_json()
    current_user = get_jwt_identity()
    
    if not data.get('content_id') or not data.get('like_type'):
        return jsonify({"error": "content_id and like_type are required"}), 400
        
    existing_like = Like.query.filter_by(user_id=current_user, content_id=data['content_id']).first()
    if existing_like:
        existing_like.like_type = LikeType(data['like_type'])
    else:
        like = Like(
            user_id=current_user,
            content_id=data['content_id'],
            like_type=LikeType(data['like_type'])
        )
        db.session.add(like)
    
    db.session.commit()
    return jsonify({"message": "Like updated"}), 200

# ========== COMMENT ROUTES ==========
@resources_bp.route('/content/<int:content_id>/comments', methods=['GET'])
def get_content_comments(content_id):
    comments = Comment.query.filter_by(content_id=content_id, is_deleted=False).all()
    return jsonify([c.to_dict() for c in comments]), 200

@resources_bp.route('/comments', methods=['POST'])
@jwt_required()
def add_comment():
    data = request.get_json()
    current_user = get_jwt_identity()
    
    if not data.get('content_id') or not data.get('body'):
        return jsonify({"error": "content_id and body are required"}), 400
        
    comment = Comment(
        user_id=current_user,
        content_id=data['content_id'],
        body=data['body']
    )
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201

# ========== ADMIN ROUTES ==========
@resources_bp.route('/admin/content/<int:content_id>/approve', methods=['POST'])
@jwt_required()
def approve_content(content_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != UserRole.ADMIN:
        return jsonify({"error": "Unauthorized"}), 403
        
    content = Content.query.get(content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404
        
    content.approval_status = ApprovalStatus.APPROVED
    content.approved_by_id = current_user.id
    db.session.commit()
    return jsonify(content.to_dict()), 200

@resources_bp.route('/admin/users/<int:user_id>/deactivate', methods=['POST'])
@jwt_required()
def deactivate_user(user_id):
    current_user = User.query.get(get_jwt_identity())
    if current_user.role != UserRole.ADMIN:
        return jsonify({"error": "Unauthorized"}), 403
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    user.is_active = False
    db.session.commit()
    return jsonify({"message": "User deactivated"}), 200

# ========== REGISTER BLUEPRINT ==========
app.register_blueprint(resources_bp, url_prefix='/api')

if __name__ == '__main__':
    app.run(debug=True)