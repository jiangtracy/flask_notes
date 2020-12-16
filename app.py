from flask import Flask, render_template, redirect, session, flash
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Note
from forms import RegisterForm, LoginForm, NoteForm

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgres:///flask_notes"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "abc123"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)
db.create_all()

toolbar = DebugToolbarExtension(app)


@app.route('/')
def show_homepage():
    """ Redirect to register page """
    return redirect('/register')


@app.route('/register', methods=["GET", "POST"])
def handle_registration():
    """ Show the registration form or handles the registration
        of a user, if the email is taken, take them back to the
        registration form
        - If someone is already logged in, redirect to their page
    """

    username = session.get("user_id")

    if username:
        return redirect(f"/users/{username}")

    form = RegisterForm()

    email = form.email.data

    # If there is a user with this email already
    if User.query.filter_by(email=email).first():
        form.email.errors = ["This email is already being used"]
        return render_template('register.html', form=form)

    if form.validate_on_submit():
        name = form.username.data
        pwd = form.password.data
        f_name = form.first_name.data
        l_name = form.last_name.data

        user = User.register(name, pwd, email, f_name, l_name)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.username

        # on successful login, redirect to user detail page
        return redirect(f"/users/{user.username}")
    else:
        return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def handle_login():
    """ Shows the login form or handles logging the user in """

    username = session.get("user_id")

    if username:
        return redirect(f"/users/{username}")

    form = LoginForm()

    if form.validate_on_submit():
        name = form.username.data
        pwd = form.password.data

        # authenticate will return a user or False
        user = User.authenticate(name, pwd)

        if user:
            session["user_id"] = user.username  # keep logged in
            return redirect(f"/users/{user.username}")

        else:
            form.username.errors = ["Bad name/password"]

    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    """ Logs out the user from the webpage """

    if session.pop("user_id", None):
        flash("You have been logged out!")
    else:
        flash("No user logged in!")

    return redirect("/")


@app.route("/users/<username>")
def show_user_detail(username):
    """ Show user details if user is logged in.
        Otherwise flash message and redirect to homepage.
    """

    # Guard
    if session.get('user_id') != username:
        flash("You are not authorized to view!")
        return redirect("/")

    user = User.query.get(username)
    return render_template('user_detail.html', user=user)


@app.route('/users/<username>/delete', methods=['POST'])
def delete_user(username):
    """ Delete the user by deleting all their posts first
        Only allow this when the user is logged in
    """

    if session.get('user_id') != username:
        flash("You are not authorized to delete this user!")
        return redirect("/")

    user = User.query.get(username)

    # Delete all the user's notes
    Note.query.filter_by(owner=username).delete()
    db.session.commit() # Not necessary

    db.session.delete(user)
    db.session.commit()

    flash("User has been deleted")

    # Clear any user info from the session
    session.pop("user_id", None)

    return redirect("/")


@app.route("/users/<username>/notes/add", methods=["GET", "POST"])
def handle_add_notes(username):
    """ Display form to add notes for the logged in user.
        Add new note and redirect to user detail.
    """

    if session.get('user_id') != username:
        flash("You are not authorized to add notes to this user!")
        return redirect('/')

    form = NoteForm()

    if form.validate_on_submit():

        new_note = Note()
        form.populate_obj(new_note)
        new_note.owner = username

        db.session.add(new_note)
        db.session.commit()

        flash("Note has been added")

        return redirect(f"/users/{username}")
    else:
        return render_template("add_notes.html", form=form)


@app.route("/notes/<int:note_id>/update", methods=["GET", "POST"])
def handle_update_note(note_id):
    """ Display form to update notes for the logged in user.
        Update note and redirect to user detail.
    """

    note = Note.query.get_or_404(note_id)

    if session.get('user_id') != note.owner:
        flash("You are not authorized to update this note!")
        return redirect('/')

    form = NoteForm(obj=note)

    if form.validate_on_submit():

        form.populate_obj(note)
        db.session.commit()

        flash("Note has been updated!")

        return redirect(f"/users/{note.owner}")
    else:
        return render_template("update_notes.html", form=form)


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    """ Handles delete note only if it belongs to the logged
        in user
     """

    note = Note.query.get_or_404(note_id)

    if session.get('user_id') != note.owner:
        flash('You are not authorized to delete this note!')
        return redirect('/')

    db.session.delete(note)
    db.session.commit()

    flash("Note deleted!")

    return redirect(f"/users/{note.owner}")
