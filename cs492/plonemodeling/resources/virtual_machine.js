function testMachine(absolute_url) {
	$("#testresults").html("Waiting...");
	$.getJSON(absolute_url + "/test_machine", function(json) {
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

function changeJobStatus(jobURL){
	
	$.getJSON(jobURL + "/change_jobstatus", function(json) {
		var statusId = jobURL+"_jobstatus"
		location.reload();
	})	
}
