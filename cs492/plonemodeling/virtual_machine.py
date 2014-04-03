from five import grok

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from plone.dexterity.content import Container
from plone.directives import form
from plone.namedfile.interfaces import IImageScaleTraversable
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_inner
from cs492.plonemodeling import MessageFactory as _
import json, logging
from urlparse import parse_qs

import boto.ec2
import time


## imports to redefine Add and View forms
from plone.directives import dexterity
from plone.dexterity.browser.add import DefaultAddForm, DefaultAddView


region_list = SimpleVocabulary(
    [SimpleTerm(value=u'us-east-1', title=_(u'us-east-1')),
     SimpleTerm(value=u'us-west-1', title=_(u'us-west-1')),
     SimpleTerm(value=u'us-west-2', title=_(u'us-west-2'))]
    )

instance_type_list = SimpleVocabulary(
    [SimpleTerm(value=u't1.micro', title=_(u't1.micro'))]
)



# Interface class; used to define content-type schema.

class IVirtualMachine(form.Schema, IImageScaleTraversable):
    """
    Specification of an EC2 instance
    """

    # If you want a schema-defined interface, delete the model.load
    # line below and delete the matching file in the models sub-directory.
    # If you want a model-based interface, edit
    # models/virtual_machine.xml to define the content type.

    #form.model("models/virtual_machine.xml")

    region = schema.Choice(
            title=_(u"Region"),
            vocabulary=region_list,
            description = u"Perferably the list of available region would be built dynamically ",
            required=False,
    )

    instance_type = schema.Choice(
            title=_(u"Instance Type"),
            vocabulary=instance_type_list,
            required=False,
            description = u"Perferably the list of available instance types would be built dynamically ",
    )

    accessKey = schema.TextLine(
            title=_(u"AWS Access Key"),
    )

    secretKey = schema.Password(
            title=_(u"AWS Secret Key"),
    )

    machineImage = schema.TextLine(
            title=_(u"Amazon Machine Image"),
    )

    monitorAuthToken = schema.TextLine(
            title=_(u"Monitor authorization token"),
            required=False
    )



# Custom content-type class; objects created for this content type will
# be instances of this class. Use this class to add content-type specific
# methods and properties. Put methods that are mainly useful for rendering
# in separate view classes.

class VirtualMachine(Container):
    grok.implements(IVirtualMachine)

    # Add your class methods and properties here
    
    status = "stop"

    def getTitle(self):
        return self.title

    def start_machine(self):
        return False


# View class
# The view will automatically use a similarly named template in
# virtual_machine_templates.
# Template filenames should be all lower case.
# The view will render when you request a content object with this
# interface with "/@@sampleview" appended.
# You may make this the default view for content objects
# of this type by uncommenting the grok.name line below or by
# changing the view class name and template filename to View / view.pt.

class SampleView(grok.View):
    """ sample view class """

    grok.context(IVirtualMachine)
    grok.require('zope2.View')
    grok.name('view')


    # Add view methods here
    def getJobsOnThisVM(self):
        """
        This method returns a list of jobs associated with this virtual machine.
        """
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')
        all_jobs = catalog.searchResults(portal_type= 'cs492.plonemodeling.job')
        joblist=[]
        for brain in all_jobs:
            if brain.getObject().virtualMachine.to_object == context:
                joblist.append(brain)
        return joblist;

def is_authorized_monitor(vm, hashkey, catalog):
    """ Helper method to check if monitorAuthToken is valid """

    jobs = catalog.unrestrictedSearchResults(portal_type='cs492.plonemodeling.job')
    for job in jobs:
        job_obj = job._unrestrictedGetObject()
        # if the request if from authorized monitor script
        if job_obj.monitorAuthToken == hashkey and \
            getToolByName(job_obj, 'virtualmachine').to_object == vm:
            return True
    return False

def find_next_job(vm, catalog):
    """ helper method to find the first job to be run on current vm """

    jobs = catalog.unrestrictedSearchResults(portal_type='cs492.plonemodeling.job')
    next_job = None
    for job in jobs:
        job_obj = job._unrestrictedGetObject()

        
        if getToolByName(job_obj, 'virtualmachine').to_object == vm and \
            job_obj.job_status == 'Queued' and \
            (not next_job or next_job.modified.greaterThan(job_obj.modified)):
            next_job = job_obj
    return next_job

