from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import datetime
import random
import string

app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///canteen.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))

    surname = db.Column(db.String(50))
    name = db.Column(db.String(50))
    patronymic = db.Column(db.String(50))
    birthdate = db.Column(db.String(20))

    class_number = db.Column(db.Integer)
    class_letter = db.Column(db.String(2))

    parent_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    children = db.relationship("User",
                               backref=db.backref("parent", remote_side=[id]),
                               lazy=True)




class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, nullable=False)
    author_id = db.Column(db.Integer, nullable=False)
    text = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.String(30), nullable=False, default=lambda: datetime.datetime.now().isoformat(timespec="seconds"))


# МЕНЮ

menu = {
    "Понедельник": {"breakfast": ["Каша", "Омлет"], "lunch": ["Суп", "Пюре"]},
    "Вторник": {"breakfast": ["Блины", "Йогурт"], "lunch": ["Борщ", "Плов"]},
    "Среда": {"breakfast": ["Сырники", "Овсянка"], "lunch": ["Щи", "Макароны"]},
    "Четверг": {"breakfast": ["Оладьи", "Творог"], "lunch": ["Суп куриный", "Гречка"]},
    "Пятница": {"breakfast": ["Круассан", "Яичница"], "lunch": ["Пицца", "Овощной суп"]},
}

orders = []
reviews = []

#  РЕГИСТРАЦИЯ

@app.route("/register", methods=["POST"])
def register():
    data = request.json

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Пользователь уже существует"})

    user = User(
        email=data["email"],
        password=data["password"],
        role=data["role"],
        surname=data.get("surname"),
        name=data.get("name"),
        patronymic=data.get("patronymic"),
        birthdate=data.get("birthdate"),
        class_number=data.get("class_number"),
        class_letter=data.get("class_letter"),
        parent_id=data.get("parent_id")
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "ok"})


#  ВХОД

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"], password=data["password"]).first()

    if not user or user.role != data["role"]:
        return jsonify({"error": "Неверный логин или пароль"})

    return jsonify({"id": user.id, "role": user.role})


#  МЕНЮ

@app.route("/menu/<day>", methods=["GET"])
def get_menu_day(day):
    return jsonify(menu.get(day, {}))


@app.route("/menu/add", methods=["POST"])
def add_dish():
    data = request.json
    menu[data["day"]][data["meal"]].append(data["dish"])
    return jsonify({"message": "Добавлено"})


@app.route("/menu/delete", methods=["POST"])
def delete_dish():
    data = request.json
    if data["dish"] in menu[data["day"]][data["meal"]]:
        menu[data["day"]][data["meal"]].remove(data["dish"])
    return jsonify({"message": "Удалено"})


#  ЗАКАЗЫ

@app.route("/order", methods=["POST"])
def order():
    data = request.json or {}

    student_id = data.get("student_id") or data.get("user_id")
    ordered_by = data.get("user_id")

    item = {
        "id": len(orders),
        "student_id": student_id,
        "ordered_by": ordered_by,
        "dish": data.get("dish"),
        "meal": data.get("meal"),
        "time": datetime.date.today().isoformat(),
        "given": False
    }

    orders.append(item)
    return jsonify({"message": "ok", "id": item["id"]})


#  ОТЗЫВЫ

@app.route("/review", methods=["POST"])
def leave_review():
    data = request.json or {}

    student_id = data.get("student_id") or data.get("user_id")
    reviews.append({
        "student_id": student_id,
        "ordered_by": data.get("user_id"),
        "dish": data.get("dish"),
        "meal": data.get("meal"),
        "review": data.get("review")
    })
    return jsonify({"message": "ok"})



#  ЗАМЕТКИ

@app.route("/note", methods=["POST"])
def add_note():
    data = request.json or {}
    student_id = data.get("student_id")
    author_id = data.get("author_id")
    text = (data.get("text") or "").strip()

    if not student_id or not author_id or not text:
        return jsonify({"error": "student_id, author_id и text обязательны"})

    note = Note(student_id=int(student_id), author_id=int(author_id), text=text)
    db.session.add(note)
    db.session.commit()
    return jsonify({"message": "ok", "id": note.id})


