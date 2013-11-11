from five import grok

from z3c.form import group, field
from zope import schema
from zope.interface import invariant, Invalid
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.dexterity.content import Container
from plone.directives import dexterity, form
from plone.app.textfield import RichText
from plone.namedfile.field import NamedImage, NamedFile
from plone.namedfile.field import NamedBlobImage, NamedBlobFile
from plone.namedfile.interfaces import IImageScaleTraversable

from z3c.relationfield.schema import RelationChoice
from plone.formwidget.contenttree import ObjPathSourceBinder

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from Products.CMFCore.utils import getToolByName

from plone.supermodel import model
from cs492.plonemodeling import MessageFactory as _

from cs492.plonemodeling.virtual_machine import IVirtualMachine
from Products.statusmessages.interfaces import IStatusMessage
import boto.ec2
import time

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
    start = schema.Datetime(
            title=_(u"Start time"),
            required=False,
    )

    end = schema.Datetime(
            title=_(u"End time"),
            required=False,
    )

    instance = schema.TextLine(
	    title=_(u"Instance location"),
	    required=False,
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

class Job(Container):
    grok.implements(IJob)

    # Add your class methods and properties here


# View class
# The view will automatically use a similarly named template in
# job_templates.
# Template filenames should be all lower case.
# The view will render when you request a content object with this
# interface with "/@@sampleview" appended.
# You may make this the default view for content objects
# of this type by uncommenting the grok.name line below or by
# changing the view class name and template filename to View / view.pt.

class SampleView(grok.View):
    """ sample view class """

    grok.context(IJob)
    grok.require('zope2.View')

    # grok.name('view')

    # Add view methods here

@grok.subscribe(IJob, IObjectAddedEvent)
def createJob(job, event):
    virtualMachine = getToolByName(job, 'virtualMachine').to_object
    accessKey = virtualMachine.accessKey
    secretKey = virtualMachine.secretKey
    machineImage = virtualMachine.machineImage
    conn = boto.ec2.connect_to_region("us-west-2", aws_access_key_id=accessKey, aws_secret_access_key=secretKey)
    reservation = conn.run_instances(machineImage,instance_type='t1.micro')
    instance = reservation.instances[0]
    status = instance.update()
    while status == 'pending':
        time.sleep(10)
        status = instance.update()
    if status == 'running':
        job.instance = instance.public_dns_name