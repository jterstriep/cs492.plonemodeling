from five import grok

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from plone.dexterity.content import Container
from plone.directives import form
from plone.namedfile.interfaces import IImageScaleTraversable
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_inner
from cs492.plonemodeling import MessageFactory as _
import json
import logging
from urlparse import parse_qs

import socket
import string
import random

from zope.lifecycleevent.interfaces import IObjectAddedEvent
import boto.ec2
import time


## imports to redefine Add and View forms
from plone.directives import dexterity
from plone.dexterity.browser.add import DefaultAddForm, DefaultAddView

USER_DATA = """
    #!/bin/bash

    MONITOR_LOCATION="https://raw.github.com/falkrust/PloneMonitor/master/monitor.py"
    MONITOR_FNAME="monitor.py"

    function monitor_setup {
        # $1 is plone location
        # $2 is authToken
        cd ~
        echo changed directory to $PWD
        echo "downloading monitor script"
        wget -N $MONITOR_LOCATION

        if [ -f $MONITOR_FNAME ]; then
        echo "file downloaded successfully"
        echo "setting exec permissions"
        chmod +x $MONITOR_FNAME

        echo "Calling the monitor script now"
        python2 $MONITOR_FNAME $1 $2
        fi
    }

"""

region_list = SimpleVocabulary(
    [SimpleTerm(value=u'us-east-1', title=_(u'us-east-1')),
     SimpleTerm(value=u'us-west-1', title=_(u'us-west-1')),
     SimpleTerm(value=u'us-west-2', title=_(u'us-west-2'))]
    )

instance_type_list = SimpleVocabulary(
    [SimpleTerm(value=u't1.micro', title=_(u't1.micro'))]
)


