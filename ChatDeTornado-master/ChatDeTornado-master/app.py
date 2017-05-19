import os
import json
import random
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.web import url
import tornado.escape
import tornado.options
from tornado.options import define, options
import sqlite3
import logging

define("port", default=5000, type=int)
define("username", default="user")
define("password", default="pass")

myUser=""

      
class BaseHandler(tornado.web.RequestHandler):

    cookie_username = "username"

    def get_current_user(self):
        username = self.get_secure_cookie(self.cookie_username)
        logging.debug('BaseHandler - username: %s' % username)
        if not username: return None
        return tornado.escape.utf8(username)

    def set_current_user(self, username):
        self.set_secure_cookie(self.cookie_username, tornado.escape.utf8(username))

    def clear_current_user(self):
        self.clear_cookie(self.cookie_username)


class GroupHandler(BaseHandler):
    def get(self):
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()
        cursor.execute("select username from users")
        result = cursor.fetchall()
        userlist = []
        for user in result:
            userlist.append(user[0])
        self.render("newgroup.html",users = userlist)
        cursor.close()
        connector.close()

    def post(self):
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()

        groupname = self.get_argument("groupname")
        users = self.get_arguments("users")
        usernames = ','.join(users)
        insert_sql = 'insert into groups (groupname, users) values(?,?)'
        values = (groupname, usernames)
        cursor.execute(insert_sql,values)
        for user in users:
            print (user)
            cursor.execute("select affiliation_group from users where username = '"+user+"'")
            result = cursor.fetchall()
            if result[0][0] == None:
                update_sql = "update users set affiliation_group = '"+ groupname +"' WHERE username = '"+user+"'"
            else:
                update_sql = "update users set affiliation_group = '" + result[0][0] +","+ groupname +"' WHERE username = '"+user+"'"
            cursor.execute(update_sql)
        connector.commit()
        self.redirect("/?"+groupname)
        cursor.close()
        connector.close()


class AuthLoginHandler(BaseHandler):

    def get(self):
        self.render("login.html")

    def post(self):
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()

        logging.debug("xsrf_cookie:" + self.get_argument("_xsrf", None))

        self.check_xsrf_cookie()


        username = self.get_argument("username")
        password = self.get_argument("password")

        cursor.execute("select * from users where username='"+username+"'")
        result = cursor.fetchall()
        print(result)
        if len(result) == 0:
            cursor.close()
            connector.close()
            self.write_error(403)
        else:
            for row in result:
                password_true = row[1]
            logging.debug('AuthLoginHandler:post %s %s' % (username, password))

            if password == password_true:
                cursor.close()
                connector.close()
 
                global myUser
                myUser = username
                #print("myUser:")
                #print(myUser)

                self.set_current_user(username)
                self.redirect("/")
            else:
                cursor.close()
                connector.close()
                self.write_error(403)


class AuthLogoutHandler(BaseHandler):
    
    def get(self):
        self.clear_current_user()
        self.redirect('/')


class IndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, *args, **kwargs):
        #face_pics = ['cat.gif', 'fere.gif', 'lion.gif']
        #img_name = random.choice(face_pics)
        #print("myUser:")
        #print(myUser)
        if myUser != "":
            img_name = myUser + '.gif'
        else:
            img_name = 'lion.gif'
        #print("img_name")
        #print(img_name)
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()
        cursor.execute("select groupname from groups")
        result = cursor.fetchall()
        grouplist = []
        if len(result) != 0:
            for groupname in result:
                grouplist.append(groupname[0])
        cursor.execute("select username from users")
        result = cursor.fetchall()
        userlist = []
        for user in result:
            if user[0] != myUser:
                userlist.append(user[0])
        self.render('index.html', img_path=self.static_url('images/' + img_name),groups = grouplist,users = userlist)
        cursor.close()
        connector.close()

    def post(self):
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()

        groupname = self.get_argument("groupname")
        users = self.get_arguments("users")
        users.append(myUser)
        usernames = ','.join(users)
        insert_sql = 'insert into groups (groupname, users) values(?,?)'
        values = (groupname, usernames)
        cursor.execute(insert_sql,values)
        for user in users:
            print (user)
            cursor.execute("select affiliation_group from users where username = '"+user+"'")
            result = cursor.fetchall()
            if result[0][0] == None:
                update_sql = "update users set affiliation_group = '"+ groupname +"' WHERE username = '"+user+"'"
            else:
                update_sql = "update users set affiliation_group = '" + result[0][0] +","+ groupname +"' WHERE username = '"+user+"'"
            cursor.execute(update_sql)
        connector.commit()
        cursor.close()
        connector.close()

