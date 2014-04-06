function changeJobStatus(){
	var jobName = document.getElementById("jobTitle").innerHTML;

	$.getJSON(jobName + "/change_jobstatus", function(json) {

	})	
	location.reload();
}

