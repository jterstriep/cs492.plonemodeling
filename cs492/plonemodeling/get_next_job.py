import json
from urlparse import parse_qs

from Products.CMFCore.utils import getToolByName
from Acquisition import aq_inner



# imports for unrestricted user
from AccessControl import getSecurityManager
from AccessControl.SecurityManagement import newSecurityManager, setSecurityManager
from AccessControl.User import UnrestrictedUser as BaseUnrestrictedUser

## logging for demo
import logging

class UnrestrictedUser(BaseUnrestrictedUser):
    def getId(self):
        return self.getUserName()

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
        
        sm = getSecurityManager()


        try:
            try:
                # Clone the current user and assign a new role.
                # Note that the username (getId()) is left in exception
                # tracebacks in the error_log,
                # so it is an important thing to store.
                tmp_user = UnrestrictedUser(
                    sm.getUser().getId(), '', ['Manager'], ''
                    )

                # Wrap the user in the acquisition context of the portal
                portal = self.context.portal_url.getPortalObject()
                tmp_user = tmp_user.__of__(portal.acl_users)
                newSecurityManager(None, tmp_user)


                context = aq_inner(self.context)
                catalog = getToolByName(context, 'portal_catalog')
                
                hashValue = str(parse_result['hash'][0])
                vms = catalog.searchResults(portal_type='cs492.plonemodeling.virtualmachine')
                for vm in vms:
                    if vm.getObject().monitorString == hashValue:
                        jobs = catalog.searchResults(portal_type='cs492.plonemodeling.job')
                        vm_job = 0
                        for job in jobs:
                            if (getToolByName(job.getObject(), 'virtualMachine').to_object == vm.getObject()) and (job.getObject().job_status == "Running"):
                                job.getObject().job_status = "Finished"
                            if (getToolByName(job.getObject(), 'virtualMachine').to_object == vm.getObject()) and (job.getObject().job_status == "Queued") and ((not vm_job) or vm_job.modified.greaterThan(job.modified)):
                                vm_job = job
                        if vm_job:
                            vm_job.getObject().job_status = "Running"
                            return json.dumps({ 'response': 'OK', 'start_string': vm_job.getObject().startString  })
                
                return json.dumps({'response': 'NOTOK', 'reason': 'invalidHash', 'hash': hashValue })


            except:
                # If special exception handlers are needed, run them here
                raise
        finally:
            # Restore the old security manager
            setSecurityManager(sm)




