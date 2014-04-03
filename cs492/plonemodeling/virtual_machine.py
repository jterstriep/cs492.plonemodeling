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

    monitorString = schema.TextLine(
            title=_(u"Monitor Identifier"),
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

class getNextJob(grok.View):
    """ sample view class """

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
            return json.dumps({'response': 'NOTOK', 'reason': e.message});
        instance = reservation.instances[0]
        status = instance.update()
        while status == 'pending':
            time.sleep(10)
            status = instance.update()
        if status != 'running':
            return json.dumps({'response': 'NOTOK', 'reason': 'Instance Status:' + status})
        
        conn.terminate_instances(instance.id);

        return json.dumps({'response': 'OK'})

