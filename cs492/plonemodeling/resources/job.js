function changeJobStatus(){
	var jobURL = document.getElementById("jobURL").innerHTML;

	$.getJSON(jobURL + "/change_jobstatus", function(json) {
		document.getElementById("job_status").innerHTML = json.response;
		location.reload();
	})	
	
}

