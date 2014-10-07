
Date.prototype.addHours = function(h)
{
	this.setTime(this.getTime() + (h * 60 * 60 * 1000)); 
	return this;
}

Date.prototype.addDays = function(d)
{
	this.setTime(this.getTime() + (d * 60 * 60 * 24 * 1000));
	return this;
}

var catcierge_events_updater = function(hostname, timeline, data)
{
	ws = new WebSocket("ws://" + hostname + "/ws/live/events") 
	ws.onopen = function(msg)
	{
		console.log("Connection successfully opened");
	}

	ws.onmessage = function(msg)
	{
		m = JSON.parse(msg.data);
		console.log("bla", m, timeline);
		
		m.start = m.time;
		m.content = m.description;

		data.update(m);
		start = new Date(m.time).addDays(-1.1);
		end = new Date(m.time).addHours(2);
		timeline.setWindow(start, end);
	};

	ws.onclose = function(msg)
	{
	}

	ws.error = function(err)
	{
		console.log(err);
	}
}
