from app import app
import mysql.connector
from flask import render_template, Flask, redirect, request, session, abort, url_for
import calendar as cld
import datetime
import re
from flask_wtf.csrf import CSRFProtect

# ------------------------------------------------------------------------------
connection = mysql.connector.connect(host="host", user="user", password="password",database="database")
cur = connection.cursor()

def get_dates():
    week_now = datetime.datetime.today().weekday()
    month_now = datetime.datetime.today().month
    day_now = datetime.datetime.today().day
    day_total = cld.monthrange(datetime.datetime.today().year,month_now)[1]
    return month_now, week_now, day_now, day_total

def user_dict(results):
    users = []
    for i in range(0, len(results)):
        users.append({'user_id':results[i][0], 'firstname':results[i][1], 'lastname':results[i][2], 'address':results[i][3], 'postcode':results[i][4],
                    'phone_no':results[i][5], 'email':results[i][6]})
    return users

def event_dict(activity):
    event = []
    for i in range(0, len(activity)):
        event.append({'act_id':activity[i][0], 'name':activity[i][1], 'description':activity[i][2], 'time':activity[i][3], 'day':activity[i][4],
                    'month':activity[i][5], 'year':activity[i][6], 'user_id':activity[i][7]})
    return event

# ------------------------------------------------------------------------------
@app.route('/')

# ------------------------------------------------------------------------------
@app.route('/index')
def index():
    if session.get('logged_in') == True:
        week_iter = []
        month_now, week_now, day_now, day_total = get_dates()

        start = day_now - week_now
        if start < 1:
            start = 1
        end = start + 7
        if end > day_total:
            end = day_total
        for i in range(start, end):
            week_iter.append({'iter':i})

        sql_statement = "SELECT activity_id, name, description, time, day, month, year, user_id FROM activity_tbl WHERE month = (%s) AND day BETWEEN (%s) AND (%s) AND user_id = (%s) ORDER BY day ASC"
        sql_values = (month_now, start, end, session.get('user_id'))
        cur.execute(sql_statement, sql_values)
        week_act = cur.fetchall()

        event = event_dict(week_act)

        return render_template('index.html', week_iter=week_iter, start=start, end=end, event=event)
    else:
        return render_template('login.html')

# ------------------------------------------------------------------------------
@app.route('/search', methods = ['GET', 'POST'])
def search():
    if session.get('logged_in') == True:
        if request.method == 'POST':
            if request.form['field'] == 'name':
                sql_statement = "SELECT activity_id, name, description, time, day, month, year, user_id FROM activity_tbl WHERE name = (%s) AND user_id = (%s)"
                sql_statement_else = "SELECT activity_id, name, description, time, day, month, year, user_id FROM activity_tbl WHERE (%s) = (%s) AND user_id = (%s)"
                sql_values = (request.form['search'],session.get('user_id'))
                sql_values_else = (request.form['field'],request.form['search'],session.get('user_id'))
                cur.execute(sql_statement, sql_values)
            else:
                cur.execute(sql_statement_else, sql_values_else)

            results = cur.fetchall()
            event = event_dict(results)

            return render_template('search.html', search = True, event = event)
        elif request.method == 'GET':
            return render_template('search.html', search = False)
    else:
        return render_template('login.html')

# ------------------------------------------------------------------------------
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':

        regex_username = re.compile(r"^(?=.*[A-Z])$|^(?=.*[a-z])$|^(?=.*[0-9]).*$", flags = re.M)
        regex_password = re.compile(r"^(?=.*[A-Z])$|^(?=.*[a-z])$|^(?=.*[0-9]).*$", flags = re.M)

        obj = regex_username.match(request.form['username'])
        if not obj:
            return render_template('login.html', error = True)
        obj = regex_username.match(request.form['password'])
        if not obj:
            return render_template('login.html', error = True)

        sql_statement = "SELECT username, password, user_id FROM account_tbl WHERE username = (%s) AND password = (PASSWORD(%s))"
        sql_values = (request.form['username'], request.form['password'])
        cur.execute(sql_statement, sql_values)
        results = cur.fetchall()
        if len(results) != 0:
            session['user_id'] = results[0][2]
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error = True)
    elif request.method == 'GET':
        pass