# Interface class used to define content-type schema.
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
        description=u"Perferably the list of available region would be built dynamically ",
        required=False,
    )

    instance_type = schema.Choice(
        title=_(u"Instance Type"),
        vocabulary=instance_type_list,
        required=False,
        description=u"Perferably the list of available instance types would be built dynamically ",
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
    vm_status = 'stopped'

    running_vm_id = ''

    def get_next_key(self):
        return self.monitorAuthToken

    def get_status(self):
        return self.vm_status

    def getTitle(self):
        return self.title

    def getInstanceStatus(self):
        try:
            conn = boto.ec2.connect_to_region(region, aws_access_key_id=self.accessKey, aws_secret_access_key=self.secretKey)
            instances = conn.get_only_instances([running_vm_id])
            return instances[0].update()
        except:
            return ''

    def get_monitor_key(self):
        AUTH_TOKEN_LENGTH = 10
        if self.monitorAuthToken:
            return self.monitorAuthToken
        else:
            self.monitorAuthToken = ''.join(random.choice(string.ascii_lowercase
                                            + string.digits) for _ in range(AUTH_TOKEN_LENGTH))
            return self.monitorAuthToken

    def start_machine(self, job_context, job):
        logger = logging.getLogger('Plone')
        logger.info('start_machine method called')
        if self.running_vm_id:
            return False

        ploneLocation = "http://" + socket.gethostbyname(socket.gethostname()) + ":8080/"
        vm_context = aq_inner(self)
        vm_path = ploneLocation + vm_context.absolute_url_path()
        logger.info('vm path is' + str(vm_path))

        try:
            user_data_script = USER_DATA + 'monitor_setup ' + vm_path + ' ' + self.get_monitor_key()

            logger.info('Credentials are ' + self.accessKey + self.secretKey)
            conn = boto.ec2.connect_to_region(self.region, aws_access_key_id=self.accessKey,
                                              aws_secret_access_key=self.secretKey)
            logger.info('Got a connection object')
            logger.info('Machine image is ' + self.machineImage)
            logger.info('Instance type is ' + self.instance_type)
            logger.info('user script is ' + user_data_script)

            reservation = conn.run_instances(self.machineImage, instance_type=self.instance_type, user_data=user_data_script)
            logger.info('Got a reservation object')
        except Exception, e:
            logger.info('Got exception ' + e.message)
        logger.info('Done with connection')
        instance = reservation.instances[0]

        instance_status = ''
        while True:
            instance_status = instance.update()
            if instance_status != 'pending':
                break
            time.sleep(10)
        logger.info('status of the instance is', instance_status)
        if instance_status == 'running':
            job.instance = instance.public_dns_name
            self.running_vm_id = instance.id

        return True


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
        all_jobs = catalog.searchResults(portal_type='cs492.plonemodeling.job')

        joblist = []
        for brain in all_jobs:
            if brain.getObject().virtualMachine.to_object == context:
                joblist.append(brain)
        return joblist


def is_authorized_monitor(vm, hashkey, catalog):
    """ Helper method to check if monitorAuthToken is valid """
    return vm.monitorAuthToken == hashkey


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

        try:
            job_path = current_vm.current_job
        except:
            job_path = None

        if job_path:
            # if has running job, return error since cannot have two running jobs
            return json.dumps({'response': 'fail', 'message': 'another job running'})
        else:
            # if the request is from authorized monitor script
            if is_authorized_monitor(current_vm, parse_result['hash'][0], catalog):
                next_job = find_next_job(current_vm, catalog)
                if next_job:
                    current_vm.current_job = next_job
                    next_job.job_status = 'Running'
                    next_job.start()
                    
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

        job_obj = current_vm.current_job

        if job_obj:
            if current_vm.monitorAuthToken == parse_result['hash'][0]:
                job_obj.job_status = new_status
                job_obj.end()
                # remove the object from the machine
                current_vm.current_job = None
                return '{"response": "success", "message": "status updated"}'
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

        self.request.response.setHeader('Content-type', 'application/json')

        context = aq_inner(self.context)
        accessKey = context.accessKey
        secretKey = context.secretKey
        machineImage = context.machineImage
        instanceType = context.instance_type
        region = context.region
        logger = logging.getLogger("Plone")
        logger.info(region)
        try:
            context.vm_status = "Invalid"
            conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKey, aws_secret_access_key=secretKey)
            reservation = conn.run_instances(machineImage, instance_type=instanceType)
        except boto.exception.EC2ResponseError, e:
            return json.dumps({'response': 'NOTOK', 'message': e.message})
        except Exception, e:
            return json.dumps({'response': 'NOTOK', 'message': e.message})
        instance = reservation.instances[0]
        status = instance.update()
        while status == 'pending':
            time.sleep(10)
            status = instance.update()
        if status != 'running':
            return json.dumps({'response': 'NOTOK', 'message': 'Instance Status:' + status})

        context.vm_status = "Valid"
        conn.terminate_instances(instance.id)

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


# Called when a virtual machine is first created.
@grok.subscribe(IVirtualMachine, IObjectAddedEvent)
def createVM(vm, event):
    vm.current_job = None
    vm.vm_status = "unevaluated"

class provideStatus(grok.View):

     grok.context(IVirtualMachine)
     grok.name('provide_status')

     def render(self):

          self.request.response.setHeader('Content-type', 'application/json')

          ## logging for demo
          logger = logging.getLogger('Plone')
          logger.info('Job status requested')

          query_string = self.request['QUERY_STRING']
          parse_result = parse_qs(query_string)

          if not 'hash' in parse_result:
               return '{"response": "fail", "message": "noHash"}'
          logger.info('the hash is ' + parse_result['hash'][0])
     
          context = aq_inner(self.context)
          catalog = getToolByName(context, 'portal_catalog')

          path = context.absolute_url_path()
          current_vm = catalog.unrestrictedTraverse(path)

          if is_authorized_monitor(current_vm, parse_result['hash'][0], catalog) and vm.current_job != None:
               return json.dumps({'response': 'success', 'message': vm.current_job.job_status})
          return '{"response": "fail", "message": "noJob"}'

