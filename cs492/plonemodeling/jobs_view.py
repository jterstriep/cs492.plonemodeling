from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_parent, aq_inner
from zope.component import getMultiAdapter

from cs492.plonemodeling.job import IJob
import time
import ZODB.FileStorage
import ZODB.serialize
import operator

queued = []
unqueued = []

def time_compare(x, y):
    if x['start'] is None:
	return 1
    elif y['start'] is None:
	return -1
    elif x['start']<y['start']:
	return 1
    elif x['start']>y['start']:
	return -1
    else:
	return 0

def status_compare(x, y):
    if x['start'] is None:
	return -1
    elif y['start'] is None:
	return 1
    elif x['start']<y['start']:
	return -1
    elif x['start']>y['start']:
	return 1
    else:
	return 0

def get_job_query(self):
    """
    Check the current user (The one who logged in). 
    If curUser is one of the Site Adminstrarors, display all the jobs.
    Else, only display the jobs created by the current user.
    """
    context = aq_inner(self.context)
    catalog = getToolByName(context, 'portal_catalog')
    mt =  getToolByName(self, 'portal_membership') 
    currentUser = mt.getAuthenticatedMember() 
   
    all_jobs = catalog.searchResults(portal_type= 'cs492.plonemodeling.job', sort_in='modified', sort_order='ascending')
    queued = []
    unqueued = []
    i = 1
    for brain in all_jobs:
        if brain.getObject().getStatus() == "queued":
            if ("Site Administrators" in currentUser.getGroups() or brain["Creator"] == currentUser.getUserName()):
                queued.append([i,brain])
            i += 1
        else:
            if ("Site Administrators" in currentUser.getGroups() or brain["Creator"] == currentUser.getUserName()):
                unqueued.append(["-",brain])
    return queued + unqueued

class JobsView(BrowserView):

    template = ViewPageTemplateFile('jobs_view.pt')

    def __call__(self):    
		
	all_jobs = get_job_query(self)
	   
	self.all_jobs = getattr(self.context, 'all_jobs', all_jobs)
	return self.template()
  

    


      
  
