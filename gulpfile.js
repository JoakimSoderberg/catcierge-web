var gulp = require("gulp");
var less = require("gulp-less");
var path = require("path");

gulp.task("default", function()
{
	// TODO: What?
});

// This will read your bower.json, iterate through your
// dependencies and returns an array of files defined in
// the main property of the packages bower.json.
var main_bower_files = require("main-bower-files");

// Copy the relevant files from the bower components to the static dir.
// https://medium.com/@wizardzloy/customizing-bootstrap-with-gulp-js-and-bower-fafac8e3e1af
gulp.task("bower", function()
{
	return gulp.src(main_bower_files(),
	{
		"base": "bower_components"
	})
	.pipe(gulp.dest("static/lib"));
});

// Copy bootstrap less sources.
gulp.task("bootstrap:prepareless", ["bower"], function()
{
	return gulp.src("less/bootstrap/variables.less")
		.pipe(gulp.dest("static/lib/bootstrap/less"));
});

// Compile bootstrap less sources.
gulp.task("bootstrap:less", ["bootstrap:prepareless"], function()
{
	return gulp.src(["static/lib/bootstrap/less/bootstrap.less"])
		.pipe(less())
		.pipe(gulp.dest("static/lib/bootstrap/dist/css"));
});

// TODO: Is this how I should do this?
// Copy catcierge less sources.
gulp.task("catcierge:prepareless", function()
{
	return gulp.src("less/*.less")
		.pipe(gulp.dest("static/less/"));
});

// Compile catcierge less sources.
gulp.task("catcierge:less", ["catcierge:prepareless"], function()
{
	return gulp.src(["static/*.less"])
		.pipe(less())
		.pipe(gulp.dest("static/css"));
});

gulp.task("watch", function()
{
	gulp.watch(
		[
			"less/bootstrap/variables.less",
			"less/*.less"
		], 
		[
			"bootstrap:less",
			"catcierge:less"
		]
	);
});


