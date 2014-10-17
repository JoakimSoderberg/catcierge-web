
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

var catcierge_update_data = function(data)
{
	if (!data)
		return;

	$.get("static/mustache/selected.html", function(html)
	{
		template = Handlebars.compile(html);

		$("#selected_event").html(template(data));
		$(".match").click(function()
		{
			$("#" + this.id + " > .steps").toggleClass("hidden");
		});
	});
}

var catcierge_events_updater = function(hostname, timeline, data)
{
	timeline.on("select", function(properties)
	{
		selected_item = data.get(properties.items[0]);
		console.log(properties, timeline, selected_item);
		catcierge_update_data(selected_item.catcierge);
	});

	ws = new WebSocket("ws://" + hostname + "/ws/live/events");

	ws.onopen = function(msg)
	{
		console.log("Connection successfully opened");
	};

	ws.onmessage = function(msg)
	{
		m = JSON.parse(msg.data);
		console.log("Got catcierge event", m, timeline);
		m.status_class = m.success ? "success" : "danger";
		m.success_str = m.success ? "OK" : "Fail";

		var catcierge_event =
		{
			id: m.id,
			start: m.time,
			content: m.description,
			catcierge: m,
			className: m.success ? "success" : "danger"
		};

		data.update(catcierge_event);
		//start = new Date(m.time).addDays(-1.1);
		start = new Date(m.time).addHours(-2);
		end = new Date(m.time).addHours(2);
		timeline.setWindow(start, end);
		timeline.select()
	};

	ws.onclose = function(msg)
	{
	};

	ws.error = function(err)
	{
		console.log(err);
	};
}
