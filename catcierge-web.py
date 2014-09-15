import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import tornado.httpserver
import os

from tornado.options import define, options, parse_command_line

define("port", default=8888, help="Run server on the given port", type=int)

clients = dict()

class IndexHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self):
		self.render('index.html')

class WebSocketHandler(tornado.websocket.WebSocketHandler):
	def open(self, *args):
		self.id = self.get_argument('Id')
		self.stream.set_nodelay(True)
		clients[self.id] = {'id': self.id, 'object': self}

	def on_message(self, message):
		print "Client %s received a message : %s" % (self.id, message)

	def on_close(self):
		if self.id in clients:
			del clients[self.id]

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r'/', IndexHandler),
			(r'/', WebSocketHandler),
		]

		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), 'templates'),
			static_path=os.path.join(os.path.dirname(__file__), 'static'),
			debug=True,
			)

		tornado.web.Application.__init__(self, handlers, **settings)

def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
	main()
