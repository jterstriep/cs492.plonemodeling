function changeJobStatus(jobURL){
	
	$.getJSON(jobURL + "/change_jobstatus", function(json) {
		var statusId = jobURL+"_jobstatus"
		location.reload();
	})	
}
