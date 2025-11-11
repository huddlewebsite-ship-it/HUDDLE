import sys
import re
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from datetime import datetime

# ==================== FLASK APP INIT ====================
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins for development

# ==================== MONGODB ATLAS CONNECTION ====================
MONGO_URI = "mongodb+srv://arpitsaxenamarch1996_db_user:arpit123@cluster0.mkgxsea.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to main student network database
def connect_to_mongodb():
    try:
        print("🔄 Connecting to MongoDB Atlas - student_network_db...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["student_network_db"]
        client.admin.command('ping')

        users_collection = db["users"]
        groups_collection = db["groups"]
        posts_collection = db["posts"]
        questions_collection = db["questions"]
        discussions_collection = db["discussions"]

        try:
            users_collection.create_index("email", unique=True)
            groups_collection.create_index("project_name")
            questions_collection.create_index("createdAt")
            questions_collection.create_index("votes")
        except Exception as index_error:
            print(f"⚠️ Index creation skipped: {index_error}")

        print("✅ student_network_db connected!")
        print(f"   Database: {db.name}")
        print(f"   Collections: users, groups, posts, questions, discussions\n")

        return users_collection, groups_collection, posts_collection, questions_collection, discussions_collection
    except Exception as e:
        print(f"❌ student_network_db CONNECTION FAILED: {e}\n")
        sys.exit(1)

# Connect to separate chat database
def connect_to_chat_db():
    try:
        print("🔄 Connecting to MongoDB Atlas - chat_db...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        chat_db = client["chat_db"]
        chats_collection = chat_db["chats"]

        print("✅ chat_db connected!")
        print(f"   Database: {chat_db.name}")
        print(f"   Collections: {chat_db.list_collection_names() or ['chats']}\n")

        return chats_collection
    except Exception as e:
        print(f"❌ chat_db CONNECTION FAILED: {e}\n")
        sys.exit(1)

# Initialize both database connections
users_collection, groups_collection, posts_collection, questions_collection, discussions_collection = connect_to_mongodb()
chats_collection = connect_to_chat_db()

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# ==================== HTML PAGE ROUTES ====================

@app.route('/')
def index():
    return send_from_directory('.', 'frontpage.html')

@app.route('/<path:filename>')
def serve_file(filename):
    """Serve any HTML file"""
    return send_from_directory('.', filename)

# ==================== USER AUTHENTICATION ROUTES ====================

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        fullName = data.get('fullName')
        university = data.get('university')
        branch = data.get('branch')
        academicYear = data.get('academicYear')
        skills = data.get('skills', [])

        if not (email and password and fullName and university and branch and academicYear):
            return jsonify({'error': 'All fields except skills are required'}), 400

        if users_collection.find_one({'email': email}):
            return jsonify({'error': 'User already exists'}), 409

        pw_hash = hash_password(password)

        user = {
            'email': email,
            'password': pw_hash,
            'fullName': fullName,
            'university': university,
            'branch': branch,
            'academicYear': academicYear,
            'skills': skills,
            'profilePhotoUrl': '',
            'coverPhotoUrl': '',
            'bio': 'Passionate student focused on learning and building innovative projects.',
            'createdAt': datetime.utcnow()
        }

        result = users_collection.insert_one(user)
        print(f"✅ User created: {email} | ID: {result.inserted_id}")

        return jsonify({
            'success': True, 
            'message': 'Account created successfully!',
            'user': {
                'id': str(result.inserted_id),
                'email': email,
                'fullName': fullName,
                'university': university,
                'branch': branch,
                'academicYear': academicYear,
                'skills': skills,
                'profilePhotoUrl': '',
                'coverPhotoUrl': '',
                'bio': user['bio']
            }
        }), 200
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return jsonify({'error': 'Failed to create account'}), 500

@app.route("/login", methods=["POST"])
def login_api():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        user = users_collection.find_one({"email": email})

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return jsonify({'error': 'Incorrect password'}), 401

        user_data = {
            "id": str(user['_id']),
            "email": user['email'],
            "fullName": user.get('fullName', ''),
            "university": user.get('university', ''),
            "branch": user.get('branch', ''),
            "academicYear": user.get('academicYear', ''),
            "skills": user.get('skills', []),
            "profilePhotoUrl": user.get('profilePhotoUrl', ''),
            "coverPhotoUrl": user.get('coverPhotoUrl', ''),
            "bio": user.get('bio', '')
        }

        print(f"✅ User logged in: {email}")
        return jsonify({'success': True, 'user': user_data}), 200
    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

# ==================== USER PROFILE ROUTES ====================

@app.route("/updateprofile", methods=["POST"])
def update_profile():
    try:
        data = request.get_json()
        user_id = data.get("userId")

        if not user_id:
            return jsonify({"error": "User ID required"}), 400

        update_data = {}
        for field in ['fullName', 'bio', 'profilePhotoUrl', 'coverPhotoUrl', 'skills']:
            if field in data:
                update_data[field] = data[field]

        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )

        if result.matched_count > 0:
            print(f"✅ Profile updated: {user_id}")
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        print(f"❌ Update profile error: {e}")
        return jsonify({"error": "Failed to update"}), 500

@app.route("/getuser/<user_id>", methods=["GET"])
def get_user(user_id):
    try:
        print(f"🔍 Attempting to fetch user: {user_id}")
        
        user = None
        
        try:
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if user:
                print(f"✅ Found user by ObjectId")
        except:
            pass
        
        if not user:
            try:
                user = users_collection.find_one({"_id": user_id})
                if user:
                    print(f"✅ Found user by string _id")
            except:
                pass
        
        if not user:
            user = users_collection.find_one({"id": user_id})
            if user:
                print(f"✅ Found user by id field")

        if not user:
            print(f"❌ User not found: {user_id}")
            return jsonify({"success": False, "error": "User not found"}), 404

        user_data = {
            "id": str(user.get('_id', user.get('id', user_id))),
            "email": user.get('email', ''),
            "fullName": user.get('fullName', ''),
            "university": user.get('university', ''),
            "branch": user.get('branch', ''),
            "academicYear": user.get('academicYear', ''),
            "skills": user.get('skills', []),
            "profilePhotoUrl": user.get('profilePhotoUrl', ''),
            "coverPhotoUrl": user.get('coverPhotoUrl', ''),
            "bio": user.get('bio', '')
        }

        print(f"✅ Retrieved user: {user_data['fullName']} (ID: {user_data['id']})")
        return jsonify({"success": True, "user": user_data}), 200
    except Exception as e:
        print(f"❌ Get user error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Failed to get user: {str(e)}"}), 500

