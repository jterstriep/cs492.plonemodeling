function testMachine() {
	$("#testresults").html("Waiting...");
	$.getJSON("test_machine", function(json) {
		if (json.response == "OK") {
			message = "Success";
		}
		else {
			message = json.message;
		}
		$("#testresults").html(message);
	})	
}
