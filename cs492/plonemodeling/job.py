from five import grok

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.dexterity.content import Item 
from plone.namedfile.interfaces import IImageScaleTraversable

from z3c.relationfield.schema import RelationChoice
from plone.formwidget.contenttree import ObjPathSourceBinder
from Acquisition import aq_inner

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from Products.CMFCore.utils import getToolByName

from plone.supermodel import model
from cs492.plonemodeling import MessageFactory as _

import socket, string, random

from cs492.plonemodeling.virtual_machine import IVirtualMachine
import urllib
import boto.ec2
import time
from datetime import datetime

import logging

## imports to redefine Add and View forms
from plone.directives import dexterity
from plone.dexterity.browser.add import DefaultAddForm, DefaultAddView


job_status_list = SimpleVocabulary(
    [SimpleTerm(value=u'Queued', title=_(u'Queued')),
     SimpleTerm(value=u'Started', title=_(u'Started')),
     SimpleTerm(value=u'Finished', title=_(u'Finished')),
     SimpleTerm(value=u'Running', title=_(u'Running')),
     SimpleTerm(value=u'Terminated', title=_(u'Terminated')),
     SimpleTerm(value=u'Pending', title=_(u'Pending'))]
    )

AUTH_TOKEN_LENGTH = 10
# Interface class; used to define content-type schema.

class IJob(model.Schema, IImageScaleTraversable):
    """
    Job which needs to be run on scientific model
    """

    # If you want a schema-defined interface, delete the model.load
    # line below and delete the matching file in the models sub-directory.
    # If you want a model-based interface, edit
    # models/job.xml to define the content type.

    # form.model("models/job.xml")
    startString = schema.TextLine(
            title=_(u"command used to start the model")
    )
    
    job_status = schema.Choice(
            title=_(u"Job Status"),
            vocabulary=job_status_list,
            required=False,
    )
        
    virtualMachine = RelationChoice(
            title=_(u"Virtual machine"),
            source=ObjPathSourceBinder(object_provides=IVirtualMachine.__identifier__),
            required=True,
        )
    monitorAuthToken = schema.TextLine(
            title=_(u"Monitor authorization token"),
            required=False
        )

# Custom content-type class; objects created for this content type will
# be instances of this class. Use this class to add content-type specific
# methods and properties. Put methods that are mainly useful for rendering
# in separate view classes.

class Job(Item):
    grok.implements(IJob)

    # Add your class methods and properties here
    indexList = []
    virtualMachineTitle = 'aaa'
 
    def __init__(self):
        self.indexList = []

    def getTitle(self):
        return self.title

    def getStatus(self):
        return self.job_status

    def getStartTime(self):
        if self.start is None:
            return "--"
        return self.start

    def getEndTime(self):
        return self.end

    def getVMTitle(self):
        return self.virtualMachine.to_object.getTitle()

    def getId(self):
        return self.id;

  


    def getJobList(self):
        print "enter"
        context = aq_inner(self)
        catalog = getToolByName(context, 'portal_catalog')
        all_jobs = catalog.searchResults(portal_type= 'cs492.plonemodeling.job',sort_on='modified', sort_order='ascending')
        for brain in all_jobs:
            self.indexList.append(brain);
        
    def getJobIndex(self):
        #get the joblist sorted by last modified time.
        if len(self.indexList) is 0:
            self.getJobList()
        i = 0
        for curJob in self.indexList:
            if curJob.getObject().getId() is self.getId():
                return i
            i = i+1
        return "x"


# View class
# The view will automatically use a similarly named template in
# job_templates.
# Template filenames should be all lower case.
# The view will render when you request a content object with this
# interface with "/@@sampleview" appended.
# You may make this the default view focontextr content objects
# of this type by uncommenting the grok.name line below or by
# changing the view class name and template filename to View / view.pt.

class SampleView(grok.View):
    """ sample view class """

    grok.context(IJob)
    grok.require('zope2.View')

    grok.name('view')

    # Add view methods here

@grok.subscribe(IJob, IObjectAddedEvent)
def createJob(job, event):
    logger = logging.getLogger("Plone")

    ## assign time upon job creation.
    job.start = str(datetime.now())
    

    ## create authorization token
    job.monitorAuthToken = ''.join(random.choice(string.ascii_lowercase \
        + string.digits) for _ in range(AUTH_TOKEN_LENGTH))

    ## Do not queue the job if status is not Queued
    if job.job_status != "Queued":
        job.job_status = "Pending"
        return

    virtualMachine = getToolByName(job, 'virtualMachine').to_object
    context = aq_inner(job)
    catalog = getToolByName(context, 'portal_catalog')
    jobs = catalog.searchResults(portal_type='cs492.plonemodeling.job')
    for job_query in jobs:
            if getToolByName(job_query.getObject(), 'virtualMachine').to_object == virtualMachine \
                    and job_query.getObject().job_status == "Running":
                return
    accessKey = virtualMachine.accessKey
    secretKey = virtualMachine.secretKey
    machineImage = virtualMachine.machineImage
    instanceType = virtualMachine.instance_type
    region = virtualMachine.region
    ploneLocation = "http://" + socket.gethostbyname(socket.gethostname()) + ":8080/Plone/"

    logger.info(region)
    monitor = urllib.urlopen('http://proteinmonster.nfshost.com/static/monitor.txt')
    startScript = monitor.read()
    startScript = startScript.replace("LOCATION", ploneLocation)
    startScript = startScript.replace("IDENTIFIER", virtualMachine.monitorString)
    conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKey, aws_secret_access_key=secretKey)
    reservation = conn.run_instances(machineImage,instance_type=instanceType,user_data=startScript)
    instance = reservation.instances[0]
    status = instance.update()
    while status == 'pending':
        time.sleep(10)
        status = instance.update()
    if status == 'running':
        job.instance = instance.public_dns_name



class EditForm(dexterity.EditForm):
    """ Custom edit form which hides authToken

        monitorAuthToken should not be edited from EditForm
        Hence, we hide it here, though user can still
        change it programmatically
    """
    grok.context(IJob)

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
