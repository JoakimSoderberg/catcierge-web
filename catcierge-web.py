import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.template
import tornado.httpserver
from tornado.web import StaticFileHandler
import os
import json
import zmq
from zmq.eventloop import ioloop, zmqstream
ioloop.install()
from datetime import timedelta, datetime
import signal
import sys
import logging
import rethinkdb as r
logger = logging.getLogger('catcierge-web')

from tornado.options import define, options, parse_command_line

define("http_port", default=8888, help="Run web server on the given port", type=int)
define("zmq_port", default=5556, help="The port the catciege ZMQ publisher is listening on", type=int)
define("zmq_host", default="localhost", help="The host the catcierge ZMQ publisher is listening on")
define("zmq_transport", default="tcp", help="The ZMQ transport to use to connect to the catcierge publisher. Possible options: inproc, ipc, tcp, tpic, multicast")
define("image_path", default=".", help="The path to the image root directory")
define("rethinkdb_host", default="localhost", help="The rethinkdb hostname")
define("rethinkdb_port", default=28015, help="The rethinkdb port")
define("rethinkdb_database", default="catcierge", help="Name of the rethinkdb database to use")

clients = dict()
	
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

		if hasattr(self, "rdb"):
			self.rdb.close()

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

			connect_str = "%s://%s:%d" % (options.zmq_transport, options.zmq_host, options.zmq_port)

			logger.info("Connecting ZMQ socket: %s" % connect_str)
			self.zmq_sock.connect(connect_str)

	def rethinkdb_connect(self):
		"""
		Connect to the RethinkDB server.
		"""
		if not hasattr(self, "rdb"):
			try:
				self.rdb = r.connect(host=options.rethinkdb_host,
									port=options.rethinkdb_port,
									db="catcierge")
			except RqlDriverError as ex:
				logger.error("Failed to connect to Rethinkdb: %s" % ex)

	def simplify_json(self, msg):
		"""
		Gets rid of unused parts of the JSON that's there
		because the catciege template system sucks.
		"""
		j = json.loads(msg)

		if "matches" in j:
			j["matches"] = j["matches"][:j["match_group_count"]]

			for m in j["matches"]:
				if "steps" in m:
					m["steps"] = m["steps"][:m["step_count"]]

		return json.dumps(j, indent=4)

	def zmq_on_recv(self, msg):
		"""
		Receives ZMQ subscription messages from Catcierge and
		passes them on to the Websocket connection.
		"""
		req_id = msg[0]
		req_msg = self.simplify_json(msg[1])

		# TODO: Enable setting IDs we listen for via command line...
		if (req_id == "event"): # "match_group_done"):
			logger.info("ZMQ recv %s: %s" % (req_id, req_msg))

			self.send_catcierge_event(req_msg)
		else:
			logger.info("ZMQ recv %s: %s", req_id, req_msg)
			logger.info("DOING NOTHING")

	def open(self):
		"""
		Websocket connection opened.
		"""
		self.id = self.request.headers['Sec-Websocket-Key']
		clients[self.id] = {'id': self.id, 'object': self}

		# Connect the ZMQ sub socket and Rethinkdb server on the first client.
		self.zmq_connect()
		self.rethinkdb_connect()

		logger.info("Websocket Client CONNECTED %s with id: %s" % (self.request.remote_ip, self.id))

	def on_message(self, message):
		"""
		Websocket on message.
		"""
		range = json.loads(message)
		logger.info("WS %s: %s" % (self.id, json.dumps(range, indent=4)))

		# TODO: Fix this query.
		"""
		events = r.db("catcierge").table("events").filter(
			lambda event: event.during(
							r.iso8601(range["start"]),
							r.iso8601(range["end"]))
			).run(self.rdb)

		for doc in events:
			print("%r " % doc)
		"""

	def on_close(self):
		"""
		Websocket on close.
		"""
		if self.id in clients:
			del clients[self.id]

class Application(tornado.web.Application):
	def __init__(self):
		print options.image_path
		handlers = [
			(r'/', IndexHandler),
			(r'/ws/live/events', LiveEventsWebSocketHandler),
			(r'/static/(.*)', StaticFileHandler, { 'path': os.path.join(os.path.dirname(__file__), 'static') }),
			(r'/images/(.*)', StaticFileHandler, { 'path': options.image_path })
		]

		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), 'templates'),
			debug=True,
			)

		tornado.web.Application.__init__(self, handlers, **settings)


def main():
	try:
		tornado.options.parse_command_line()

		http_server = tornado.httpserver.HTTPServer(Application())
		http_server.listen(options.http_port)
		tornado.ioloop.IOLoop.instance().start()
	except Exception as ex:
		print("Error: %s" % ex)
		exit(-1)

if __name__ == "__main__":
	main()
