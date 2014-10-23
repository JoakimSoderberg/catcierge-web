
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
		
		// TODO: Add an explicit button that is pressed to show the steps, 
		// if the steps div is shown, fetch the images via ajax, otherwise don't.
		$(".match").click(function()
		{
			$("#" + this.id + " > .steps").toggleClass("hidden");
		});
	});
}

var catcierge_events_updater = function(hostname, timeline, data)
{
	wsurl = "ws://" + hostname + "/ws/live/events"
	console.log("Connect to websocket" + "ws://" + hostname + "/ws/live/events")
	ws = new WebSocket(wsurl);

	timeline.on("select", function(properties)
	{
		selected_item = data.get(properties.items[0]);
		console.log(properties, timeline, selected_item);
		catcierge_update_data(selected_item.catcierge);
	});

	ws.onopen = function(msg)
	{
		console.log("Websocket Connection successfully opened");

		send_time_range = function(range)
		{
			// TODO: Only send this new range if the old one was smaller.
			ws.send(JSON.stringify(
			{
				start: range.start.toISOString(),
				end: range.end.toISOString()
			}))
		};

		// Get events for the initial time range.
		range = timeline.getWindow();
		send_time_range(range);

		// BUGFIX! The below is a fix in visjs for the "rangechanged"
		// event firing as if it was "rangchange" when zooming.
		// Solve this by using a timer to figure out when a zoom
		// has stopped and keep that as a flag.
		//
		// If we don't do this we would keep spamming the webserver
		// with requests for events in the zoom range we are.
		var is_still_zooming = true;
		on_zooming = function()
		{
			clearTimeout($.data(this, 'timer'));
			$.data(this, 'timer', setTimeout(function()
			{
				is_still_zooming = false;
			}, 250));
		};

		timeline.on("mousewheel", on_zooming);
		timeline.on("DOMMouseScroll", on_zooming);
		timeline.on("pinch", on_zooming);

		// Update events on range change.
		timeline.on("rangechanged", function(p)
		{
			if (!is_still_zooming)
			{
				send_time_range(p);
				is_still_zooming = true;
			}
		});
	};

	ws.onmessage = function(msg)
	{
		m = JSON.parse(msg.data);
		console.log("Got catcierge event", m, timeline);
		m.status_class = m.match_group_success ? "alert-success" : "alert-danger";
		m.success_str = m.match_group_success ? "OK" : "Fail";

		for (var i = 0; i < m.matches.length; i++)
		{
			m.matches[i].status_class = m.matches[i].success ? "alert-success" : "alert-danger";
		}

		var catcierge_event =
		{
			id: m.id,
			start: m.start,
			content: m.description,
			catcierge: m,
			className: m.status_class
		};

		data.update(catcierge_event);

		if (m.live)
		{
			start = new Date(m.start).addHours(-2);
			end = new Date(m.start).addHours(2);

			timeline.setWindow(start, end);
		}
	};

	ws.onclose = function(msg)
	{
		timeline.off("rangechanged");
		timeline.off("mousewheel");
		timeline.off("DOMMouseScroll");
		timeline.off("pinch");
	};

	ws.error = function(err)
	{
		console.log(err);
	};
}