class ChatHandler(tornado.websocket.WebSocketHandler):

    groups = ['all']
    waiters = [[]]
    messages = [[]]
    group_members = [[]]
    groupnumber = 0
    print('a')
    def open(self, *args, **kwargs):
        self.groupnumber = 0
        nowgroup = self.get_argument("group")
        #print('a', flush=True)
        #print(self.get_argument("group"))
        match = False
        for group in self.groups:
            if group == nowgroup:
                match = True
                break
            self.groupnumber += 1
        if not match :
            self.groups.append(nowgroup)
            self.waiters.append([])
            self.messages.append([])
        #print >> kwargs
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()
        self.waiters[self.groupnumber].append(self)
        cursor.execute("select message,username from messages where groupname='"+ nowgroup +"'")
        result = cursor.fetchall()
        if len(result) != 0:
            for message in result:
                if(message[1] == myUser):
                    message = json.loads(message[0])
                    self.write_message({'img_path': message['img_path'], 'message': message['message'], 'mymessage': True})
                else:
                    message = json.loads(message[0])
                    self.write_message({'img_path': message['img_path'], 'message': message['message'], 'mymessage': False})
        cursor.close()
        connector.close()
        print(self.groupnumber)

    def on_message(self, message):
        print(self.groupnumber)
        print(self.messages[self.groupnumber])
        message = json.loads(message)
        #self.messages[self.groupnumber].append(message)
        connector = sqlite3.connect("userdata.db")
        cursor = connector.cursor()
        insert_sql = 'insert into messages (groupname, message, username) values(?,?,?)'
        print ("insert into messages (groupname, message, username) values('"+ self.groups[self.groupnumber] +"','"+ json.dumps(message, ensure_ascii=False) +"','" + myUser +"')")
        values = (self.groups[self.groupnumber], json.dumps(message, ensure_ascii=False), myUser)
        cursor.execute(insert_sql,values)
        connector.commit()
        cursor.close()
        connector.close()
        print(self.waiters)
        for waiter in self.waiters[self.groupnumber]:
            if waiter == self:
                continue
            waiter.write_message({'img_path': message['img_path'], 'message': message['message'], 'mymessage': False})

    def on_close(self):
        print(self.groupnumber)
        self.waiters[self.groupnumber].remove(self)


class Application(tornado.web.Application):

    def __init__(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        handlers = [
            url(r'/', IndexHandler, name='index'),
            url(r'/chat', ChatHandler),
            url(r'/newgroup', GroupHandler),
            url(r'/auth/login', AuthLoginHandler),
            url(r'/auth/logout', AuthLogoutHandler),
        ]
        settings = dict(
            cookie_secret='gaofjawpoer940r34823842398429afadfi4iias',
            template_path=os.path.join(BASE_DIR, 'templates'),
            static_path=os.path.join(BASE_DIR, 'static'),
            login_url="/auth/login",
            xsrf_cookies=True,
            autoescape="xhtml_escape",
            debug=True,
            )
        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == '__main__':
    tornado.options.parse_config_file(os.path.join(os.path.dirname(__file__), 'server.conf'))
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    logging.debug('run on port %d in %s mode' % (options.port, options.logging))
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
