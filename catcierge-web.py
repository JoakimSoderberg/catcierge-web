import tornado.ioloop
from tornado.ioloop import IOLoop
import tornado.web
import tornado.websocket
import tornado.template
import tornado.httpserver
import os
import json
from datetime import timedelta, datetime

from tornado.options import define, options, parse_command_line

define("port", default=8888, help="Run server on the given port", type=int)

clients = dict()

ioloop = tornado.ioloop.IOLoop.instance()

class IndexHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self):
		self.render('index.html', hostname=self.request.host)


class WebSocketHandler(tornado.websocket.WebSocketHandler):

	def send_event(self):
		self.write_message(json.dumps({
			'id': self.event_id,
			'content': 'item %d' % self.event_id,
			'start': str(datetime.today() + timedelta(days=self.event_id)),
		}))

		self.event_id += 1

		ioloop.add_timeout(timedelta(seconds=5), self.send_event)

	def open(self):
		self.event_id = 7
		self.id = self.request.headers['Sec-Websocket-Key']
		clients[self.id] = {'id': self.id, 'object': self}
		
		print("CONNECTED %s with id: %s" % (self.request.remote_ip, id))
		ioloop.add_timeout(timedelta(seconds=5), self.send_event)

	def on_message(self, message):
		print("%s: %s" % (self.id, message))

	def on_close(self):
		if self.id in clients:
			del clients[self.id]


class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r'/', IndexHandler),
			(r'/ws', WebSocketHandler),
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
