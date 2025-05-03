import json
from datetime import datetime, timedelta, timezone
from app import app, db
from models import (
    User, Content, Category, Profile, Subscription,
    Wishlist, Comment, Like, Notification, Share, Flag,
    Conversation, ConversationParticipant, Message, SharedContent,
    UserRole, ContentType, ApprovalStatus, NotificationType
)

def utc_now():
    return datetime.now(timezone.utc)

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

        # === USERS ===
        users = []
        user_data = [
            {"username": "admin_user", "email": "admin@moringa.admin.com", "role": UserRole.ADMIN},
            {"username": "tech_writer1", "email": "writer1@moringa.techwriter.com", "role": UserRole.TECHWRITER},
            {"username": "tech_writer2", "email": "writer2@moringa.techwriter.com", "role": UserRole.TECHWRITER},
            {"username": "student1", "email": "student1@moringa.student.com", "role": UserRole.USER},
            {"username": "student2", "email": "student2@moringa.student.com", "role": UserRole.USER},
            {"username": "student3", "email": "student3@moringa.student.com", "role": UserRole.USER},
        ]

        for user_info in user_data:
            user = User(
                username=user_info["username"],
                email=user_info["email"],
                role=user_info["role"]
            )
            user.password = "password123"  # Uses the password setter
            db.session.add(user)
            users.append(user)
        
        db.session.commit()
        print("✅ Users created")

        # === PROFILES ===
        profiles = []
        interests = ["Web Development", "Mobile Apps", "Data Science", "Cybersecurity"]
        for user in users:
            profile = Profile(
                user_id=user.id,
                bio=f"This is {user.username}'s bio. I love technology and learning new things!",
                profile_picture=f"https://i.pravatar.cc/300?u={user.email}",
                website=f"https://{user.username.replace('_', '-')}.portfolio.com",
                interests=json.dumps(interests[:2])  # Each user gets first 2 interests
            )
            profiles.append(profile)
        
        db.session.add_all(profiles)
        db.session.commit()
        print("✅ Profiles created")

        # === CONTENT ===
        contents = []
        content_data = [
            {
                "title": "Introduction to Cybersecurity", 
                "body": "Learn the basics of cybersecurity including common threats and protection methods...", 
                "content_type": ContentType.ARTICLE,
                "author": users[1],  # tech writer
                "category": categories[0],  # Cyber-Security
                "approval_status": ApprovalStatus.APPROVED,
                "media_url": None,
                "view_count": 150
            },
            {
                "title": "React Hooks Explained", 
                "body": "A comprehensive guide to React Hooks with practical examples...", 
                "content_type": ContentType.VIDEO,
                "author": users[2],  # tech writer
                "category": categories[1],  # Full-Stack
                "approval_status": ApprovalStatus.APPROVED,
                "media_url": "https://example.com/videos/react-hooks",
                "view_count": 320
            },
            {
                "title": "Getting Started with Docker", 
                "body": "Step-by-step tutorial for beginners to containerization...", 
                "content_type": ContentType.ARTICLE,
                "author": users[3],  # student
                "category": categories[2],  # DevOps
                "approval_status": ApprovalStatus.PENDING,
                "media_url": None,
                "view_count": 45
            },
            {
                "title": "Machine Learning Basics", 
                "body": "Understanding the fundamentals of ML algorithms...", 
                "content_type": ContentType.ARTICLE,
                "author": users[1],  # tech writer
                "category": categories[3],  # AI/ML
                "approval_status": ApprovalStatus.APPROVED,
                "media_url": None,
                "view_count": 210
            },
        ]

        for data in content_data:
            content = Content(
                title=data["title"],
                body=data["body"],
                content_type=data["content_type"],
                author_id=data["author"].id,
                category_id=data["category"].id,
                approval_status=data["approval_status"],
                media_url=data["media_url"],
                view_count=data["view_count"]
            )
            contents.append(content)
        
        db.session.add_all(contents)
        db.session.commit()
        print("✅ Content created")

        # === COMMENTS ===
        comments = []
        comment_data = [
            {"user": users[3], "content": contents[0], "body": "Great article! Very helpful for beginners."},
            {"user": users[4], "content": contents[0], "body": "I learned so much from this, thank you!"},
            {"user": users[0], "content": contents[1], "body": "Excellent video tutorial, well explained!"},
            {"user": users[2], "content": contents[3], "body": "This covers all the fundamentals nicely."},
        ]

        # First create all root comments
        for data in comment_data:
            comment = Comment(
                user_id=data["user"].id,
                content_id=data["content"].id,
                body=data["body"]
            )
            db.session.add(comment)
            comments.append(comment)

        # Commit root comments first
        db.session.commit()

        # Now add replies (need parent comments to exist first)
        reply_data = [
            {"parent": comments[0], "user": users[4], "body": "I agree, the explanations are very clear!"},
            {"parent": comments[1], "user": users[3], "body": "Glad you found it useful too!"},
        ]

        for data in reply_data:
            reply = Comment(
                user_id=data["user"].id,
                content_id=data["parent"].content_id,
                parent_comment_id=data["parent"].id,
                body=data["body"]
            )
            db.session.add(reply)
            comments.append(reply)

        db.session.commit()
        print("✅ Comments created")

        # === LIKES ===
        likes = []
        like_data = [
            {"user": users[3], "content": contents[0], "like_type": "like"},
            {"user": users[4], "content": contents[0], "like_type": "like"},
            {"user": users[0], "content": contents[1], "like_type": "like"},
            {"user": users[1], "content": contents[3], "like_type": "like"},
            {"user": users[2], "content": contents[3], "like_type": "like"},
            {"user": users[5], "content": contents[1], "like_type": "like"},
        ]

        for data in like_data:
            like = Like(
                user_id=data["user"].id,
                content_id=data["content"].id,
                like_type=data["like_type"]
            )
            likes.append(like)
        
        db.session.add_all(likes)
        db.session.commit()
        print("✅ Likes created")

        # === SUBSCRIPTIONS ===
        subscriptions = []
        subscription_data = [
            {"user": users[3], "category": categories[0]},  # student1 -> Cyber-Security
            {"user": users[4], "category": categories[1]},  # student2 -> Full-Stack
            {"user": users[0], "category": categories[2]},  # admin -> DevOps
            {"user": users[5], "category": categories[3]},  # student3 -> AI/ML
        ]

        for data in subscription_data:
            subscription = Subscription(
                user_id=data["user"].id,
                category_id=data["category"].id
            )
            subscriptions.append(subscription)
        
        db.session.add_all(subscriptions)
        db.session.commit()
        print("✅ Subscriptions created")

        # === WISHLISTS ===
        wishlists = []
        wishlist_data = [
            {"user": users[3], "content": contents[1]},  # student1 -> React video
            {"user": users[4], "content": contents[0]},  # student2 -> Cyber article
            {"user": users[5], "content": contents[3]},  # student3 -> ML article
        ]

        for data in wishlist_data:
            wishlist = Wishlist(
                user_id=data["user"].id,
                content_id=data["content"].id
            )
            wishlists.append(wishlist)
        
        db.session.add_all(wishlists)
        db.session.commit()
        print("✅ Wishlists created")

        # === FLAGS === (for testing moderation)
        flags = []
        flag_data = [
            {
                "content": contents[1], 
                "flagged_by": users[3], 
                "reason": "Potential outdated information in video"
            },
            {
                "content": contents[2], 
                "flagged_by": users[4], 
                "reason": "Needs technical review"
            },
        ]

        for data in flag_data:
            flag = Flag(
                content_id=data["content"].id,
                flagged_by_id=data["flagged_by"].id,
                reason=data["reason"]
            )
            flags.append(flag)
            # Update content status
            data["content"].approval_status = ApprovalStatus.FLAGGED
        
        db.session.add_all(flags)
        db.session.commit()
        print("✅ Flags created")

        # === CONVERSATIONS ===
        conversations = []
        conversation_data = [
            {"participants": [users[0], users[3]]},  # admin - student1
            {"participants": [users[1], users[4]]},  # tech_writer1 - student2
            {"participants": [users[2], users[5]]},  # tech_writer2 - student3
        ]

        for data in conversation_data:
            conv = Conversation()
            db.session.add(conv)
            db.session.flush()  # To get the ID
            
            for participant in data["participants"]:
                cp = ConversationParticipant(
                    conversation_id=conv.id,
                    user_id=participant.id
                )
                db.session.add(cp)
            
            conversations.append(conv)
        
        db.session.commit()
        print("✅ Conversations created")

        # === MESSAGES ===
        messages = []
        message_data = [
            {
                "conversation": conversations[0],
                "sender": users[0],
                "content": "Hi there! How can I help you today?",
                "hours_ago": 2
            },
            {
                "conversation": conversations[0],
                "sender": users[3],
                "content": "Hello! I had a question about the cybersecurity content",
                "hours_ago": 1
            },
            {
                "conversation": conversations[1],
                "sender": users[1],
                "content": "Did you get a chance to review the React tutorial?",
                "hours_ago": 5
            },
            {
                "conversation": conversations[1],
                "sender": users[4],
                "content": "Yes! It was very helpful, thank you!",
                "hours_ago": 3
            },
            {
                "conversation": conversations[2],
                "sender": users[2],
                "content": "Let me know if you need help with your project",
                "hours_ago": 8
            },
        ]

        for data in message_data:
            message = Message(
                conversation_id=data["conversation"].id,
                sender_id=data["sender"].id,
                content=data["content"],
                created_at=utc_now() - timedelta(hours=data["hours_ago"])
            )
            messages.append(message)
        
        db.session.add_all(messages)
        db.session.commit()
        print("✅ Messages created")

        # === SHARED CONTENT ===
        shared_content = []
        shared_data = [
            {
                "conversation": conversations[0],
                "content": contents[0],
                "shared_by": users[0]
            },
            {
                "conversation": conversations[1],
                "content": contents[1],
                "shared_by": users[1]
            },
        ]

        for data in shared_data:
            shared = SharedContent(
                conversation_id=data["conversation"].id,
                content_id=data["content"].id,
                shared_by_id=data["shared_by"].id,
                shared_at=utc_now() - timedelta(hours=1)
            )
            shared_content.append(shared)
        
        db.session.add_all(shared_content)
        db.session.commit()
        print("✅ Shared content created")

        # === NOTIFICATIONS ===
        notifications = []
        notification_data = [
            {
                "user": users[3], 
                "message": "Your comment received a reply!", 
                "type": NotificationType.NEW_REPLY,
                "content": contents[0],
                "hours_ago": 3
            },
            {
                "user": users[0], 
                "message": "New content needs approval", 
                "type": NotificationType.CONTENT_APPROVED,
                "content": contents[2],
                "hours_ago": 6
            },
            {
                "user": users[1], 
                "message": "Your content was flagged for review", 
                "type": NotificationType.CONTENT_FLAGGED,
                "content": contents[1],
                "hours_ago": 2
            },
            {
                "user": users[4], 
                "message": "You received a new message", 
                "type": NotificationType.NEW_MESSAGE,
                "content": None,
                "hours_ago": 1
            },
        ]

        for data in notification_data:
            notification = Notification(
                user_id=data["user"].id,
                message=data["message"],
                notification_type=data["type"],
                related_content_id=data["content"].id if data["content"] else None,
                created_at=utc_now() - timedelta(hours=data["hours_ago"])
            )
            notifications.append(notification)
        
        db.session.add_all(notifications)
        db.session.commit()
        print("✅ Notifications created")

        print("🌱 Database seeding completed successfully!")

if __name__ == "__main__":
    create_sample_data()