# ==================== GROUP ROUTES ====================

@app.route('/getavailablegroups', methods=['GET', 'POST'])
def get_groups():
    try:
        if request.method == 'POST' and request.json:
            data = request.get_json()
            userid = str(data.get('userId', ''))
        else:
            userid = str(request.args.get('userId', ''))
        
        groups = list(groups_collection.find().sort('createdAt', -1))
        groupslist = []
        for group in groups:
            members = group.get('members', [])
            members = [str(m) for m in members]
            preferredteamsize = group.get('preferred_team_size')
            maxsize = None
            if preferredteamsize:
                match = re.search(r'(\d+)', str(preferredteamsize))
                if match:
                    maxsize = int(match.group(1))
                else:
                    try:
                        maxsize = int(preferredteamsize)
                    except:
                        maxsize = None
            
            isfull = False
            if maxsize and len(members) >= maxsize:
                isfull = True
            ismember = userid in members if userid else False
            projectname = group.get('project_name')
            if not projectname or not str(projectname).strip():
                projectname = "Unnamed Group"
            
            groupslist.append({
                "groupId": str(group['_id']),
                "creatoruserid": str(group.get('creatoruserid')),
                "members": members,
                "memberCount": len(members),
                "maxMembers": maxsize,
                "isFull": isfull,
                "isMember": ismember,
                "preferredteamsize": preferredteamsize,
                "projectname": projectname,
                "descriptionobjective": group.get('description_objective', ""),
                "projecttimeline": group.get('project_timeline', ""),
                "requiredskills": group.get('required_skills', []),
                "createdAt": str(group.get('createdAt', datetime.utcnow()).isoformat())
            })
        return jsonify(success=True, groups=groupslist), 200
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify(error="Could not load groups", details=str(e)), 500

