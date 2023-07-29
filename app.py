from flask import Flask, flash, render_template, request, redirect, make_response, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
import hashlib
import os


# Flask App configuration and setup of secret key
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = secrets.token_bytes(16)

# file upload control
ALLOWED_EXTENSIONS = set(['png', 'jpeg', 'jpg', 'mp4', 'mov',
                          'wmv','avi','mkv'])
def allowed_file(filename): # this function checks if file is allowed to be uploaded
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# is it a teacher checker
def is_teacher(uname):
    client = (UserData.query.filter_by(username=uname).first()).person
    if client == "Teacher":
        return True
    if client == "Student":
        return False


# Person Pic
person_pic = os.path.join('static', 'Images')
app.config['UPLOAD_FOLDER'] = person_pic


# database connectivity
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
app.config['SQLALCHEMY_BINDS'] = {'user_info': 'sqlite:///userinfo.db',
                                  'exam_sche': 'sqlite:///examsche.db',
                                  'student_marks': 'sqlite:///studentmarks.db'}
db = SQLAlchemy(app)


"""App Contains 4 databases for user/uploadedfiles/examschedules and exam results"""
class UserData(db.Model):
    # User Database
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    username = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(320), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    person = db.Column(db.String(10), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

class Upload(db.Model):
    # Uploaded Files Database
    __bind_key__ = "user_info"
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), nullable=False) # A single user can upload multiple so unique=False
    filename = db.Column(db.String(50))

class ExamSche(db.Model):
    # Exam Schedules Database
    __bind_key__ = "exam_sche"
    id = db.Column(db.Integer, primary_key=True)
    teacher_username = db.Column(db.String(20), nullable=False)
    exam_description = db.Column(db.String(50), nullable=False)
    date_scheduled = db.Column(db.String(20), nullable=False)


class ExamResults(db.Model):
    # Exam Results Database
    __bind_key__ = "student_marks"
    id = db.Column(db.Integer, primary_key=True)
    teacher_username = db.Column(db.String(20), nullable=False)
    student_username = db.Column(db.String(20), nullable=False)
    grade_comments = db.Column(db.String(100), nullable=False)



#Registration
@app.route('/register', methods=['POST', 'GET'])
def registration():
    if request.cookies.get("username") == None:
        if request.method == 'POST':
            if request.form.get('person') == 'teacher':
                person = "Teacher"
            else:
                person = "Student"

            fname = str.capitalize(request.form['fname'])
            lname = str.capitalize(request.form['lname'])
            if request.form.get('gender') == 'male':
                gender = "Male"
            else:
                gender = "Female"

            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            final_password = hashlib.md5(password.encode('utf-8')).hexdigest()
            dataset = UserData(first_name=fname,
                                last_name=lname,
                                username=username,
                                email=email,
                                password=final_password,
                                person=person,
                                gender=gender
                                )
            try:
                db.session.add(dataset)
                db.session.commit()
                flash('Account Creation Successful!!')
                return redirect(url_for('index'))
            except:
                return "Error In Code!!"

        return render_template('signup.html')
    flash("Your are already Logged In !")
    return redirect(url_for('index'))


# Login/ Welcome page
@app.route('/', methods=['POST', 'GET'])
def index():
    """Check for Cookie and redirect to the relavent page"""
    if request.cookies.get("username"):
       return redirect(f'/home/{request.cookies.get("username")}')
    
    if request.method == 'POST':
        uname = request.form['username']
        password = request.form['password']
        # encripting the password to save in database !
        encrpted_pass = hashlib.md5(password.encode('utf-8')).hexdigest()
        if UserData.query.filter_by(username=uname).count() == 1:
            user_in_db = UserData.query.filter_by(username=uname).first()
            if user_in_db.password == encrpted_pass:
                #Login - Success
                # Cookie Creation
                resp = make_response(redirect('/home/'+uname))
                resp.set_cookie('username', uname)
                return resp
            else:
                flash("Check the Password and Try Again...!")
                return redirect(url_for('index'))
        else:
            flash("No Such User! Try Again...")
            return redirect('/')
    return render_template('welcome.html')


