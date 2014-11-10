
$(function()
{
	var data = new vis.DataSet({});
	var container = document.getElementById('visualization');

	$.when(
		$.get("static/mustache/item.html"),
		$.get("static/mustache/day.html"))
		.then(function(item_html, day_html)
		{
			var templates =
			{
				item: Handlebars.compile(item_html[0]),
				day: Handlebars.compile(day_html[0])
			};

			var options =
			{
				maxHeight: "250px",
				minHeight: "250px",
				clickToUse: false,
				width: "95%",
				stack: false,
				template: function(item)
				{
					var template = templates[item.template];
					return template(item);
				}
			};

			var timeline = new vis.Timeline(container, data, options);

			catcierge_events_updater(location.host, timeline, data);
		});
});

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

var catcierge_update_selected_data = function(data)
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

		if (selected_item)
		catcierge_update_selected_data(selected_item.catcierge);
	});

	ws.onopen = function(msg)
	{
		console.log("Websocket Connection successfully opened");

		send_time_range = function(range)
		{
			// TODO: Save the unix time epoch below in an interval tree.
			// https://github.com/shinout/interval-tree
			// http://en.wikipedia.org/wiki/Interval_tree
			// https://github.com/toberndo/interval-query
			// var itree = new IntervalTree(300); 
			// itree.add([22, 56,  'foo']);
			// itree.add([44, 199, 'bar']);
			// 
			// First query the tree with the range.
			// If any other range is overlapping, remove those ranges from the interval
			// tree and merge with them.
			// http://stackoverflow.com/questions/14545695/merge-ranges-in-intervals
			//
			// One simple implementation is to simply use an array for the ranges
			// and when inserting we merge right away.
			//
			// There is one interval tree for each aggregation level.
			// - events (< 1 day)
			// - days (> 1 day)
			// - weeks (> 1 week)
			// - months (> 3 months)
			// - years (> 1 year)
			console.log("Sending ", range.start.getTime(), range.end.getTime());



			ws.send(JSON.stringify(
			{
				start: range.start.toISOString(),
				end: range.end.toISOString(),
				exclude: timeline.getVisibleItems()
			}));
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
		//
		// Incoming Websocket message.
		//
		m = JSON.parse(msg.data);
		console.log("Got catcierge event", m, timeline);

		if (m.type == "day")
		{
			// Day aggregate event.

			// TODO: Find and hide all events except day ones!

			var catcierge_event =
			{
				id: m.start,
				start: m.start,
				end: m.end,
				content: m.description,
				catcierge: m,
				className: "alert-info",
				template: "day",
				type: "background"
			};

			data.update(catcierge_event);
		}
		else
		{
			// Normal event.
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
				className: m.status_class,
				template: "item"
			};

			data.update(catcierge_event);

			if (m.live)
			{
				start = new Date(m.start).addHours(-2);
				end = new Date(m.start).addHours(2);

				timeline.setWindow(start, end);
			}
		}
	};

	ws.onclose = function(msg)
	{
		// TODO: Don't do it like this...
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
