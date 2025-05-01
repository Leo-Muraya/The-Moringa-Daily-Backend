from datetime import datetime
from app import app, db
from models import (
    User, Content, Category, Profile, Subscription,
    Wishlist, Comment, Like, Notification, Share,
    UserRole, ContentType, ApprovalStatus, LikeType
)

def create_sample_data():
    with app.app_context():
        print("🔥 Dropping and recreating database tables...")
        db.drop_all()
        db.create_all()

        # === CATEGORIES ===
        categories = [
            Category(name="Cyber-Security", description="Tech-related content"),
            Category(name="Full-Stack", description="Frontend and backend development"),
            Category(name="DevOps", description="CI/CD, cloud, infrastructure"),
            Category(name="AI/ML", description="Machine Learning and AI discussions"),
            Category(name="Blockchain", description="Crypto, smart contracts, and more"),
            Category(name="UI/UX", description="Design and user experience"),
        ]
        db.session.add_all(categories)
        db.session.commit()
        print("✅ Categories created")

        # === USERS + PROFILES ===
        users = []
        user_data = [
            {"username": "collins", "email": "collins@moringa.student.com", "role": UserRole.USER},
            {"username": "ken", "email": "ken@moringa.techwriter.com", "role": UserRole.TECHWRITER},
            {"username": "mary", "email": "mary@moringa.admin.com", "role": UserRole.ADMIN},
            {"username": "sarah", "email": "sarah@moringa.student.com", "role": UserRole.USER},
            {"username": "james", "email": "james@moringa.techwriter.com", "role": UserRole.TECHWRITER},
            {"username": "linda", "email": "linda@moringa.admin.com", "role": UserRole.ADMIN},
        ]

        for user_info in user_data:
            user = User(
                username=user_info["username"],
                email=user_info["email"],
                role=user_info["role"]
            )
            user.password = "123456789"  # This uses the password setter from your model
            db.session.add(user)
            users.append(user)
        
        db.session.commit()
        print("✅ Users created")

        # Create profiles for users
        profiles = []
        for i, user in enumerate(users):
            profile = Profile(
                user_id=user.id,
                bio=f"This is {user.username}'s bio",
                profile_picture=f"https://picsum.photos/seed/{user.username}/200",
                website=f"https://{user.username}.tech"
            )
            profiles.append(profile)
        
        db.session.add_all(profiles)
        db.session.commit()
        print("✅ Profiles created")

        # === CONTENT ===
        contents = [
            {
                "title": "The Future of AI", 
                "body": "AI is evolving fast...", 
                "content_type": ContentType.ARTICLE,
                "author": users[0],
                "category": categories[0]
            },
            {
                "title": "Deep Dive into React", 
                "body": "React hooks and context API...", 
                "content_type": ContentType.ARTICLE,
                "author": users[1],
                "category": categories[1]
            },
            {
                "title": "Why DevOps Matters", 
                "body": "CI/CD practices in 2025...", 
                "content_type": ContentType.VIDEO,
                "author": users[2],
                "category": categories[2]
            },
            {
                "title": "Prompt Engineering", 
                "body": "Optimizing LLM responses...", 
                "content_type": ContentType.ARTICLE,
                "author": users[3],
                "category": categories[3]
            },
            {
                "title": "NFTs & the Future", 
                "body": "Digital ownership explained...", 
                "content_type": ContentType.ARTICLE,
                "author": users[4],
                "category": categories[4]
            },
            {
                "title": "Design Systems", 
                "body": "Atomic design in practice...", 
                "content_type": ContentType.ARTICLE,
                "author": users[5],
                "category": categories[5]
            },
        ]

        content_objects = []
        for content_data in contents:
            content = Content(
                title=content_data["title"],
                body=content_data["body"],
                content_type=content_data["content_type"],
                author_id=content_data["author"].id,
                category_id=content_data["category"].id,
                approval_status=ApprovalStatus.APPROVED
            )
            content_objects.append(content)
        
        db.session.add_all(content_objects)
        db.session.commit()
        print("✅ Content created")

        # === COMMENTS ===
        comments = [
            {"user": users[0], "content": content_objects[1], "body": "Nice write-up!"},
            {"user": users[1], "content": content_objects[0], "body": "Very insightful."},
            {"user": users[2], "content": content_objects[2], "body": "Love the video!"},
            {"user": users[3], "content": content_objects[3], "body": "LLMs are the future."},
            {"user": users[4], "content": content_objects[4], "body": "Great intro to NFTs."},
            {"user": users[5], "content": content_objects[5], "body": "Super helpful tips."},
        ]

        comment_objects = []
        for comment_data in comments:
            comment = Comment(
                user_id=comment_data["user"].id,
                content_id=comment_data["content"].id,
                body=comment_data["body"]
            )
            comment_objects.append(comment)
        
        db.session.add_all(comment_objects)
        db.session.commit()
        print("✅ Comments created")

        # === LIKES ===
        likes = [
            {"user": users[0], "content": content_objects[0], "like_type": LikeType.LIKE},
            {"user": users[1], "content": content_objects[1], "like_type": LikeType.LIKE},
            {"user": users[2], "content": content_objects[2], "like_type": LikeType.LIKE},
            {"user": users[3], "content": content_objects[3], "like_type": LikeType.LIKE},
            {"user": users[4], "content": content_objects[4], "like_type": LikeType.LIKE},
            {"user": users[5], "content": content_objects[5], "like_type": LikeType.LIKE},
        ]

        like_objects = []
        for like_data in likes:
            like = Like(
                user_id=like_data["user"].id,
                content_id=like_data["content"].id,
                like_type=like_data["like_type"]
            )
            like_objects.append(like)
        
        db.session.add_all(like_objects)
        db.session.commit()
        print("✅ Likes created")

        # === SHARES ===
        shares = [
            {"user": users[0], "content": content_objects[2], "shared_with": "friend@example.com"},
            {"user": users[1], "content": content_objects[1], "shared_with": "colleague@example.com"},
        ]

        share_objects = []
        for share_data in shares:
            share = Share(
                user_id=share_data["user"].id,
                content_id=share_data["content"].id,
                shared_with=share_data["shared_with"]
            )
            share_objects.append(share)
        
        db.session.add_all(share_objects)
        db.session.commit()
        print("✅ Shares created")

        # === SUBSCRIPTIONS ===
        subscriptions = [
            {"user": users[2], "category": categories[0]},
            {"user": users[3], "category": categories[1]},
        ]

        subscription_objects = []
        for sub_data in subscriptions:
            subscription = Subscription(
                user_id=sub_data["user"].id,
                category_id=sub_data["category"].id
            )
            subscription_objects.append(subscription)
        
        db.session.add_all(subscription_objects)
        db.session.commit()
        print("✅ Subscriptions created")

        # === WISHLISTS ===
        wishlists = [
            {"user": users[4], "content": content_objects[1]},
            {"user": users[5], "content": content_objects[0]},
        ]

        wishlist_objects = []
        for wish_data in wishlists:
            wishlist = Wishlist(
                user_id=wish_data["user"].id,
                content_id=wish_data["content"].id
            )
            wishlist_objects.append(wishlist)
        
        db.session.add_all(wishlist_objects)
        db.session.commit()
        print("✅ Wishlists created")

        # === NOTIFICATIONS ===
        notifications = [
            {"user": users[0], "message": "Your content got a new like!", "is_read": False},
            {"user": users[1], "message": "You have a new comment!", "is_read": False},
            {"user": users[2], "message": "Someone subscribed to your content.", "is_read": True},
        ]

        notification_objects = []
        for notif_data in notifications:
            notification = Notification(
                user_id=notif_data["user"].id,
                message=notif_data["message"],
                is_read=notif_data["is_read"]
            )
            notification_objects.append(notification)
        
        db.session.add_all(notification_objects)
        db.session.commit()
        print("✅ Notifications created")

        print("🌱 Database seeded successfully!")

if __name__ == "__main__":
    create_sample_data()