# Page After Login
@app.route('/home/<uname>')
def home(uname):
    alluserdata = UserData.query.filter_by(username=uname).first()
    if request.cookies.get("username") == uname:
        #profile pic loader
        if alluserdata.person == 'Teacher':
            profilepic = url_for('static', filename='Images/Teacher.png')
            return render_template('home.html', data=alluserdata, profilepic=profilepic)
        elif alluserdata.person == 'Student':
            if alluserdata.gender == 'Male':
                profilepic = url_for('static', filename='Images/student-M.png')
                return render_template('home.html', data=alluserdata, profilepic=profilepic)
            else:
                profilepic = url_for('static', filename='Images/student-F.png')
                return render_template('home.html', data=alluserdata, profilepic=profilepic)
            
    flash("You Are Not Logged In...!")
    return redirect(url_for('index'))

# Logout /Deleting Cookie
@app.route('/logout')
def logout():
    resp = make_response(redirect('/'))
    resp.set_cookie('username', expires=0)
    return resp


""" Teacher configurations for the 3 duties """
# controls teacher file adding page and deletion
@app.route('/lecture', methods=['POST', 'GET'])
@app.route('/lecture/<int:lecturedelete>')
def lecture(lecturedelete=None):
    username = request.cookies.get("username")
    if username:
        if is_teacher(username):
            if lecturedelete != None: # Deleting lecture
                material = Upload.query.get(lecturedelete)
                os.remove(f"static/uploadfiles/{material.filename}")
                db.session.delete(material)
                db.session.commit()     

            # check if file is being upload
            if request.method == 'POST': 
                file = request.files['file']
                title = request.form['title']
                if allowed_file(file.filename):
                    filename = f"{title}.{file.filename.rsplit('.', 1)[1].lower()}"

                    # check whether same title duplicate file exists
                    if filename not in [name.filename for name in Upload.query.filter_by(user_name=request.cookies.get('username')).all()]:
                        
                        # saving the file
                        filedb = Upload(user_name=(request.cookies.get("username")),
                                        filename=filename)
                        try:
                                db.session.add(filedb)
                                db.session.commit() # save file info to database
                                file.save(f"static/uploadfiles/{filename}") # save file to server
                                flash("File Uploaded Successfully !")
                                return redirect(url_for('lecture'))
                        except:
                            flash("Error in Uploading !")
                            return redirect(url_for('lecture'))
                    
                    else:
                        flash("Choose Another Title !")
                        return redirect(url_for('lecture'))
                    
                else:
                    flash("Choose Other File-Type !")
                    return redirect(url_for('lecture'))
            
            # returning the user_name and videos/pics to be displayed
            lectures = Upload.query.filter_by(user_name=username).all() # list of lectures
            return render_template('lecture.html', lectures=lectures, no=len(lectures))
        else:
            return redirect(url_for("index"))
    else:
        flash("You are not Logged In !")
        return redirect(url_for('index'))


# Schedules/Delete exam
@app.route('/exams', methods=['POST', 'GET'])
@app.route('/exams/<int:scheduleid>')
def exams(scheduleid=None):
    username = request.cookies.get("username")

    if username:
        if is_teacher(username):
            if scheduleid != None:
                # Delete Schedule/Flash and Redirect
                material = ExamSche.query.get(scheduleid)
                db.session.delete(material)
                db.session.commit()

            if request.method == 'POST':
                # Add Schedule/Flash and Redirect
                date_scheduled = request.form.getlist('datetime')[0]
                exam_description = request.form['description']
                scheduledb = ExamSche(teacher_username=username,
                                    exam_description=exam_description,
                                    date_scheduled=date_scheduled)
                try:
                    db.session.add(scheduledb)
                    db.session.commit()
                    flash("Scheduled Successful !")
                    return redirect(url_for('exams'))
                except:
                    flash("Error in Scheduling !")
                    return redirect(url_for('exams'))

            schedules = ExamSche.query.filter_by(teacher_username=username).all() # list of schedules
            return render_template('examscheduler.html', schedules=schedules, no=len(schedules))
        else:
            return redirect(url_for('index'))
    
    else:
        flash("You are not Logged In !")
        return redirect(url_for('index'))