@app.route("/creategroup", methods=["POST"])
def create_group():
    try:
        data = request.get_json()

        if not data.get("project_name"):
            return jsonify({"error": "Project name required"}), 400

        creator_id = str(data.get("creatoruserid"))
        
        group = {
            "creatoruserid": creator_id,
            "project_name": data.get("project_name"),
            "description_objective": data.get("description_objective", ""),
            "preferred_team_size": data.get("preferred_team_size", ""),
            "required_skills": data.get("required_skills", []),
            "project_timeline": data.get("project_timeline", ""),
            "members": [creator_id],
            "createdAt": datetime.utcnow()
        }

        result = groups_collection.insert_one(group)
        print(f"✅ Group created: {group['project_name']} | ID: {result.inserted_id}")

        return jsonify({
            "success": True, 
            "message": "Group created successfully!",
            "groupId": str(result.inserted_id)
        }), 200
    except Exception as e:
        print(f"❌ Create group error: {e}")
        return jsonify({"error": "Failed to create group"}), 500

@app.route("/joingroup", methods=["POST"])
def join_group_api():
    try:
        data = request.get_json()
        user_id = str(data.get("user_id"))
        group_id = data.get("group_id")

        if not user_id or not group_id:
            return jsonify({"error": "User ID and Group ID required"}), 400

        print(f"🔍 Join group - User: {user_id}, Group: {group_id}")

        group = groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            print(f"❌ Group not found: {group_id}")
            return jsonify({"error": "Group not found"}), 404

        result = groups_collection.update_one(
            {"_id": ObjectId(group_id)},
            {"$addToSet": {"members": str(user_id)}}
        )

        if result.matched_count > 0:
            print(f"✅ User {user_id} joined group {group_id}")
            return jsonify({"success": True, "message": "Joined successfully!"}), 200
        else:
            return jsonify({"error": "Group not found"}), 404
    except Exception as e:
        print(f"❌ Join group error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to join group: {str(e)}"}), 500

@app.route("/leavegroup", methods=["POST"])
def leave_group_api():
    try:
        data = request.get_json()
        user_id = str(data.get("user_id"))
        group_id = data.get("group_id")

        if not user_id or not group_id:
            return jsonify({"error": "User ID and Group ID required"}), 400

        print(f"🔍 Leave group - User: {user_id}, Group: {group_id}")

        group = groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            return jsonify({"error": "Group not found"}), 404

        result = groups_collection.update_one(
            {"_id": ObjectId(group_id)},
            {"$pull": {"members": str(user_id)}}
        )

        if result.matched_count > 0:
            print(f"✅ User {user_id} left group {group_id}")
            return jsonify({"success": True, "message": "Left group successfully!"}), 200
        else:
            return jsonify({"error": "Group not found"}), 404
    except Exception as e:
        print(f"❌ Leave group error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to leave group: {str(e)}"}), 500

@app.route("/getmygroups", methods=["GET"])
def get_my_groups():
    try:
        user_id = str(request.args.get('userId'))
        if not user_id or user_id == 'None':
            return jsonify({"error": "User ID required"}), 400

        my_groups = list(groups_collection.find(
            {'members': user_id},
            {'_id': 1, 'project_name': 1} 
        ))

        groups_list = []
        for group in my_groups:
            groups_list.append({
                "groupId": str(group['_id']),
                "groupName": group.get("project_name", "Unnamed Group")
            })
        
        print(f"✅ Retrieved {len(groups_list)} groups for user {user_id}")
        return jsonify({"success": True, "groups": groups_list}), 200

    except Exception as e:
        print(f"❌ Get my groups error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Could not load user's groups"}), 500

# ==================== POST ROUTES ====================

@app.route("/createpost", methods=["POST"])
def create_post():
    try:
        data = request.get_json()

        post = {
            "userId": data.get("userId"),
            "userName": data.get("userName"),
            "userPhoto": data.get("userPhoto", ""),
            "content": data.get("content", ""),
            "imageUrl": data.get("imageUrl", ""),
            "likes": [],
            "comments": [],
            "createdAt": datetime.utcnow()
        }

        result = posts_collection.insert_one(post)
        print(f"✅ Post created by: {post['userName']} | ID: {result.inserted_id}")

        return jsonify({
            "success": True,
            "message": "Post created successfully!",
            "postId": str(result.inserted_id)
        }), 200
    except Exception as e:
        print(f"❌ Create post error: {e}")
        return jsonify({"error": "Failed to create post"}), 500

