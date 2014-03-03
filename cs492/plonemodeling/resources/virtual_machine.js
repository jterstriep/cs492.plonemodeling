function testMachine() {
	$("#testresults").html("Waiting...");
	$.getJSON("test_machine", function(json) {
		if (json.respone == "OK") {
			message = "Success";
		}
		else {
			message = json.reason;
		}
		$("#testresults").html(message);
	})	
}