# send a student their marks
@app.route('/marks', methods=['POST', 'GET'])
def marks():
    uname = request.cookies.get("username")

    if uname:
        if is_teacher(uname):
            if request.method == 'POST':
                student_username = request.form['student_username']
                if UserData.query.filter_by(username=student_username).first():
                    if (UserData.query.filter_by(username=student_username).first()).person == 'Student':
                        # We check if username of student entered by teacher exists else we dont send the message to non existing user
                        grade_comments = request.form['grade_comments']
                        resultsdb = ExamResults(teacher_username=uname,
                                                student_username=student_username,
                                                grade_comments=grade_comments)
                        db.session.add(resultsdb)
                        db.session.commit()
                        flash(f"Marks Sent to {student_username} !")
                        return redirect(url_for('marks'))
                    else:
                        flash(f"Cannot Send Marks to Teachers !")
                        return redirect(url_for('marks'))

                else:
                    flash(f"No Student with Username : {student_username}")
                    return redirect(url_for('marks'))
                
            return render_template('marksender.html')
        else:
            return redirect(url_for('index'))
    flash("You are not Logged In !")
    return redirect(url_for('index'))


""" Student Configuations For the 3 functions"""
# Function Responsible for displaying videos/Images of lecturers
@app.route('/studymaterial')
@app.route('/studymaterial/<teacher>')
@app.route('/studymaterial/<teacher>/<int:content>')
def watch_lectures(teacher=None, content=None):
    username = request.cookies.get('username')
    if username:
        if not is_teacher(username):
            if teacher == None and content == None:
                # Display list Of Teachers 
                teacher_list = UserData.query.filter_by(person="Teacher").all()
                return render_template('studymaterial.html', teacher_list=teacher_list, no=len(teacher_list), process1=True)
            
            elif teacher != None and content == None:
                # Display list Of videos of the specific teacher
                content_list = Upload.query.filter_by(user_name=teacher).all()
                teachername = UserData.query.filter_by(username=teacher).first()
                return render_template('studymaterial.html',
                                        content_list=content_list,
                                        no=len(content_list),
                                        teacher=[teachername.first_name, teachername.last_name],
                                        process2=True)

            elif teacher != None and content != None:
                # Display the selected Video/Picture
                video_ext = ['mp4', 'mov','wmv','avi','mkv']
                image_ext = ['png', 'jpeg', 'jpg']
                # Confirming the Content is the tearcher's
                teacher_files = Upload.query.filter_by(user_name=teacher).all()
                teacher_files_id = [data.id for data in teacher_files]
                if content in teacher_files_id:
                    # Proceeding to Displaying
                    file = Upload.query.filter_by(id=content).first()
                    current_type = '.' in file.filename and file.filename.rsplit('.', 1)[1].lower()
                    file_title = '.' in file.filename and file.filename.rsplit('.', 1)[0].lower()
                    if current_type in video_ext:
                        # video type
                        video = url_for('static', filename=f'/uploadfiles/{file.filename}')
                        return render_template('studymaterial.html', video=video, process3=True, teacher=teacher, file_title=file_title, current_type=current_type)
                    elif current_type in image_ext:
                        # photo type
                        photo = url_for('static', filename=f'/uploadfiles/{file.filename}')
                        return render_template('studymaterial.html', photo=photo, process4=True, teacher=teacher, file_title=file_title)
                
                flash("Server Error !")
                return redirect(url_for('watch_lectures'))
        
            else:
                return redirect(url_for("index"))
        else:
            return redirect(url_for("index"))

    else:
        flash("You are Not logged In!")
        return redirect(url_for('index'))


# Function Responsible For showing a student the exams held by all lecturers
@app.route('/examdates')
def examdates():
    username = request.cookies.get('username')
    if username:
        if not is_teacher(username):
            exam_schedules = ExamSche.query.all()
            return render_template('readscheduler.html', exam_schedules=exam_schedules, no=len(exam_schedules))
        else:
            return redirect(url_for("index"))
    else:
        flash("You Are Not Logged In...!")
        return redirect(url_for('index'))


# Function Resposible for showing a student his list of marks
@app.route('/examarks')
@app.route('/examarks/delete/<int:markid>')
def read_exam_marks(markid=None):
    username = request.cookies.get('username')
    if username:
        if not is_teacher(username):
            if markid != None:
                # Removing the Exam marks
                material = ExamResults.query.get(markid)
                db.session.delete(material)
                db.session.commit()

            # Iter through db and show list of marks
            exam_results = ExamResults.query.filter_by(student_username=username).all()
            return render_template('readmarks.html', exam_results=exam_results, no=len(exam_results))
        else:
            return redirect(url_for("index"))
    else:
        flash("You Are Not Logged In...!")
        return redirect(url_for('index'))
        

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    #app.run(debug=True)
    app.run(host='0.0.0.0') 
    