function changeJobStatus(){
	var jobName = document.getElementById("jobTitle").innerHTML;

	$.getJSON(jobName + "/change_jobstatus", function(json) {
		document.getElementById("job_status").innerHTML = json.response;
		location.reload();
	})	
	
}