@app.route("/getposts", methods=["GET"])
def get_posts():
    try:
        posts = list(posts_collection.find({}).sort("createdAt", -1).limit(50))

        posts_list = []
        for post in posts:
            posts_list.append({
                "postId": str(post['_id']),
                "userId": post.get("userId"),
                "userName": post.get("userName"),
                "userPhoto": post.get("userPhoto", ""),
                "content": post.get("content", ""),
                "imageUrl": post.get("imageUrl", ""),
                "likes": post.get("likes", []),
                "comments": post.get("comments", []),
                "createdAt": post.get("createdAt", datetime.utcnow()).isoformat()
            })

        print(f"✅ Retrieved {len(posts_list)} posts")
        return jsonify({"success": True, "posts": posts_list}), 200
    except Exception as e:
        print(f"❌ Get posts error: {e}")
        return jsonify({"error": "Could not load posts"}), 500

# ==================== Q&A ROUTES (ENHANCED WITH FIXES) ====================

@app.route("/createquestion", methods=["POST"])
def create_question():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("title") or len(data.get("title", "").strip()) < 10:
            return jsonify({"error": "Question title must be at least 10 characters"}), 400

        question = {
            "userId": str(data.get("userId")),
            "userName": data.get("userName"),
            "userPhoto": data.get("userPhoto", ""),
            "title": data.get("title").strip(),
            "content": data.get("content", "").strip(),
            "tags": data.get("tags", []),
            "answers": [],
            "votes": 0,
            "views": 0,
            "createdAt": datetime.utcnow()
        }

        result = questions_collection.insert_one(question)
        print(f"✅ Question created: {question['title'][:50]}... | ID: {result.inserted_id}")

        return jsonify({
            "success": True,
            "message": "Question posted successfully!",
            "questionId": str(result.inserted_id)
        }), 200
    except Exception as e:
        print(f"❌ Create question error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to create question: {str(e)}"}), 500