# ------------------------------------------------------------------------------
@app.route('/logout')
def logout():
    if session.get('logged_in') == True:
        session['logged_in'] = False
        session.pop('username', None)
        return redirect('/index')
    else:
        return render_template('login.html')

# ------------------------------------------------------------------------------
@app.route('/create_account', methods = ['GET', 'POST'])
def create_account():
    if request.method == 'POST':

        # check for duplicate in database
        sql_statement = "SELECT username FROM account_tbl WHERE username = (%s)"
        sql_values = (request.form['username'],)
        cur.execute(sql_statement, sql_values)
        username_check = cur.fetchall()
        if len(username_check) != 0:
            return render_template('create_account.html', error = 'username')

        # check passwords match
        if request.form['password'] != request.form['repeat_password']:
            return render_template('create_account.html', error = 'password')

        # check for duplicates
        sql_statement = "SELECT email from user_tbl WHERE email = (%s)"
        sql_values = (request.form['email'],)
        cur.execute(sql_statement, sql_values)
        email_check = cur.fetchall()
        if len(email_check) != 0:
            return render_template('create_account.html', error = 'email')

        # input validation
        regex_name = re.compile(r"^[a-zA-Z]+-[a-zA-Z]+$|^[a-zA-Z]+$|^[a-zA-Z]+'[a-zA-Z]+$", flags = re.M)
        regex_username = re.compile(r"^(?=.*[A-Z])$|^(?=.*[a-z])$|^(?=.*[0-9]).*$", flags = re.M)
        regex_password = re.compile(r"^(?=.*[A-Z])$|^(?=.*[a-z])$|^(?=.*[0-9]).*$", flags = re.M)
        regex_address = re.compile(r"^[0-9]+ [A-Z][a-z]+$|^[0-9]+ [A-Z][a-z]+ [A-Z][a-z]+$", flags = re.M)
        regex_postcode = re.compile(r"^[A-Z][A-Z][0-9][0-9] [0-9][A-Z][A-Z]$", flags = re.M)
        regex_phone_no = re.compile(r"^[0-9]{11}$", flags = re.M)
        regex_email = re.compile(r"^[a-zA-Z-_.]+@[a-zA-Z]+\.[a-zA-Z]+\.[a-zA-Z]+$|^[a-zA-Z-_.]+@[a-zA-Z]+\.[a-zA-Z]+$", flags = re.M)

        obj = regex_name.match(request.form['firstname'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_name.match(request.form['lastname'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_username.match(request.form['username'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_username.match(request.form['password'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_address.match(request.form['address'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_postcode.match(request.form['postcode'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_phone_no.match(request.form['phone_no'])
        if not obj:
            return render_template('create_account.html', error = 'format')
        obj = regex_email.match(request.form['email'])
        if not obj:
            return render_template('create_account.html', error = 'format')


        sql_statement = "INSERT INTO user_tbl (user_id, firstname, lastname, address, postcode, phone_no, email) VALUES (uuid(), %s, %s, %s, %s, %s, %s)"
        sql_values = (request.form['firstname'], request.form['lastname'], request.form['address'], request.form['postcode'], request.form['phone_no'], request.form['email'])
        cur.execute(sql_statement, sql_values)
        connection.commit()

        sql_statement = "SELECT user_id FROM user_tbl WHERE email = %s"
        sql_values = (request.form['email'],)
        cur.execute(sql_statement, sql_values)
        user_id_add = cur.fetchall()
        user_id_add_str = str(user_id_add[0])
        punctuation = '''('),'''
        remove_punct = ""
        for i in user_id_add_str:
            if i not in punctuation:
                remove_punct = remove_punct + i

        sql_statement = "INSERT INTO account_tbl (username, password, user_id, admin) VALUES (%s, PASSWORD(%s), %s, %s)"
        sql_values = (request.form['username'], request.form['password'], remove_punct, 'false')
        cur.execute(sql_statement, sql_values)
        connection.commit()

        return render_template('login.html')
    elif request.method == 'GET':
        return render_template('create_account.html')

# ------------------------------------------------------------------------------
@app.route('/calendar', methods = ['GET', 'POST'])
def calendar():
    if request.method == 'POST':
        if session.get('logged_in') == True:
            pass
        else:
            return render_template('login.html')
    elif request.method == 'GET':
        if session.get('logged_in') == True:
            month_now, week_now, day_now, day_total = get_dates()

            sql_statement = "SELECT activity_id, name, description, time, day, month, year, user_id FROM activity_tbl WHERE month = (%s) AND user_id = (%s)"
            sql_values = (month_now, session['user_id'])
            cur.execute(sql_statement, sql_values)
            act = cur.fetchall()
            event = event_dict(act)

            day_list = []
            for i in range(0, day_total):
                day_list.append(i)

            return render_template('calendar.html', event = event, day_list = day_list)
        else:
            return render_template('login.html')

# ------------------------------------------------------------------------------
@app.route('/add_event', methods = ['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        if session.get('logged_in') == True:
            regex_event_name = re.compile(r"^[a-zA-Z0-9 ]+$", flags = re.M)
            regex_event_description = re.compile(r"^[a-zA-Z0-9 ]+$", flags = re.M)
            regex_event_time = re.compile(r"^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", flags = re.M)

            obj = regex_event_name.match(request.form['event_name'])
            if not obj:
                return render_template('add_event.html', error = 'format')
            obj = regex_event_description.match(request.form['description'])
            if not obj:
                return render_template('add_event.html', error = 'format')
            obj = regex_event_time.match(request.form['event_time'])
            if not obj:
                return render_template('add_event.html', error = 'format')

            sql_statement = "INSERT INTO activity_tbl (activity_id, time, user_id, description, day, month, year, name) VALUES (uuid(), %s, %s, %s, %s, %s, %s, %s)"
            sql_values = (request.form['event_time'], session['user_id'], request.form['description'], request.form['day'], request.form['month'], request.form['year'], request.form['event_name'])
            cur.execute(sql_statement, sql_values)
            connection.commit()
            return redirect(url_for('calendar', method="GET"))
        else:
            return render_template('login.html')

    elif request.method == 'GET':
        if session.get('logged_in') == True:
            return render_template('add_event.html')
        else:
            return render_template('login.html')

# ------------------------------------------------------------------------------
@app.route('/edit_event', methods = ['GET', 'POST'])
def edit_event():
    if request.method == 'GET':
        if session.get('logged_in') == True:
            id = request.args.get('id')
            if id == '':
                return render_template('calendar.html')

            sql_statement = "SELECT activity_id, name, description, time, day, month, year, user_id FROM activity_tbl WHERE activity_id = (%s)"
            sql_values = (id,)
            cur.execute(sql_statement, sql_values)

            results = cur.fetchall()
            event = event_dict(results)

            return render_template('edit_event.html', id=results[0][0], name=results[0][1], desc=results[0][2], time=results[0][3])
        else:
            return render_template('login.html')

@app.route('/update_event', methods = ['POST'])
def update_event():
    if request.method == 'POST':
        if session.get('logged_in') == True:

            regex_event_name = re.compile(r"^[a-zA-Z0-9 ]+$", flags = re.M)
            regex_event_description = re.compile(r"^[a-zA-Z0-9 ]+$", flags = re.M)
            regex_event_time = re.compile(r"^[0-2][0-9]:[0-5][0-9]:[0-5][0-9]$", flags = re.M)

            obj = regex_event_name.match(request.form['event_name'])
            if not obj:
                return render_template('calendar.html')
            obj = regex_event_description.match(request.form['description'])
            if not obj:
                return render_template('calendar.html')
            obj = regex_event_time.match(request.form['event_time'])
            if not obj:
                return render_template('calendar.html')

            sql_statement = "UPDATE activity_tbl SET day = (%s), month = (%s), year = (%s), name = (%s), time = (%s), description = (%s) WHERE activity_id = (%s)"
            sql_values = (request.form['day'], request.form['month'], request.form['year'], request.form['event_name'], request.form['event_time'], request.form['description'], request.form['event_id'])
            cur.execute(sql_statement, sql_values)
            connection.commit()
            return redirect(url_for('calendar', method="GET"))
        else:
            return render_template('login.html')

# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app.debug = True
    app.run(debug = True)
