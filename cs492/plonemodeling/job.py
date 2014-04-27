from five import grok

from zope import schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.dexterity.content import Item
from plone.namedfile.interfaces import IImageScaleTraversable

from z3c.relationfield.schema import RelationChoice
from plone.formwidget.contenttree import ObjPathSourceBinder
from Acquisition import aq_inner

from zope.lifecycleevent.interfaces import IObjectAddedEvent, IObjectMovedEvent, IObjectRemovedEvent, IObjectModifiedEvent
from Products.CMFCore.utils import getToolByName

from plone.supermodel import model
from cs492.plonemodeling import MessageFactory as _

import string
import random

from cs492.plonemodeling.virtual_machine import IVirtualMachine
import json
from datetime import datetime

import logging

job_status_list = SimpleVocabulary(
    [SimpleTerm(value=u'Queued', title=_(u'Queued')),
     SimpleTerm(value=u'Failed', title=_(u'Failed')),
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
        default=job_status_list.getTerm(u'Pending').value
    )

    virtualMachine = RelationChoice(
        title=_(u"Virtual machine"),
        source=ObjPathSourceBinder(object_provides=IVirtualMachine.__identifier__),
        required=True,
    )


# Custom content-type class; objects created for this content type will
# be instances of this class. Use this class to add content-type specific
# methods and properties. Put methods that are mainly useful for rendering
# in separate view classes.
class Job(Item):
    grok.implements(IJob)

    # Add your class methods and properties here

    start_time = "--"
    end_time = "--"
    creation_time = "--"
    queued_time = "--"

    def getTitle(self):
        return self.title

    def getStatus(self):
        return self.job_status

    def startNow(self):
        self.start_time = datetime.now()

    def endNow(self):
        self.end_time = datetime.now()

    def getDuration(self):
        if self.start_time is "--" or self.end_time is "--":
            return "--"
        return str(self.end_time - self.start_time)

    def getVMTitle(self):
        return self.virtualMachine.to_object.title

    def getVMUrl(self):
        return self.virtualMachine.to_object.absolute_url_path()

    def getId(self):
        return self.id


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


@grok.subscribe(IJob, IObjectAddedEvent)
def createJob(job, event):
    logger = logging.getLogger("Plone")

    ## assign time upon job creation_time.
    job.creation_time = datetime.now()

    ## create authorization token
    job.monitorAuthToken = ''.join(random.choice(string.ascii_lowercase +
                                   string.digits) for _ in range(AUTH_TOKEN_LENGTH))

    ## Do not queue the job if status is not Queued
    if job.job_status != "Queued":
        job.job_status = "Pending"
        return

    job.queued_time = datetime.now()
    virtualMachine = getToolByName(job, 'virtualMachine').to_object
    context = aq_inner(job)
    result = virtualMachine.start_machine(context, job)
    logger.info('Result of vm.start_machine is' + str(result))


class changeJobStatus(grok.View):

    grok.context(IJob)
    grok.require('zope2.View')
    grok.name('change_jobstatus')

    def render(self):
        self.request.response.setHeader('Content-type', 'application/json')
        context = aq_inner(self.context)
        status_string = context.job_status

        if status_string in ['Pending', 'Terminated', 'Failed', 'Finished']:
            context.job_status = 'Queued'
        if status_string == 'Running':
            context.job_status = 'Terminated'
        if status_string == 'Queued':
            context.job_status = 'Pending'

        return json.dumps({'response': context.job_status})


@grok.subscribe(IJob, IObjectModifiedEvent)
def job_changed(job, event):
    if job.job_status == "Queued" and job.queued_time == "--":
        virtualMachine = getToolByName(job, 'virtualMachine').to_object
        context = aq_inner(job)
        virtualMachine.start_machine(context, job)
        job.queued_time = datetime.now()
    else:
        job.queued_time = "--"
    logger = logging.getLogger("Plone")
    logger.info("modified")
    return
