import tornado.ioloop
#from tornado.ioloop import IOLoop
import tornado.web
import tornado.websocket
import tornado.template
import tornado.httpserver
import os
import json
import zmq
from zmq.eventloop import ioloop, zmqstream
ioloop.install()
from datetime import timedelta, datetime
import signal
import sys
import logging
logger = logging.getLogger('catcierge-web')

from tornado.options import define, options, parse_command_line

define("http_port", default=8888, help="Run web server on the given port", type=int)
define("zmq_port", default=5556, help="The port the catciege ZMQ publisher is listening on", type=int)
define("zmq_host", default="localhost", help="")

clients = dict()

#ioloop = tornado.ioloop.IOLoop.instance()
sigint_handlers = []

def sighandler(signum, frame):
	logger.info("Program: Received SIGINT, shutting down...")

	for handler in sigint_handlers:
		handler(signum, frame)

	sys.exit(0)

# Trap keyboard interrupts.
signal.signal(signal.SIGINT, sighandler)
signal.signal(signal.SIGTERM, sighandler)

class IndexHandler(tornado.web.RequestHandler):
	"""
	Web server.
	"""
	@tornado.web.asynchronous
	def get(self):
		self.render('index.html', hostname=self.request.host)


class LiveEventsWebSocketHandler(tornado.websocket.WebSocketHandler):
	"""
	Websocket handler for pushing live events.
	"""

	def __del__(self):
		if hasattr(self, "zmq_stream"):
			self.zmq_stream.close()

	def send_event(self):
		self.write_message(json.dumps(
		{
			'id': self.event_id,
			'content': 'item %d' % self.event_id,
			'start': str(datetime.today() + timedelta(days=self.event_id)),
		}))

		self.event_id += 1

		ioloop.add_timeout(timedelta(seconds=5), self.send_event)

	def send_catcierge_event(self, msg):
		"""
		Sends a catcierge event over the websocket.
		"""
		self.write_message(msg)

	def zmq_connect(self):
		"""
		Connect to ZMQ publisher.
		"""
		if not hasattr(self, "zmq_ctx"):
			self.zmq_ctx = zmq.Context()
			self.zmq_sock = self.zmq_ctx.socket(zmq.SUB)
			self.zmq_stream = zmqstream.ZMQStream(self.zmq_sock, tornado.ioloop.IOLoop.instance())
			self.zmq_stream.on_recv(self.zmq_on_recv)
			self.zmq_sock.setsockopt(zmq.SUBSCRIBE, b"")

			connect_str = "tcp://%s:%s" % ("192.168.0.204", "5556")

			logger.info("Connecting ZMQ socket: %s" % connect_str)
			self.zmq_sock.connect(connect_str)

	def zmq_on_recv(self, msg):
		"""
		Receives ZMQ subscription messages from Catcierge and
		passes them on to the Websocket connection.
		"""
		req_id = msg[0]
		req_msg = msg[1]

		logger.info("ZMQ recv %s: %s" % (req_id, req_msg))

		self.send_catcierge_event(req_msg)

	def open(self):
		"""
		Websocket connection opened.
		"""
		#self.event_id = 7

		self.id = self.request.headers['Sec-Websocket-Key']
		clients[self.id] = {'id': self.id, 'object': self}

		# Connect the ZMQ sub socket on the first client.
		self.zmq_connect()

		logger.info("Websocket Client CONNECTED %s with id: %s" % (self.request.remote_ip, self.id))
		#ioloop.add_timeout(timedelta(seconds=5), self.send_event)

	def on_message(self, message):
		"""
		Websocket on message.
		"""
		logger.debug("WS %s: %s" % (self.id, message))

	def on_close(self):
		"""
		Websocket on close.
		"""
		if self.id in clients:
			del clients[self.id]

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r'/', IndexHandler),
			(r'/ws/live/events', LiveEventsWebSocketHandler),
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