@app.route("/getquestions", methods=["GET"])
def get_questions():
    """
    Enhanced getquestions with filtering, search, and pagination
    """
    try:
        # Get query parameters with defaults
        filter_type = request.args.get('filter', 'all').lower()
        search = request.args.get('search', '').strip()
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 5))))
        skip = (page - 1) * limit
        
        print(f"📥 GET /getquestions - filter: {filter_type}, search: '{search}', page: {page}, limit: {limit}")
        
        # Build the query
        query = {}
        
        # Add search functionality
        if search:
            # Remove # from search if present
            search_term = search.replace('#', '').strip()
            query['$or'] = [
                {'title': {'$regex': search_term, '$options': 'i'}},
                {'content': {'$regex': search_term, '$options': 'i'}},
                {'tags': {'$in': [search_term.lower()]}}
            ]
        
        # Apply filter
        if filter_type == 'unanswered':
            query['$or'] = [
                {'answers': {'$exists': False}},
                {'answers': {'$size': 0}}
            ]
        
        # Set up sorting
        if filter_type == 'most-voted':
            sort_field = "votes"
            sort_direction = -1
        elif filter_type == 'recent':
            sort_field = "createdAt"
            sort_direction = -1
        else:  # 'all' or default
            sort_field = "createdAt"
            sort_direction = -1
        
        # Execute query with sorting and pagination
        cursor = questions_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
        questions = list(cursor)
        
        # Count total for pagination
        total_count = questions_collection.count_documents(query)
        
        print(f"📊 Found {total_count} questions matching criteria, returning {len(questions)} for page {page}")
        
        # Format response
        questions_list = []
        for q in questions:
            # Ensure answers have all required fields
            formatted_answers = []
            for answer in q.get('answers', []):
                formatted_answer = {
                    'answerId': answer.get('answerId', str(ObjectId())),
                    'userId': str(answer.get('userId', '')),
                    'userName': answer.get('userName', 'Anonymous'),
                    'userPhoto': answer.get('userPhoto', ''),
                    'content': answer.get('content', ''),
                    'votes': int(answer.get('votes', 0)),
                    'accepted': bool(answer.get('accepted', False)),
                    'createdAt': answer.get('createdAt', datetime.utcnow().isoformat())
                }
                formatted_answers.append(formatted_answer)
            
            questions_list.append({
                "questionId": str(q['_id']),
                "userId": str(q.get("userId", '')),
                "userName": q.get("userName", 'Anonymous'),
                "userPhoto": q.get("userPhoto", ""),
                "title": q.get("title", "Untitled Question"),
                "content": q.get("content", ""),
                "tags": q.get("tags", []),
                "answers": formatted_answers,
                "votes": int(q.get("votes", 0)),
                "views": int(q.get("views", 0)),
                "createdAt": q.get("createdAt", datetime.utcnow()).isoformat()
            })

        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        print(f"✅ Retrieved {len(questions_list)} questions (Page {page}/{total_pages})")
        
        return jsonify({
            "success": True, 
            "questions": questions_list,
            "pagination": {
                "currentPage": page,
                "totalPages": total_pages,
                "totalItems": total_count,
                "itemsPerPage": limit
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Get questions error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Could not load questions: {str(e)}"}), 500

@app.route("/addanswer", methods=["POST"])
def add_answer():
    try:
        data = request.get_json()
        question_id = data.get("questionId")
        content = data.get("content", "").strip()

        if not question_id:
            return jsonify({"error": "Question ID required"}), 400
        
        if not content or len(content) < 5:
            return jsonify({"error": "Answer must be at least 5 characters"}), 400

        answer = {
            "answerId": str(ObjectId()),
            "userId": str(data.get("userId")),
            "userName": data.get("userName", "Anonymous"),
            "userPhoto": data.get("userPhoto", ""),
            "content": content,
            "votes": 0,
            "accepted": False,
            "createdAt": datetime.utcnow().isoformat()
        }

        result = questions_collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$push": {"answers": answer}}
        )

        if result.matched_count > 0:
            print(f"✅ Answer added to question {question_id}")
            return jsonify({"success": True, "message": "Answer posted!"}), 200
        else:
            return jsonify({"error": "Question not found"}), 404
    except Exception as e:
        print(f"❌ Add answer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to add answer: {str(e)}"}), 500

@app.route("/votequestion", methods=["POST"])
def vote_question():
    try:
        data = request.get_json()
        question_id = data.get("questionId")
        vote_type = data.get("voteType")

        if not question_id or not vote_type:
            return jsonify({"error": "Question ID and vote type required"}), 400

        increment = 1 if vote_type == "up" else -1

        result = questions_collection.update_one(
            {"_id": ObjectId(question_id)},
            {"$inc": {"votes": increment}}
        )

        if result.matched_count > 0:
            print(f"✅ Vote recorded for question {question_id}: {vote_type}")
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Question not found"}), 404
    except Exception as e:
        print(f"❌ Vote question error: {e}")
        return jsonify({"error": "Failed to vote"}), 500

@app.route("/acceptanswer", methods=["POST"])
def accept_answer():
    try:
        data = request.get_json()
        question_id = data.get("questionId")
        answer_id = data.get("answerId")
        user_id = str(data.get("userId"))
        
        if not all([question_id, answer_id, user_id]):
            return jsonify({"error": "Question ID, Answer ID, and User ID required"}), 400
        
        question_id_obj = ObjectId(question_id)
        
        question = questions_collection.find_one({"_id": question_id_obj})
        if not question:
            return jsonify({"error": "Question not found"}), 404
        
        if str(question.get("userId")) != user_id:
            return jsonify({"error": "Unauthorized: You can only accept answers for your questions"}), 403
        
        # Un-accept any previously accepted answers
        questions_collection.update_one(
            {"_id": question_id_obj},
            {"$set": {"answers.$[].accepted": False}}
        )
        
        # Accept the specified answer
        result = questions_collection.update_one(
            {"_id": question_id_obj, "answers.answerId": answer_id},
            {"$set": {"answers.$.accepted": True}}
        )
        
        if result.matched_count > 0:
            print(f"✅ Answer {answer_id} accepted for question {question_id}")
            return jsonify({"success": True, "message": "Answer accepted!"}), 200
        else:
            return jsonify({"error": "Answer not found"}), 404
        
    except Exception as e:
        print(f"❌ Accept answer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to accept answer: {str(e)}"}), 500