@app.route("/notes/<int:student_id>", methods=["GET"])
def get_notes(student_id):
    notes = Note.query.filter_by(student_id=student_id).order_by(Note.id.desc()).all()
    return jsonify([{
        "id": n.id,
        "student_id": n.student_id,
        "author_id": n.author_id,
        "text": n.text,
        "created_at": n.created_at
    } for n in notes])


@app.route("/note/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    n = Note.query.get(note_id)
    if not n:
        return jsonify({"error": "Не найдено"})
    db.session.delete(n)
    db.session.commit()
    return jsonify({"message": "Удалено"})


#  КАБИНЕТ ПОВАРА

@app.route("/cook/orders_today", methods=["GET"])
def cook_orders_today():
    today = datetime.date.today().isoformat()
    todays = [o for o in orders if o["time"] == today]
    return jsonify(todays)


@app.route("/cook/mark_given", methods=["POST"])
def cook_mark_given():
    data = request.json or {}
    oid = data.get("id")
    if oid is None:
        return jsonify({"error": "no id"})

    if isinstance(oid, int) and 0 <= oid < len(orders):
        orders[oid]["given"] = True
        return jsonify({"message": "Отмечено"})

    return jsonify({"error": "Не найден"})


@app.route("/cook/reviews", methods=["GET"])
def cook_reviews():
    return jsonify(reviews)



@app.route("/cook/notes_today", methods=["GET"])
def cook_notes_today():
    today = datetime.date.today().isoformat()
    student_ids = sorted({o.get("student_id") for o in orders if o.get("time") == today and o.get("student_id") is not None})
    if not student_ids:
        return jsonify([])

    notes = Note.query.filter(Note.student_id.in_(student_ids)).order_by(Note.created_at.desc()).all()

    users = User.query.filter(User.id.in_(set(student_ids + [n.author_id for n in notes]))).all()
    user_by_id = {u.id: u for u in users}

    out = []
    for n in notes:
        stu = user_by_id.get(n.student_id)
        au = user_by_id.get(n.author_id)
        out.append({
            "id": n.id,
            "student_id": n.student_id,
            "student_email": (stu.email if stu else None),
            "author_id": n.author_id,
            "author_email": (au.email if au else None),
            "text": n.text,
            "created_at": n.created_at,
        })
    return jsonify(out)


#  КАБИНЕТ РОДИТЕЛЯ

@app.route("/parent/link_child", methods=["POST"])
def parent_link_child():
    data = request.json or {}
    parent_id = data.get("parent_id")
    child_email = (data.get("child_email") or "").strip()

    if not parent_id or not child_email:
        return jsonify({"error": "parent_id и child_email обязательны"}), 400

    parent = User.query.get(parent_id)
    if not parent or parent.role != "parent":
        return jsonify({"error": "Родитель не найден"}), 404

    child = User.query.filter_by(email=child_email).first()
    if not child or child.role != "student":
        return jsonify({"error": "Ученик с такой почтой не найден"}), 404

    child.parent_id = parent_id
    db.session.commit()
    return jsonify({"message": "ok", "child_id": child.id})


@app.route("/parent/link_child_full", methods=["POST"])
def parent_link_child_full():
    data = request.json or {}
    parent_id = data.get("parent_id")

    email = (data.get("email") or "").strip()
    surname = (data.get("surname") or "").strip()
    name = (data.get("name") or "").strip()
    patronymic = (data.get("patronymic") or "").strip()
    birthdate = (data.get("birthdate") or "").strip()
    class_number = data.get("class_number")
    class_letter = (data.get("class_letter") or "").strip()

    if not parent_id or not email or not surname or not name or not birthdate or not class_number or not class_letter:
        return jsonify({"error": "Обязательны: parent_id, email, фамилия, имя, дата рождения, класс (номер и буква)"}), 400

    parent = User.query.get(parent_id)
    if not parent or parent.role != "parent":
        return jsonify({"error": "Родитель не найден"}), 404

    child = User.query.filter_by(email=email).first()

    if child:
        if child.role != "student":
            return jsonify({"error": "Пользователь с такой почтой существует, но не является учеником"}), 400

        if child.parent_id and int(child.parent_id) != int(parent_id):
            return jsonify({"error": "Ученик уже привязан к другому родителю"}), 400

        def norm(x):
            return (x or "").strip().lower()

        mismatch = []

        def compare_or_fill(attr_name, new_value, label):
            current = getattr(child, attr_name)
            if norm(current) == "":

                setattr(child, attr_name, new_value)
                return
            if norm(current) != norm(new_value):
                mismatch.append(label)

        compare_or_fill("surname", surname, "фамилия")
        compare_or_fill("name", name, "имя")
        compare_or_fill("patronymic", patronymic, "отчество")
        compare_or_fill("birthdate", birthdate, "дата рождения")

        if child.class_number is None:
            try:
                child.class_number = int(class_number)
            except Exception:
                mismatch.append("класс (номер)")
        else:
            if str(child.class_number) != str(class_number):
                mismatch.append("класс (номер)")

        if norm(child.class_letter) == "":
            child.class_letter = class_letter
        else:
            if norm(child.class_letter) != norm(class_letter):
                mismatch.append("класс (буква)")

        if mismatch:
            return jsonify({"error": "Данные ученика не совпадают: " + ", ".join(mismatch)}), 400
        child.parent_id = parent_id
        db.session.commit()
        return jsonify({"message": "linked", "child_id": child.id})

    alphabet = string.ascii_letters + string.digits
    temp_password = "".join(random.choice(alphabet) for _ in range(10))

    child = User(
        email=email,
        password=temp_password,
        role="student",
        surname=surname,
        name=name,
        patronymic=patronymic,
        birthdate=birthdate,
        class_number=int(class_number),
        class_letter=class_letter,
        parent_id=parent_id
    )
    db.session.add(child)
    db.session.commit()

    return jsonify({"message": "created", "child_id": child.id, "temp_password": temp_password})

@app.route("/parent/children/<int:parent_id>", methods=["GET"])
def parent_children(parent_id):
    kids = User.query.filter_by(parent_id=parent_id, role="student").all()
    return jsonify([{
        "id": k.id,
        "surname": k.surname,
        "name": k.name,
        "patronymic": k.patronymic,
        "class_number": k.class_number,
        "class_letter": k.class_letter,
        "email": k.email
    } for k in kids])


@app.route("/parent/orders/<int:student_id>", methods=["GET"])
def parent_student_orders(student_id):
    arr = [o for o in orders if o.get("student_id") == student_id]
    return jsonify(arr)


@app.route("/parent/reviews/<int:student_id>", methods=["GET"])
def parent_student_reviews(student_id):
    arr = [r for r in reviews if r.get("student_id") == student_id]
    return jsonify(arr)


@app.route("/admin/users", methods=["GET"])
def admin_get_users():
    users = User.query.all()
    arr = []
    for u in users:
        arr.append({
            "id": u.id,
            "email": u.email,
            "role": u.role,
            "surname": u.surname,
            "name": u.name,
            "patronymic": u.patronymic,
            "class_number": u.class_number,
            "class_letter": u.class_letter,
            "parent_id": u.parent_id
        })
    return jsonify(arr)


@app.route("/admin/users/delete", methods=["POST"])
def admin_delete_user():
    data = request.json
    user = User.query.get(data["id"])
    if not user:
        return jsonify({"error": "Не найден"})
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Удалено"})


@app.route("/admin/users/role", methods=["POST"])
def admin_change_role():
    data = request.json
    user = User.query.get(data["id"])
    if not user:
        return jsonify({"error": "Не найден"})
    user.role = data["role"]
    db.session.commit()
    return jsonify({"message": "Обновлено"})


@app.route("/admin/stats", methods=["GET"])
def get_stats():
    stats = {
        "total_orders": len(orders),
        "popular_dishes": {},
        "reviews": reviews
    }
    for o in orders:
        dish = o["dish"]
        stats["popular_dishes"][dish] = stats["popular_dishes"].get(dish, 0) + 1
    return jsonify(stats)


@app.route("/admin/clear", methods=["POST"])
def clear_stats():
    orders.clear()
    reviews.clear()
    return jsonify({"message": "Очищено"})

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
