import json
from urlparse import parse_qs

from Products.CMFCore.utils import getToolByName
from Acquisition import aq_inner





## logging for demo
import logging


class GetNextJob(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.doc_uid = request.form.get('uid', None)
    ## template = ViewPageTemplateFile('hello_world_view.pt')

    def __call__(self):
        """"""
        ## self.hello_name = getattr(self.context, 'hello_name', 'World')
        ##return self.template()

        ## logging for demo
        logger = logging.getLogger("Plone")
        logger.info("Job requested")

        method = self.request['REQUEST_METHOD']
        if method != 'GET':
            response = self.request.response
            response.setStatus("404 Not Found")
            return "Wrong method"

        query_string = self.request['QUERY_STRING']
        parse_result = parse_qs(query_string)
        if not 'hash' in parse_result:
            return "{'response': 'NOTOK', 'reason': 'noHash'}"
        
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')
        
        hashValue = str(parse_result['hash'][0])
        logger.info('the hash is ' + hashValue)

        vms = catalog.unrestrictedSearchResults(portal_type='cs492.plonemodeling.virtualmachine')
        for vm in vms:
            if vm._unrestrictedGetObject().monitorString == hashValue:
                jobs = catalog.unrestrictedSearchResults(portal_type='cs492.plonemodeling.job')
                vm_job = 0
                for job in jobs:
                    if (getToolByName(job._unrestrictedGetObject(), 'virtualMachine').to_object == vm._unrestrictedGetObject()) and (job._unrestrictedGetObject().job_status == "Running"):
                        job.getObject().job_status = "Finished"
                    if (getToolByName(job._unrestrictedGetObject(), 'virtualMachine').to_object == vm._unrestrictedGetObject()) and (job._unrestrictedGetObject().job_status == "Queued") and ((not vm_job) or vm_job.modified.greaterThan(job.modified)):
                        vm_job = job
                if vm_job:
                    vm_job._unrestrictedGetObject().job_status = "Running"
                    return json.dumps({ 'response': 'OK', 'start_string': vm_job._unrestrictedGetObject().startString  })
        
        return json.dumps({'response': 'NOTOK', 'reason': 'invalidHash', 'hash': hashValue })