class getNextJob(grok.View):
    """ get next job to be run on virtual machine """

    grok.context(IVirtualMachine)
    grok.require('zope2.View')
    grok.name('get_next_job')



    def render(self):
        """ return next job for virtual machine """
        # check the monitor identity from the request
        #   report error if it is incorrect
        #   terminate instance

        # log the time of the last polling

        # check for running job if found
        #   return nothing to do

        # check for queued job if found
        #   return job information

        self.request.response.setHeader('Content-type', 'application/json')


        ## logging for demo
        logger = logging.getLogger('Plone')
        logger.info('Job requested')

        query_string = self.request['QUERY_STRING']
        parse_result = parse_qs(query_string)
        if not 'hash' in parse_result:
            return '{"response": "NOTOK", "message": "noHash"}'
        
        logger.info('the hash is ' + parse_result['hash'][0])
        context = aq_inner(self.context)

        catalog = getToolByName(context, 'portal_catalog')

        path = context.absolute_url_path()
        current_vm = catalog.unrestrictedTraverse(path)

        job_path = current_vm.current_job_url

        if job_path:
            # if has running job, return error since cannot have two running jobs
            return json.dumps({'response': 'fail', 'message': 'another job running'})  
        else:
            # if the request is from authorized monitor script
            if is_authorized_monitor(current_vm, parse_result['hash'][0], catalog):
                next_job = find_next_job(current_vm, catalog)
                if next_job:
                    current_vm.current_job = next_job.absolute_url_path()
                    next_job.status = 'Started'
                    return json.dumps({
                        'response': 'success',
                        'start_string': next_job.startString,
                        })
                else:
                    return json.dumps({'response': 'fail', 'message': 'no jobs to be run'})
            else:
                return json.dumps({'response': 'fail', 'message': 'invalid hash'})


class updateJobStatus(grok.View):
    """ Web service which updates job status

        Expects authorization token to be passed in from monitor
    """

    grok.context(IVirtualMachine)
    grok.require('zope2.View')
    grok.name('update_job_status')

    def render(self):

        self.request.response.setHeader('Content-type', 'application/json')


        ## logging for demo
        logger = logging.getLogger('Plone')
        logger.info('Job status update requested')

        query_string = self.request['QUERY_STRING']
        parse_result = parse_qs(query_string)

        if not 'hash' in parse_result:
            return '{"response": "fail", "message": "noHash"}'
        new_status = parse_result.get('new_status', None)
        if not new_status:
            return '{"response": "fail", "message": "new status missing"}'
        else:
            # currently support only two kinds of status updates
            # failed stands for script which returned an error when running
            if new_status not in ['Finished', 'Failed']:
                return '{"response": "fail", "message": "Invalid new status"}'
        
        context = aq_inner(self.context)
        catalog = getToolByName(context, 'portal_catalog')

        path = context.absolute_url_path()
        current_vm = catalog.unrestrictedTraverse(path)

        job_path = current_vm.current_job_url

        if job_path:
            # if has job, assume the job is finished
            job_obj = catalog.unrestrictedTraverse(job_path)
            if job_obj.monitorAuthToken == parse_result['hash'][0]:
                job_obj.job_status = new_status
                # remove the object from the machine
                current_vm.current_job_url = None
                return '{"response": "sucess", "message": "status updated"}'
            else:
                return '{"response": "fail", "message": "invalid hash"}'
        else:
            # if no job, then request is invalid
            # return error
            return '{"response": "fail", "message": "job is not found"}'



class testMachine(grok.View):

    grok.context(IVirtualMachine)
    grok.require('zope2.View')
    grok.name('test_machine')

    def render(self):

        self.request.response.setHeader('Content-type', 'application/json');

        context = aq_inner(self.context)
        accessKey = context.accessKey
        secretKey = context.secretKey
        machineImage = context.machineImage
        instanceType = context.instance_type
        region = context.region
        logger = logging.getLogger("Plone")
        logger.info(region)
        try:
            conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKey, aws_secret_access_key=secretKey)
            reservation = conn.run_instances(machineImage,instance_type=instanceType)
        except boto.exception.EC2ResponseError, e:
            return json.dumps({'response': 'NOTOK', 'message': e.message});
        except Exception, e:
            return json.dumps({'response': 'NOTOK', 'message': e.message});
        instance = reservation.instances[0]
        status = instance.update()
        while status == 'pending':
            time.sleep(10)
            status = instance.update()
        if status != 'running':
            return json.dumps({'response': 'NOTOK', 'message': 'Instance Status:' + status})
        
        conn.terminate_instances(instance.id);

        return json.dumps({'response': 'OK'})

class EditForm(dexterity.EditForm):
    """ Custom edit form which hides authToken

        monitorAuthToken should not be edited from EditForm
        Hence, we hide it here, though user can still
        change it programmatically
    """
    grok.context(IVirtualMachine)

    def updateWidgets(self):
        super(EditForm, self).updateWidgets()
        self.widgets['monitorAuthToken'].mode = 'hidden'


class AddForm(DefaultAddForm):
    """ Custom add form which hides authToken
        Then token is generated randomly and should not be
        edited by user
    """
    def updateWidgets(self):
        """ """
        # Some custom code here
        super(AddForm, self).updateWidgets()
        self.widgets['monitorAuthToken'].mode = 'hidden' 

class AddView(DefaultAddView):
    form = AddForm
