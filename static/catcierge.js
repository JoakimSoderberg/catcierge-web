
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
		console.log("Connection successfully opened");

		// Send the initial range.
		range = timeline.getWindow();
		ws.send(JSON.stringify(
			{
				start: range.start.toISOString(),
				end: range.end.toISOString() 
			}))

		// Update on range change.
		timeline.on("rangechanged", function(p)
		{
			ws.send(JSON.stringify(
				{
					start: p.start.toISOString(),
					end: p.end.toISOString() 
				}))
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
			start: m.timestamp,
			content: m.description,
			catcierge: m,
			className: m.status_class
		};

		data.update(catcierge_event);
		start = new Date(m.timestamp).addHours(-2);
		end = new Date(m.timestamp).addHours(2);
		timeline.setWindow(start, end);
		//timeline.select()
	};

	ws.onclose = function(msg)
	{
	};

	ws.error = function(err)
	{
		console.log(err);
	};
}
