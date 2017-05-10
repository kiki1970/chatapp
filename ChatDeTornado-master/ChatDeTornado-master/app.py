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
        self.render('index.html', img_path=self.static_url('images/' + img_name))


class ChatHandler(tornado.websocket.WebSocketHandler):

    waiters = set()
    messages = []

    def open(self, *args, **kwargs):
        print("open")
        self.waiters.add(self)
        self.write_message({'messages': self.messages})

    def on_message(self, message):
        print("message")
        message = json.loads(message)
        self.messages.append(message)
        for waiter in self.waiters:
            if waiter == self:
                continue
            waiter.write_message({'img_path': message['img_path'], 'message': message['message']})

    def on_close(self):
        print("close")
        self.waiters.remove(self)


class Application(tornado.web.Application):

    def __init__(self):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        handlers = [
            url(r'/', IndexHandler, name='index'),
            url(r'/chat', ChatHandler, name='chat'),
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
