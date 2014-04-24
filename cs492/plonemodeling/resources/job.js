function changeJobStatus(){
	var jobID = document.getElementById("jobID").innerHTML;

	$.getJSON(jobID + "/change_jobstatus", function(json) {
		document.getElementById("job_status").innerHTML = json.response;
		location.reload();
	})	
	
}

