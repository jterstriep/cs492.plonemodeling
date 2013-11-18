import json
from urlparse import parse_qs

## logging for demo
import logging

## for testing
## actual values will be gotten from the queue
hashDict = {
    '12345': 'ls -l',
    '23456': 'ls -R /'
}

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

        hashValue = str(parse_result['hash'][0])
        if not hashValue in hashDict:
            return "{'response': 'NOTOK', 'reason': 'invalidHash', 'hash': '" + hashValue +"'}"
        return json.dumps(
                {
                    'response': 'OK',
                    'start_string': hashDict[hashValue]
                }
            )
