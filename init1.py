#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect, send_from_directory
import pymysql.cursors
import hashlib 
import time

#Initialize the app from Flask
app = Flask(__name__, static_url_path = "/static", static_folder = "static")

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='PriCoSha',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
	return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
	return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
	return render_template('register.html')

#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password']
	hashedpw = hashlib.md5(password).hexdigest()
	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM Person WHERE username = %s and password = %s'
	cursor.execute(query, (username, hashedpw))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	cursor.close()
	error = None
	if(data):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		return redirect(url_for('home'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password']
	fname = request.form['fname']
	lname = request.form['lname']
	hashedpw = hashlib.md5(password).hexdigest()
	#cursor used to send queries
	cursor = conn.cursor()
	#executes query
	query = 'SELECT * FROM Person WHERE username = %s'
	cursor.execute(query, (username))
	#stores the results in a variable
	data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
	error = None
	if(data):
		#If the previous query returns data, then user exists
		error = "This username has been taken"
		return render_template('register.html', error = error)
	else:
		ins = 'INSERT INTO Person VALUES(%s, %s, %s, %s)'
		cursor.execute(ins, (username, hashedpw, fname, lname))
		conn.commit()
		cursor.close()
		return render_template('index.html')

@app.route('/home')
def home():
	username = session['username']
	cursor = conn.cursor();
	query = 'SELECT DISTINCT(id), username as poster, timest, file_path, content_name FROM Content NATURAL JOIN Person WHERE id in (SELECT id FROM Share WHERE group_name in (SELECT group_name FROM Member WHERE username = %s) AND username in (SELECT username_creator FROM Member WHERE username = %s)) OR public = True OR username = %s ORDER BY timest DESC' 
	query2 = 'SELECT first_name FROM Person WHERE username = %s'
	getgr = 'SELECT group_name FROM FriendGroup WHERE username = %s'
	cursor.execute(query, (username, username, username))
	data = cursor.fetchall()
	cursor.execute(query2, (username))
	fname = cursor.fetchone()
	cursor.execute(getgr, (username))
	groups = cursor.fetchall() 
	print("groups at home to post to:", groups)
	print("list of content", data)
	cursor.close()
	return render_template('home.html', username=username, posts=data, fname = fname, lgr = groups)

		
@app.route('/post', methods=['GET', 'POST'])
def post():
	username = session['username']
	content_name = request.form['caption']
	fpath = "/static/" + request.form['path'] 
	pBool = int(request.form['public']) 
	share2 = request.form.getlist('groups')

	print('this is groups that I selected to share with:', share2)

	tstmp = str(time.strftime('%Y-%m-%d %H:%M:%S'))

	newpost = 'INSERT INTO Content VALUES (0, %s, %s, %s, %s, %s)'
	sharepost = 'INSERT INTO Share Values (%s, %s, %s)'
	cursor = conn.cursor()
	cursor.execute(newpost, (username, tstmp, fpath, content_name, pBool))
	cid = cursor.lastrowid

	print("Content ID is:", cid)
	print "\n \n No groups:	", len(share2), "\n\n"
	if len(share2) >0: 
		for group in share2:
			print("THis is a group:", group)
			cursor.execute(sharepost,(cid, group, username))

	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

# @app.route('/getTags', methods = ['GET', 'POST'])
# def getTags():
# 	username = session["username"]
# 	return redirect(url_for('managetags')) 


@app.route('/managetags', methods = ['GET', 'POST'])
def managetags():
	username = session['username']
	cid = request.form['contentid']
	print '\n This is the content id', cid
	q1 = 'SELECT first_name, last_name FROM Person WHERE username in (SELECT username_taggee FROM Tag WHERE id = %s AND status = 1)'
	q2 = 'SELECT * FROM Tag WHERE id = %s AND username_taggee = %s AND status = 0'
	cursor = conn.cursor();
	cursor.execute(q1, (cid)) 
	apptag = cursor.fetchall()
	cursor.execute(q2, (cid, username))
	unapp = cursor.fetchall() 
	cursor.close() 
	print apptag, unapp, cid
	return render_template('managetags.html', approved = apptag, unapproved = unapp, id = cid)

@app.route('/authTag', methods = ['GET', 'POST'])
def authTag():
	username = session['username']
	action = request.form['approved']
	cid = request.form['contentid']
	usertagger = request.form['tagger']
	print(cid, "CID in authTag", action)
	cursor = conn.cursor(); 
	if action == "1":
		aquery = "UPDATE Tag SET status = 1 WHERE id = %s AND username_tagger = %s AND username_taggee = %s" 
		cursor.execute(aquery, (cid, usertagger,username))
		conn.commit()
	elif action == "-1":
		dquery = "DELETE FROM Tag WHERE id = %s AND username_tagger = %s AND username_taggee = %s" 
		cursor.execute(dquery, (cid, usertagger, username))	
	cursor.close()	
	return redirect(url_for('home'))

def validate(memlist, public, taggee):
	print '\n Inside validate function \n', memlist, public
	inlist = False
	ispub = False
	for member in memlist:
		print member['username']
		if member['username'] == taggee:
			inlist = True
			break
	if public['public'] == 1:
		ispub = True
	return inlist or ispub  

@app.route('/reqTag', methods = ['GET', 'POST']) 
def reqTag(): 
	username = session['username']
	tagthisuser = request.form['tagthisusername']
	cid = request.form['contentid']
	cid = cid.strip('/')
	print('This is the content ID in req Tag', cid)
	cursor = conn.cursor()
	tstmp = str(time.strftime('%Y-%m-%d %H:%M:%S'))

	pquery = 'SELECT public FROM Content WHERE id = %s'
	cursor.execute(pquery, (cid))
	public = cursor.fetchone()
	mquery = 'SELECT username FROM Member WHERE username_creator in (SELECT username FROM Share WHERE id = %s) AND group_name in (SELECT group_name FROM Share WHERE id = %s)'
	cursor.execute(mquery,(cid, cid))
	member = cursor.fetchall() 
	print(public, 'member', member)
	error = None
	if username == tagthisuser:
		query = 'INSERT INTO Tag VALUES(%s, %s, %s, %s, 1)'
		cursor.execute(query,(cid, username, tagthisuser, tstmp))
		conn.commit() 
		cursor.close()
		return redirect(url_for('home'))
	elif validate(member, public, tagthisuser):
		query = 'INSERT INTO Tag VALUES(%s, %s, %s, %s, 0)'
		cursor.execute(query,(cid, username, tagthisuser, tstmp))
		conn.commit() 
		cursor.close()
		return redirect(url_for('home'))
	else: 
		error = "This person does not have access to the content."
		return render_template('managetags.html', error = error)		

@app.route('/friends') 
def friends():
	username = session['username']
	getgr = "SELECT group_name FROM FriendGroup WHERE username = %s"
	cursor = conn.cursor()
	cursor.execute(getgr, (username))
	groups = cursor.fetchall()
	cursor.close()
	return render_template('test.html', fgroups = groups)

@app.route('/addfriend', methods = ['GET', 'POST'])
def addfriend():
	username = session['username']
	group = request.form['fgroup']
	fname = request.form['fname']
	lname = request.form['lname']

	cursor = conn.cursor()

	addfr = 'INSERT INTO Member VALUES(%s, %s, %s)'
	check = 'SELECT COUNT(*) FROM Person WHERE first_name = %s AND last_name = %s'
	dupcheck = 'SELECT COUNT(*) FROM Person NATURAL JOIN Member WHERE first_name = %s and last_name = %s and group_name=%s and username_creator = %s'
	getusrnm = 'SELECT username FROM Person WHERE first_name=%s and last_name = %s'
	getgr = "SELECT group_name FROM FriendGroup WHERE username = %s"

	cursor.execute(getgr, (username))
	groups = cursor.fetchall()

	cursor.execute(check,(fname, lname))
	collision = cursor.fetchone()

	cursor.execute(dupcheck, (fname, lname, group, username))
	dup = cursor.fetchone()

	print 'dup', dup, '\ncollision', collision, '\ngroups', groups

	error = None
	if collision["COUNT(*)"] > 1: 
		cursor.close()
		error = "There is more than one person by the name of"
		return render_template('test.html', error = error, fname = fname, lname = lname, fgroups = groups)
	elif dup["COUNT(*)"] > 0: 
		cursor.close()
		error = "Specified person is already in the selected group: "
		return render_template('test.html', error = error, fname = fname, lname = lname, fgroups = groups)
	elif collision["COUNT(*)"] < 1:
		cursor.close()
		error = "The specified person does not exist: "
		return render_template('test.html', error = error, fname = fname, lname = lname, fgroups = groups)		
	else:
		cursor.execute(getusrnm, (fname, lname))
		usrnm = cursor.fetchone()["username"]
		cursor.execute(addfr, (usrnm, group, username))
		conn.commit()
		cursor.close()
		msg = "Friend was successfully added to group: "
		return render_template('test.html', error = error, fname = fname, lname = lname, msg = msg, fgroups = groups) 

@app.route('/comments', methods = ['GET', 'POST'])
def comments():
	username = session['username']
	cid = request.form['contentid']
	cname = request.form['contentname']
	getcom = 'SELECT username, comment_text, timest FROM Comment WHERE id = %s ORDER BY timest ASC'
	cursor = conn.cursor()
	cursor.execute(getcom, (cid))
	lstcom = cursor.fetchall()
	cursor.close()
	return render_template('comments.html', lcom = lstcom, name = cname, id = cid)

@app.route('/addcom', methods = ['GET', 'POST'])
def addcomment(): 
	username = session['username']
	cid = request.form['contentid']
	text = request.form['comment']
	getname = 'SELECT content_name FROM Content WHERE id = %s'
	ts = str(time.strftime('%Y-%m-%d %H:%M:%S'))
	addcom = 'INSERT INTO Comment VALUES(%s, %s, %s, %s)'
	cursor = conn.cursor()
	cursor.execute(addcom,(cid, username, ts, text))
	conn.commit()
	cursor.execute(getname, (cid))
	name = cursor.fetchone()
	cursor.close() 
	return redirect(url_for('home'))


@app.route('/logout')
def logout():
	session.pop('username')
	return redirect('/')
		

app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True --> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
