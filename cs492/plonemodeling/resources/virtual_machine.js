function testMachine() {
	$("#testresults").html("Waiting...");
	$.getJSON("test_machine", function(json) {
		if (json.response == "OK") {
			message = "Success";
			document.getElementById("vm_status").innerHTML = "Valid";
		}
		else {
			message = json.message;
			document.getElementById("vm_status").innerHTML = "Invalid";
		}
		$("#testresults").html(message);
	})	
}
