#!/usr/bin/env python

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
import arrow
logger = logging.getLogger('catcierge-web')

from tornado.options import define, options, parse_command_line

define("http_port", default=8888, help="Run web server on the given port", type=int)
define("zmq_port", default=5556, help="The port the catcierge ZMQ publisher is listening on", type=int)
define("zmq_host", default="localhost", help="The host the catcierge ZMQ publisher is listening on")
define("zmq_transport", default="tcp", help="The ZMQ transport to use to connect to the catcierge publisher. Possible options: inproc, ipc, tcp, tpic, multicast")
define("image_path", default=".", help="The path to the image root directory")
define("rethinkdb_host", default="localhost", help="The rethinkdb hostname")
define("rethinkdb_port", default=28015, help="The rethinkdb port")
define("rethinkdb_database", default="catcierge", help="Name of the rethinkdb database to use")
define("event_topic", default="event", help="The ZMQ topic for a catcierge event")
define("docker", default=False, type=bool, help="If we're running inside of docker. Reads RethinkDB settings from dockers linked environment variables")
define("docker_db_alias", default="db", help="The name of the Docker RethinkDB alias to get connection settings from")

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

	def initialize(self):
		logger.debug("Initializing Websocket Handler")
		self.zmq_connect()
		self.rethinkdb_connect()

	def __del__(self):
		print("Deleting websocket handler")
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
									db=options.rethinkdb_database)
			except r.RqlDriverError as ex:
				logger.error("Failed to connect to Rethinkdb: %s" % ex)

	def rethinkdb_insert(self, req_msg):
		"""
		Inserts an event into RethinkDB.
		"""

		# Add timestamps in a format RethinkDB understands.
		del req_msg["live"]
		req_msg["timestamp"] = r.iso8601(req_msg["start"])
		req_msg["timestamp_end"] = r.iso8601(req_msg["end"])
		r.db("catcierge").table("events").insert(req_msg).run(self.rdb)

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

		return j

	def zmq_on_recv(self, msg):
		"""
		Receives ZMQ subscription messages from Catcierge and
		passes them on to the Websocket connection.
		"""
		req_topic = msg[0]
		req_msg = self.simplify_json(msg[1])
		req_msg["live"] = True  # This is so that the JavaScript knows if we should zoom in on this.
		req_msg_json = json.dumps(req_msg, indent=4)

		#logger.info("ZMQ recv %s: %s" % (req_topic, req_msg_json))

		if (req_topic == options.event_topic):

			# Send to browser clients.
			logger.info("Sending to websocket clients...")
			self.send_catcierge_event(req_msg_json)

			# Save in database.
			logger.info("Sending to database...")
			self.rethinkdb_insert(req_msg)
		else:
			logger.info("DOING NOTHING, not listening to topic %s" % req_topic)

	def open(self):
		"""
		Websocket connection opened.
		"""
		self.id = self.request.headers['Sec-Websocket-Key']
		clients[self.id] = {'id': self.id, 'object': self}

		logger.info("Websocket Client CONNECTED %s with id: %s" % (self.request.remote_ip, self.id))

	def on_message(self, message):
		"""
		Websocket on message.
		"""
		range = json.loads(message)
		logger.info("WS %s: %s" % (self.id, json.dumps(range, indent=4)))

		# Return different queries depending on the length of the time range.
		timediff = arrow.get(range["end"]) - arrow.get(range["start"])

		if timediff.days >= 1:
			logger.info("Time span more than 1 day (%s - %s) %s" % (range["start"], range["end"], timediff))

			global_start = arrow.get(range["start"])
			global_end = arrow.get(range["end"])

			events = []

			# Based on the timeline time range shown, split it up into days
			# and get the number of events for each day.
			for day in arrow.Arrow.span_range("day", global_start, global_end):
				start = day[0].isoformat()
				end = day[1].isoformat()

				# For each day do a query and count.
				# TODO: Make all this into one query?
				# http://www.rethinkdb.com/docs/cookbook/python/#implementing-pagination
				num_events = r.db("catcierge").table("events").filter(
						r.row["timestamp"].during(
							r.iso8601(start),
							r.iso8601(end))
					).count().run(self.rdb)

				if num_events == 0:
					continue

				event = {
					"type": "day",
					"start": start,
					"end": end,
					"count": num_events
				}

				events.append(event)

			for event in events:
				self.send_catcierge_event(event)
		# TODO: Add month aggregate...
		else:
			# Query RethinkDB for events in the given time range.
			events = r.db("catcierge").table("events").filter(
					r.row["timestamp"].during(
						r.iso8601(range["start"]),
						r.iso8601(range["end"]))
				).run(self.rdb)

			for doc in events:
				# Delete these stupid date things we have the same info in start/end
				# so that we can turn the document into JSON.
				del doc["timestamp"]
				del doc["timestamp_end"]
				jdoc = json.dumps(doc, indent=4)
				self.send_catcierge_event(jdoc)

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

		if (options.docker):
			# Translate the environment variables Docker creates
			# when containers are linked to a Python dictionary.
			from docker_links import parse_links
			links = parse_links(os.environ)

			logger.info("Docker mode (links):")
			logger.info("\n%s" % json.dumps(links, indent=4))

			# The user can specify another alias to look for.
			if options.docker_db_alias not in links:
				raise Exception('No Docker alias named "%s" found. Available:\n%s' \
					% (options.docker_db_alias, "\n".join(links.keys())))

			db = links[options.docker_db_alias]

			options.rethinkdb_host = db["hostname"]

		logger.info("Options:\n%s" % "\n".join(map(lambda x: \
			"%25s: %s" % (x[0], x[1]), options.items())))

		http_server = tornado.httpserver.HTTPServer(Application())
		http_server.listen(options.http_port)
		tornado.ioloop.IOLoop.instance().start()
	except Exception as ex:
		logger.error("Error: %s" % ex)
		exit(-1)

if __name__ == "__main__":
	main()