@app.route("/voteanswer", methods=["POST"])
def vote_answer():
    try:
        data = request.get_json()
        question_id = data.get("questionId")
        answer_id = data.get("answerId")
        vote_type = data.get("voteType")
        
        if not all([question_id, answer_id, vote_type]):
            return jsonify({"error": "Question ID, Answer ID, and vote type required"}), 400
        
        if vote_type not in ['up', 'down']:
            return jsonify({"error": "Vote type must be 'up' or 'down'"}), 400
        
        question_id_obj = ObjectId(question_id)
        increment = 1 if vote_type == 'up' else -1
        
        result = questions_collection.update_one(
            {"_id": question_id_obj, "answers.answerId": answer_id},
            {"$inc": {"answers.$.votes": increment}}
        )
        
        if result.matched_count > 0:
            print(f"✅ Answer {answer_id} voted {vote_type}")
            return jsonify({"success": True, "message": f"Answer {vote_type}voted!"}), 200
        else:
            return jsonify({"error": "Answer not found"}), 404
        
    except Exception as e:
        print(f"❌ Vote answer error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to vote on answer: {str(e)}"}), 500

# ==================== NOTIFICATIONS ROUTE ====================

@app.route('/getnotifications', methods=['GET'])
def get_notifications():
    try:
        user_id = str(request.args.get('userId'))
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400

        notifications_data = []

        user_groups = list(groups_collection.find({'members': user_id}))

        for group in user_groups:
            group_id = str(group["_id"])
            project_name = group.get('project_name', 'Unnamed Group')
            created_at = group.get('createdAt', datetime.utcnow()).isoformat()
            
            notifications_data.append({
                'id': f'group-{group_id}',
                'type': 'group',
                'name': project_name,
                'avatar': project_name[0:2].upper() if project_name else 'UG',
                'time': created_at,
                'content': f"You joined the group '{project_name}'. Start collaborating!",
                'unread': True,
                'actionUrl': f"mainpage.html#group-{group_id}",
                'createdAt': created_at,
            })
            
            if str(group.get('creatoruserid')) == user_id and len(group.get('members', [])) > 1:
                member_count = len(group.get('members', []))
                notifications_data.append({
                    'id': f'member-{group_id}',
                    'type': 'activity',
                    'name': 'New Member Alert',
                    'avatar': '👥',
                    'time': created_at,
                    'content': f"Your group '{project_name}' now has {member_count} member{'s' if member_count > 1 else ''}!",
                    'unread': True,
                    'actionUrl': f"mainpage.html#group-{group_id}",
                    'createdAt': created_at,
                })

        notifications_data.append({
            'id': 'system-qa-update',
            'type': 'activity',
            'name': 'Platform Update',
            'avatar': '🎉',
            'time': datetime.utcnow().isoformat(),
            'content': 'New Q&A features are now live! Try asking your first question.',
            'unread': True,
            'actionUrl': 'qa.html',
            'createdAt': datetime.utcnow().isoformat(),
        })

        print(f"✅ Generated {len(notifications_data)} notifications for user {user_id}")
        return jsonify({'success': True, 'notifications': notifications_data}), 200

    except Exception as e:
        print(f"❌ Get notifications error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== DISCUSSION ROUTES ====================

@app.route("/getdiscussions", methods=["GET"])
def get_discussions():
    try:
        user_id = str(request.args.get('userId'))
        
        if not user_id or user_id == 'None':
            return jsonify({"error": "User ID required"}), 400
        
        user_groups = list(groups_collection.find({'members': user_id}, {'_id': 1}))
        group_ids = [str(g['_id']) for g in user_groups]
        
        discussions = list(discussions_collection.find({
            'groupId': {'$in': group_ids}
        }).sort("lastMessageTime", -1).limit(50))

        discussions_list = []
        for d in discussions:
            discussions_list.append({
                "discussionId": str(d['_id']),
                "roomName": d.get("roomName"),
                "topic": d.get("topic", ""),
                "participants": d.get("participants", []),
                "lastMessage": d.get("lastMessage", ""),
                "lastMessageTime": d.get("lastMessageTime", datetime.utcnow()).isoformat(),
                "createdBy": d.get("createdBy"),
                "createdByName": d.get("createdByName", ""),
                "groupId": d.get("groupId"),
                "groupName": d.get("groupName", ""),
                "createdAt": d.get("createdAt", datetime.utcnow()).isoformat()
            })

        print(f"✅ Retrieved {len(discussions_list)} discussions for user {user_id}")
        return jsonify({"success": True, "discussions": discussions_list}), 200
    except Exception as e:
        print(f"❌ Get discussions error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/creatediscussion", methods=["POST"])
def create_discussion():
    try:
        data = request.get_json()
        room_name = data.get("roomName")
        group_id = data.get("groupId")
        user_id = str(data.get("userId"))
        
        if not all([room_name, group_id, user_id]):
            return jsonify({"error": "Room name, group ID, and user ID required"}), 400
        
        group = groups_collection.find_one({"_id": ObjectId(group_id)})
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        members = [str(m) for m in group.get("members", [])]
        if user_id not in members:
            return jsonify({"error": "You are not a member of this group"}), 403

        discussion = {
            "roomName": room_name,
            "topic": data.get("topic", ""),
            "createdBy": user_id,
            "createdByName": data.get("userName"),
            "participants": [user_id],
            "messages": [],
            "lastMessage": "",
            "lastMessageTime": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "groupId": group_id,
            "groupName": group.get("project_name", "")
        }

        result = discussions_collection.insert_one(discussion)
        print(f"✅ Discussion created: {discussion['roomName']} | ID: {result.inserted_id}")

        return jsonify({
            "success": True,
            "message": "Discussion created!",
            "discussionId": str(result.inserted_id)
        }), 200
    except Exception as e:
        print(f"❌ Create discussion error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/getmessages/<discussion_id>", methods=["GET"])
def get_messages(discussion_id):
    try:
        user_id = str(request.args.get('userId'))
        
        if not user_id or user_id == 'None':
            return jsonify({"error": "User ID required"}), 400
            
        discussion = discussions_collection.find_one({"_id": ObjectId(discussion_id)})

        if not discussion:
            return jsonify({"error": "Discussion not found"}), 404
        
        group_id = discussion.get("groupId")
        if group_id:
            group = groups_collection.find_one({"_id": ObjectId(group_id)})
            if not group:
                return jsonify({"error": "Group not found"}), 403
            
            members = [str(m) for m in group.get("members", [])]
            if user_id not in members:
                return jsonify({"error": "Access denied"}), 403

        return jsonify({
            "success": True,
            "messages": discussion.get("messages", []),
            "roomName": discussion.get("roomName"),
            "topic": discussion.get("topic", ""),
            "groupName": discussion.get("groupName", "")
        }), 200
    except Exception as e:
        print(f"❌ Get messages error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/sendmessage", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        discussion_id = data.get("discussionId")
        user_id = str(data.get("userId"))

        if not discussion_id or not user_id:
            return jsonify({"error": "Discussion ID and User ID required"}), 400
        
        discussion = discussions_collection.find_one({"_id": ObjectId(discussion_id)})
        if not discussion:
            return jsonify({"error": "Discussion not found"}), 404
        
        group_id = discussion.get("groupId")
        if group_id:
            group = groups_collection.find_one({"_id": ObjectId(group_id)})
            if not group:
                return jsonify({"error": "Group not found"}), 403
            
            members = [str(m) for m in group.get("members", [])]
            if user_id not in members:
                return jsonify({"error": "Access denied"}), 403

        message = {
            "messageId": str(ObjectId()),
            "userId": user_id,
            "userName": data.get("userName"),
            "userPhoto": data.get("userPhoto", ""),
            "content": data.get("content"),
            "timestamp": datetime.utcnow().isoformat()
        }

        result = discussions_collection.update_one(
            {"_id": ObjectId(discussion_id)},
            {
                "$push": {"messages": message},
                "$set": {
                    "lastMessage": data.get("content"),
                    "lastMessageTime": datetime.utcnow()
                },
                "$addToSet": {"participants": user_id}
            }
        )

        if result.matched_count > 0:
            print(f"✅ Message sent in discussion {discussion_id}")
            return jsonify({"success": True}), 200
        else:
            return jsonify({"error": "Discussion not found"}), 404
    except Exception as e:
        print(f"❌ Send message error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== CHAT ROUTES ====================

@app.route('/chat', methods=['POST'])
def save_chat():
    try:
        data = request.get_json()
        username = data.get('username')
        message = data.get('message')
        room = data.get('room', 'general')

        if not username or not message:
            return jsonify({"error": "Username and message required"}), 400

        chat = {
            "username": username,
            "message": message,
            "room": room,
            "timestamp": datetime.utcnow()
        }

        result = chats_collection.insert_one(chat)
        print(f"✅ Chat saved: {username} in {room}")

        return jsonify({
            "success": True,
            "chatId": str(result.inserted_id)
        }), 201
    except Exception as e:
        print(f"❌ Save chat error: {e}")
        return jsonify({"error": "Failed to save chat"}), 500

@app.route('/chats', methods=['GET'])
def get_chats():
    try:
        room = request.args.get('room', None)

        query = {"room": room} if room else {}
        chats = list(chats_collection.find(query).sort("timestamp", -1).limit(100))

        for c in chats:
            c['_id'] = str(c['_id'])
            c['timestamp'] = c['timestamp'].isoformat() if 'timestamp' in c else None

        print(f"✅ Retrieved {len(chats)} chats")
        return jsonify({"success": True, "chats": chats}), 200
    except Exception as e:
        print(f"❌ Get chats error: {e}")
        return jsonify({"error": "Failed to get chats"}), 500

# ==================== UTILITY ROUTES ====================

@app.route('/health', methods=['GET'])
def health():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        db_status = "connected"
    except:
        db_status = "disconnected"

    return jsonify({
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        "message": "✅ The Huddle API is working!",
        "databases": {
            "student_network_db": ["users", "groups", "posts", "questions", "discussions"],
            "chat_db": ["chats"]
        },
        "endpoints": {
            "auth": ["/signup [POST]", "/login [POST]"],
            "profile": ["/updateprofile [POST]", "/getuser/<user_id> [GET]"],
            "groups": ["/getavailablegroups [GET/POST]", "/creategroup [POST]", "/joingroup [POST]", "/leavegroup [POST]", "/getmygroups [GET]"],
            "posts": ["/createpost [POST]", "/getposts [GET]"],
            "qa": ["/createquestion [POST]", "/getquestions [GET]", "/addanswer [POST]", "/votequestion [POST]", "/acceptanswer [POST]", "/voteanswer [POST]"],
            "discussions": ["/getdiscussions [GET]", "/creatediscussion [POST]", "/getmessages/<id> [GET]", "/sendmessage [POST]"],
            "chat": ["/chat [POST]", "/chats [GET]"],
            "notifications": ["/getnotifications [GET]"],
            "utility": ["/health [GET]", "/test [GET]"]
        }
    }), 200

# ==================== START SERVER ====================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 THE HUDDLE - STUDENT NETWORKING PLATFORM")
    print("="*70)
    print(f"🌐 Server URL:    http://127.0.0.1:5000")
    print(f"🗄️  Database 1:    student_network_db")
    print(f"🗄️  Database 2:    chat_db")
    print(f"✅ Status:        Ready")
    print(f"🆕 Q&A Features:  Enhanced with better error handling")
    print("="*70)
    print("\n📄 Available Pages:")
    print("   • http://127.0.0.1:5000/login.html")
    print("   • http://127.0.0.1:5000/qa.html")
    print("\n🔧 Test Endpoints:")
    print("   • http://127.0.0.1:5000/test")
    print("   • http://127.0.0.1:5000/health")
    print("   • http://127.0.0.1:5000/getquestions")
    print("="*70 + "\n")

    app.run(host="127.0.0.1", port=5000, debug=True)